import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Header, HTTPException

from config import Settings
from main import run_pipeline
from state import load_state

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

settings: Settings = None  # type: ignore[assignment]


def _parse_cron(expr: str) -> dict:
    parts = expr.split()
    # Convert standard cron day_of_week (0=Sunday) to APScheduler/ISO (0=Monday)
    dow = str((int(parts[4]) - 1) % 7)
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": dow,
    }


def _now() -> datetime:
    """Wrapped for test patching."""
    return datetime.now(tz=ZoneInfo("UTC"))


def _most_recent_scheduled_time(cron_expr: str, timezone: str) -> datetime | None:
    """Compute the most recent time the cron should have fired.

    Walks backward from now up to 7 days to find the last matching
    day_of_week + hour + minute that has already passed.
    """
    cron = _parse_cron(cron_expr)
    minute, hour = int(cron["minute"]), int(cron["hour"])
    # _parse_cron already returns ISO weekday (0=Monday), same as Python
    python_dow = int(cron["day_of_week"])

    tz = ZoneInfo(timezone)
    now = _now().astimezone(tz)

    for days_ago in range(7):
        candidate = now - timedelta(days=days_ago)
        candidate = candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate.weekday() == python_dow and candidate <= now:
            return candidate

    return None


def _should_run_on_startup(
    cron_expr: str,
    timezone: str,
    last_run: str | None,
) -> bool:
    """Check if the most recent scheduled time was missed."""
    if last_run is None:
        return True

    most_recent = _most_recent_scheduled_time(cron_expr, timezone)
    if most_recent is None:
        return False

    last_run_date = datetime.strptime(last_run, "%Y-%m-%d").date()
    return last_run_date < most_recent.date()


async def _scheduled_run():
    logger.info("Scheduler triggered pipeline run")
    try:
        await run_pipeline(settings)
    except Exception:
        logger.exception("Pipeline run failed")


async def _scheduler_watchdog(scheduler: AsyncIOScheduler, check_interval: float = 600) -> None:
    """Periodically verify the scheduler is alive. Exit if dead."""
    while True:
        await asyncio.sleep(check_interval)
        if not scheduler.running:
            logger.error("Scheduler watchdog: scheduler is dead, exiting process")
            sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global settings
    if settings is None:  # type: ignore[comparison-overlap]
        settings = Settings()  # type: ignore[reportCallIssue]
    scheduler = AsyncIOScheduler()
    cron_kwargs = _parse_cron(settings.schedule_cron)
    scheduler.add_job(
        _scheduled_run,
        CronTrigger(timezone=settings.schedule_timezone, **cron_kwargs),
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info("Scheduler started: %s %s", settings.schedule_cron, settings.schedule_timezone)
    state = load_state(settings.movie_state_path)
    if _should_run_on_startup(settings.schedule_cron, settings.schedule_timezone, state["last_run"]):
        logger.info("Missed run detected — running pipeline now")
        try:
            await run_pipeline(settings)
        except Exception:
            logger.exception("Startup pipeline run failed")

    watchdog_task = asyncio.create_task(_scheduler_watchdog(scheduler))

    yield

    watchdog_task.cancel()
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/trigger")
async def trigger(date: str | None = None, authorization: str = Header(default="")):
    expected = settings.trigger_api_key
    if not expected or authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    logger.info("Manual trigger received (date override: %s)", date)
    try:
        await run_pipeline(settings, date_override=date)
        return {"status": "success"}
    except Exception as e:
        logger.exception("Pipeline failed")
        return {"status": "error", "detail": str(e)}
