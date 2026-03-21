import pytest

from scraper.regal import get_regal_showtimes


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scrape_regal_returns_movies():
    """Integration test — requires network and Playwright browsers."""
    movies = await get_regal_showtimes("0336")
    assert isinstance(movies, list)
    assert len(movies) > 0
    assert "title" in movies[0]
    assert "showtime_count" in movies[0]
