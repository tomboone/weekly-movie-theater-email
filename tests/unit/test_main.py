from unittest.mock import AsyncMock, patch

import pytest

from main import enrich_movie, run_pipeline


def _make_settings(monkeypatch, tmp_path, **overrides):
    monkeypatch.setenv("REGAL_CINEMA_ID", "0336")
    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    monkeypatch.setenv("ACS_CONNECTION_STRING", "endpoint=https://test.azure.com/;accesskey=dGVzdA==")
    monkeypatch.setenv("EMAIL_FROM", "from@example.com")
    monkeypatch.setenv("EMAIL_TO", "to@example.com")
    monkeypatch.setenv("MOVIE_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setenv("EXCLUDE_PATTERNS", overrides.get("exclude_patterns", ""))

    from config import Settings

    return Settings(_env_file=None)  # type: ignore[reportCallIssue]


@pytest.mark.asyncio
async def test_enrich_movie_returns_enriched_dict():
    tmdb = AsyncMock()
    tmdb.search_movie.return_value = {"id": 1, "release_date": "2026-03-14"}
    tmdb.get_movie_details.return_value = {
        "imdb_id": "tt1234567",
        "director": "Jane Doe",
        "cast": ["Actor A", "Actor B"],
        "genres": ["Action"],
        "release_date": "2026-03-14",
        "runtime": 120,
        "mpaa_rating": "PG-13",
    }

    result = await enrich_movie("Test Movie", 5, tmdb, "2026-03-14")

    assert result is not None
    assert result["title"] == "Test Movie (2026)"
    assert result["showtime_count"] == 5
    assert result["imdb_url"] == "https://www.imdb.com/title/tt1234567/"
    assert result["director"] == "Jane Doe"
    assert result["runtime"] == 120
    assert result["mpaa_rating"] == "PG-13"


@pytest.mark.asyncio
async def test_enrich_movie_no_tmdb_match():
    tmdb = AsyncMock()
    tmdb.search_movie.return_value = None

    result = await enrich_movie("Unknown Movie", 1, tmdb, "2026-03-14")

    assert result is None


@pytest.mark.asyncio
async def test_enrich_movie_no_imdb_id():
    tmdb = AsyncMock()
    tmdb.search_movie.return_value = {"id": 1, "release_date": "2026-01-01"}
    tmdb.get_movie_details.return_value = {
        "imdb_id": None,
        "director": None,
        "cast": [],
        "genres": [],
        "release_date": "2026-01-01",
        "runtime": None,
        "mpaa_rating": None,
    }

    result = await enrich_movie("No IMDB", 1, tmdb, "2026-03-14")

    assert result is not None
    assert result["imdb_url"] is None


@pytest.mark.asyncio
async def test_enrich_movie_no_release_year():
    tmdb = AsyncMock()
    tmdb.search_movie.return_value = {"id": 1, "release_date": ""}
    tmdb.get_movie_details.return_value = {
        "imdb_id": "tt0000001",
        "director": None,
        "cast": [],
        "genres": [],
        "release_date": None,
        "runtime": None,
        "mpaa_rating": None,
    }

    result = await enrich_movie("No Year", 1, tmdb, "2026-03-14")

    assert result is not None
    assert result["title"] == "No Year"


@pytest.mark.asyncio
@patch("main.send_email", new_callable=AsyncMock)
@patch("main.get_regal_showtimes", new_callable=AsyncMock)
async def test_pipeline_sends_email_for_new_movies(mock_scrape, mock_email, monkeypatch, tmp_path):
    settings = _make_settings(monkeypatch, tmp_path)
    mock_scrape.return_value = [
        {"title": "New Movie", "showtime_count": 3},
    ]

    with patch("main.TMDBClient") as mock_tmdb_cls:
        tmdb = AsyncMock()
        mock_tmdb_cls.return_value = tmdb
        tmdb.search_movie.return_value = {"id": 1, "release_date": "2026-03-14"}
        tmdb.get_movie_details.return_value = {
            "imdb_id": "tt1234567",
            "director": "Dir",
            "cast": ["A"],
            "genres": ["Drama"],
            "release_date": "2026-03-14",
            "runtime": 100,
            "mpaa_rating": "R",
        }

        await run_pipeline(settings)

    mock_email.assert_called_once()


@pytest.mark.asyncio
@patch("main.send_email", new_callable=AsyncMock)
@patch("main.get_regal_showtimes", new_callable=AsyncMock)
async def test_pipeline_skips_email_when_no_new_movies(mock_scrape, mock_email, monkeypatch, tmp_path):
    settings = _make_settings(monkeypatch, tmp_path)

    # First run — establishes state
    mock_scrape.return_value = [{"title": "Old Movie", "showtime_count": 2}]
    with patch("main.TMDBClient") as mock_tmdb_cls:
        tmdb = AsyncMock()
        mock_tmdb_cls.return_value = tmdb
        tmdb.search_movie.return_value = {"id": 1, "release_date": "2026-01-01"}
        tmdb.get_movie_details.return_value = {
            "imdb_id": "tt0000001",
            "director": "D",
            "cast": [],
            "genres": [],
            "release_date": "2026-01-01",
            "runtime": 90,
            "mpaa_rating": "PG",
        }
        await run_pipeline(settings)

    mock_email.reset_mock()

    # Second run — same movies, no new ones
    await run_pipeline(settings)

    mock_email.assert_not_called()


@pytest.mark.asyncio
@patch("main.send_email", new_callable=AsyncMock)
@patch("main.get_regal_showtimes", new_callable=AsyncMock)
async def test_pipeline_excludes_filtered_movies(mock_scrape, mock_email, monkeypatch, tmp_path):
    settings = _make_settings(monkeypatch, tmp_path, exclude_patterns="Met Opera")
    mock_scrape.return_value = [
        {"title": "Met Opera: Carmen", "showtime_count": 1},
    ]

    with patch("main.TMDBClient") as mock_tmdb_cls:
        tmdb = AsyncMock()
        mock_tmdb_cls.return_value = tmdb

        await run_pipeline(settings)

    # Movie was filtered, no enrichment, no email
    tmdb.search_movie.assert_not_called()
    mock_email.assert_not_called()


@pytest.mark.asyncio
@patch("main.send_email", new_callable=AsyncMock)
@patch("main.get_regal_showtimes", new_callable=AsyncMock)
async def test_pipeline_saves_state(mock_scrape, mock_email, monkeypatch, tmp_path):
    settings = _make_settings(monkeypatch, tmp_path)
    mock_scrape.return_value = [{"title": "Movie A", "showtime_count": 1}]

    with patch("main.TMDBClient") as mock_tmdb_cls:
        tmdb = AsyncMock()
        mock_tmdb_cls.return_value = tmdb
        tmdb.search_movie.return_value = {"id": 1, "release_date": "2026-03-14"}
        tmdb.get_movie_details.return_value = {
            "imdb_id": "tt0000001",
            "director": "D",
            "cast": [],
            "genres": [],
            "release_date": "2026-03-14",
            "runtime": 90,
            "mpaa_rating": "PG",
        }

        await run_pipeline(settings)

    from state import load_state

    state = load_state(str(tmp_path / "state.json"))
    assert "Movie A" in state["movies"]
    assert state["last_run"] is not None
