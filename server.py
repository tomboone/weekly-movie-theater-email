import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Header, HTTPException

from config import Settings
from main import run_pipeline

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

settings = Settings()  # type: ignore[reportCallIssue]


def _parse_cron(expr: str) -> dict:
    parts = expr.split()
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


async def _scheduled_run():
    logger.info("Scheduler triggered pipeline run")
    try:
        await run_pipeline(settings)
    except Exception:
        logger.exception("Pipeline run failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    cron_kwargs = _parse_cron(settings.schedule_cron)
    scheduler.add_job(
        _scheduled_run,
        CronTrigger(timezone=settings.schedule_timezone, **cron_kwargs),
    )
    scheduler.start()
    logger.info("Scheduler started: %s %s", settings.schedule_cron, settings.schedule_timezone)
    yield
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
