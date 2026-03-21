import asyncio
import logging
from datetime import datetime

from config import Settings
from email_sender.acs import send_email
from email_sender.template import render_email
from enrichment.tmdb import TMDBClient
from filters import apply_pre_enrichment_filters, categorize_movie
from scraper.regal import get_regal_showtimes
from state import diff_movies, load_state, save_state

logger = logging.getLogger(__name__)


async def enrich_movie(
    title: str,
    showtime_count: int,
    tmdb: TMDBClient,
    current_date: str,
) -> dict | None:
    search_result = await tmdb.search_movie(title)
    if not search_result:
        logger.warning("TMDB: no match for '%s', skipping", title)
        return None

    movie_id = search_result["id"]
    release_year = search_result.get("release_date", "")[:4] or None
    details = await tmdb.get_movie_details(movie_id)

    imdb_url = f"https://www.imdb.com/title/{details['imdb_id']}/" if details.get("imdb_id") else None

    display_title = f"{title} ({release_year})" if release_year else title

    movie = {
        "title": display_title,
        "showtime_count": showtime_count,
        "imdb_url": imdb_url,
        "director": details.get("director"),
        "cast": details.get("cast", []),
        "genres": details.get("genres", []),
        "release_date": details.get("release_date"),
        "runtime": details.get("runtime"),
        "mpaa_rating": details.get("mpaa_rating"),
    }

    category = categorize_movie(movie, current_date=current_date)
    movie["category"] = category
    movie["is_rerelease"] = category == "rerelease"

    return movie


async def run_pipeline(settings: Settings | None = None, date_override: str | None = None) -> None:
    if settings is None:
        settings = Settings()  # type: ignore[reportCallIssue]

    logger.info("Starting movie pipeline")

    current_date = datetime.now().strftime("%Y-%m-%d")
    display_date = datetime.now().strftime("%B %d, %Y")

    # 1. Scrape
    regal_movies = await get_regal_showtimes(settings.regal_cinema_id, date=date_override)
    current_titles = [m["title"] for m in regal_movies]
    title_to_showtimes = {m["title"]: m["showtime_count"] for m in regal_movies}
    logger.info("Scraped %d movies from Regal", len(regal_movies))

    # 2. Diff
    state = load_state(settings.movie_state_path)
    new_titles = diff_movies(state["movies"], current_titles)
    logger.info("Found %d new movies", len(new_titles))

    if not new_titles and not settings.send_empty_email:
        logger.info("No new movies and SEND_EMPTY_EMAIL=false, skipping")
        save_state(settings.movie_state_path, current_date, current_titles)
        return

    # 3. Pre-enrichment filtering
    new_movies_raw = [{"title": t, "showtime_count": title_to_showtimes.get(t, 0)} for t in new_titles]
    included, excluded = apply_pre_enrichment_filters(new_movies_raw, settings.exclude_patterns)
    logger.info("After filtering: %d included, %d excluded", len(included), len(excluded))

    # 4. Enrich
    tmdb = TMDBClient(api_key=settings.tmdb_api_key)

    enrichment_tasks = [enrich_movie(m["title"], m["showtime_count"], tmdb, current_date) for m in included]
    enriched = await asyncio.gather(*enrichment_tasks, return_exceptions=True)
    for result in enriched:
        if isinstance(result, Exception):
            logger.error("Movie enrichment failed: %s", result)
    enriched = [m for m in enriched if isinstance(m, dict)]

    # 5. Log results
    logger.info("Enriched %d movies", len(enriched))

    # 6. Render and send
    if not enriched and not settings.send_empty_email:
        logger.info("No new movies to send, skipping email")
        save_state(settings.movie_state_path, current_date, current_titles)
        return

    html = render_email(
        new_movies=enriched,
        date=display_date,
    )
    subject = f"New Movies at Regal This Week — {display_date}"

    await send_email(
        connection_string=settings.acs_connection_string,
        sender=settings.email_from,
        recipient=settings.email_to,
        subject=subject,
        html_body=html,
    )
    logger.info("Email sent successfully")

    # 7. Save state (last — retry-safe)
    save_state(settings.movie_state_path, current_date, current_titles)
    logger.info("State saved")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    asyncio.run(run_pipeline())
