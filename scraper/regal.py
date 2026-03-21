import json
import logging
import re
from datetime import datetime, timedelta

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)


def _next_friday() -> str:
    today = datetime.now()
    weekday = today.weekday()
    days_ahead = 4 - weekday if weekday <= 4 else -(weekday - 4)
    friday = today + timedelta(days=days_ahead)
    return friday.strftime("%m-%d-%Y")


async def get_regal_showtimes(cinema_id: str, date: str | None = None) -> list[dict]:
    if date is None:
        date = _next_friday()

    url = (
        f"https://www.regmovies.com/api/getShowtimes"
        f"?theatres={cinema_id}&date={date}&hoCode=&ignoreCache=false&moviesOnly=false"
    )
    logger.info("Scraping Regal showtimes: cinema=%s date=%s", cinema_id, date)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        response = await page.goto(url, wait_until="networkidle", timeout=30000)
        if response is None:
            await browser.close()
            raise ValueError("Navigation to Regal API returned no response")
        raw_text = await response.text()
        await browser.close()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"<pre>(.*?)</pre>", raw_text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
        else:
            logger.error("Could not parse Regal API response: %s", raw_text[:500])
            raise ValueError("Could not parse Regal API response") from None

    movies = []
    shows = data.get("shows", [])
    if shows:
        for film in shows[0].get("Film", []):
            title = film.get("Title")
            performances = film.get("Performances", [])
            if title:
                movies.append(
                    {
                        "title": title,
                        "showtime_count": len(performances),
                    }
                )

    logger.info("Found %d movies at Regal cinema %s", len(movies), cinema_id)
    return movies
