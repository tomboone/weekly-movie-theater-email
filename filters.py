import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_RERELEASE_WEEKS = 10


def apply_pre_enrichment_filters(movies: list[dict], exclude_patterns: list[str]) -> tuple[list[dict], list[dict]]:
    included = []
    excluded = []
    for movie in movies:
        title = movie["title"]
        if any(pattern.lower() in title.lower() for pattern in exclude_patterns if pattern):
            logger.info("Excluding '%s' (matched exclude pattern)", title)
            excluded.append(movie)
        else:
            included.append(movie)
    return included, excluded


def categorize_movie(movie: dict, current_date: str) -> str:
    current = datetime.strptime(current_date, "%Y-%m-%d")

    release_date = movie.get("release_date")
    if release_date:
        try:
            release = datetime.strptime(release_date, "%Y-%m-%d")
            if current - release > timedelta(weeks=_RERELEASE_WEEKS):
                return "rerelease"
        except ValueError:
            pass

    return "new"
