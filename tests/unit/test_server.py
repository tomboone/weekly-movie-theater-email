import asyncio
import contextlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from server import _should_run_on_startup


class TestShouldRunOnStartup:
    """Test missed-run detection logic."""

    def test_no_previous_run(self):
        """First ever run — last_run is None, should run."""
        result = _should_run_on_startup(
            cron_expr="0 10 * * 5",
            timezone="America/New_York",
            last_run=None,
        )
        assert result is True

    @patch("server._now")
    def test_last_run_before_most_recent_scheduled_time(self, mock_now):
        """last_run is from last week, scheduled time has passed — should run."""
        mock_now.return_value = datetime(2026, 3, 27, 15, 0, tzinfo=ZoneInfo("America/New_York"))
        result = _should_run_on_startup(
            cron_expr="0 10 * * 5",
            timezone="America/New_York",
            last_run="2026-03-20",
        )
        assert result is True

    @patch("server._now")
    def test_last_run_is_today(self, mock_now):
        """last_run is today — already ran, should not run."""
        mock_now.return_value = datetime(2026, 3, 27, 15, 0, tzinfo=ZoneInfo("America/New_York"))
        result = _should_run_on_startup(
            cron_expr="0 10 * * 5",
            timezone="America/New_York",
            last_run="2026-03-27",
        )
        assert result is False

    @patch("server._now")
    def test_before_scheduled_time_same_day(self, mock_now):
        """It's Friday but before 10am — most recent scheduled time is last week."""
        mock_now.return_value = datetime(2026, 3, 27, 8, 0, tzinfo=ZoneInfo("America/New_York"))
        result = _should_run_on_startup(
            cron_expr="0 10 * * 5",
            timezone="America/New_York",
            last_run="2026-03-20",
        )
        assert result is False

    @patch("server._now")
    def test_not_scheduled_day(self, mock_now):
        """It's Wednesday — most recent scheduled time was last Friday."""
        mock_now.return_value = datetime(2026, 3, 25, 12, 0, tzinfo=ZoneInfo("America/New_York"))
        result = _should_run_on_startup(
            cron_expr="0 10 * * 5",
            timezone="America/New_York",
            last_run="2026-03-20",
        )
        assert result is False

    @patch("server._now")
    def test_missed_by_multiple_weeks(self, mock_now):
        """last_run is from weeks ago — should run."""
        mock_now.return_value = datetime(2026, 3, 27, 15, 0, tzinfo=ZoneInfo("America/New_York"))
        result = _should_run_on_startup(
            cron_expr="0 10 * * 5",
            timezone="America/New_York",
            last_run="2026-03-06",
        )
        assert result is True


@pytest.mark.asyncio
@patch("server.run_pipeline", new_callable=AsyncMock)
@patch("server._should_run_on_startup", return_value=True)
@patch("server.settings")
async def test_lifespan_triggers_pipeline_on_missed_run(mock_settings, mock_check, mock_pipeline):
    """If startup check detects missed run, pipeline runs."""
    from server import lifespan

    mock_settings.schedule_cron = "0 10 * * 5"
    mock_settings.schedule_timezone = "America/New_York"
    mock_settings.movie_state_path = "/tmp/nonexistent.json"

    app = MagicMock()
    async with lifespan(app):
        pass

    mock_pipeline.assert_called_once_with(mock_settings)


@pytest.mark.asyncio
@patch("server.run_pipeline", new_callable=AsyncMock)
@patch("server._should_run_on_startup", return_value=False)
@patch("server.settings")
async def test_lifespan_skips_pipeline_when_not_missed(mock_settings, mock_check, mock_pipeline):
    """If startup check says no miss, pipeline does not run."""
    from server import lifespan

    mock_settings.schedule_cron = "0 10 * * 5"
    mock_settings.schedule_timezone = "America/New_York"
    mock_settings.movie_state_path = "/tmp/nonexistent.json"

    app = MagicMock()
    async with lifespan(app):
        pass

    mock_pipeline.assert_not_called()


@pytest.mark.asyncio
@patch("server.sys.exit")
async def test_watchdog_exits_when_scheduler_dead(mock_exit):
    """Watchdog calls sys.exit when scheduler is not running."""
    from server import _scheduler_watchdog

    scheduler = MagicMock()
    scheduler.running = False

    task = asyncio.create_task(_scheduler_watchdog(scheduler, check_interval=0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    mock_exit.assert_called_with(1)


@pytest.mark.asyncio
@patch("server.sys.exit")
async def test_watchdog_does_not_exit_when_scheduler_alive(mock_exit):
    """Watchdog does not exit when scheduler is running."""
    from server import _scheduler_watchdog

    scheduler = MagicMock()
    scheduler.running = True

    task = asyncio.create_task(_scheduler_watchdog(scheduler, check_interval=0.01))
    await asyncio.sleep(0.05)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    mock_exit.assert_not_called()
