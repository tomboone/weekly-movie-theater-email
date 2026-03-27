import httpx
import pytest
import respx

from enrichment.tmdb import TMDBClient


@pytest.fixture
def tmdb():
    return TMDBClient(api_key="test-key")


@respx.mock
@pytest.mark.asyncio
async def test_tmdb_search_movie(tmdb):
    respx.get("https://api.themoviedb.org/3/search/movie").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"id": 123, "title": "Test Movie", "release_date": "2026-03-14", "genre_ids": [28, 12]}]},
        )
    )

    result = await tmdb.search_movie("Test Movie")
    assert result["id"] == 123
    assert result["title"] == "Test Movie"


@respx.mock
@pytest.mark.asyncio
async def test_tmdb_search_movie_no_results(tmdb):
    respx.get("https://api.themoviedb.org/3/search/movie").mock(return_value=httpx.Response(200, json={"results": []}))

    result = await tmdb.search_movie("Nonexistent Movie")
    assert result is None


@respx.mock
@pytest.mark.asyncio
async def test_tmdb_search_strips_suffixes(tmdb):
    route = respx.get("https://api.themoviedb.org/3/search/movie")
    route.side_effect = [
        httpx.Response(200, json={"results": []}),
        httpx.Response(
            200, json={"results": [{"id": 456, "title": "Cool Movie", "release_date": "2026-03-14", "genre_ids": []}]}
        ),
    ]

    result = await tmdb.search_movie("Cool Movie in IMAX")
    assert result["id"] == 456


@respx.mock
@pytest.mark.asyncio
async def test_tmdb_get_movie_details(tmdb):
    respx.get("https://api.themoviedb.org/3/movie/123").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 123,
                "imdb_id": "tt1234567",
                "genres": [{"id": 28, "name": "Action"}, {"id": 12, "name": "Adventure"}],
                "release_date": "2025-09-01",
                "credits": {
                    "crew": [
                        {"job": "Director", "name": "Jane Director"},
                        {"job": "Producer", "name": "Bob Producer"},
                    ],
                    "cast": [
                        {"name": "Actor One", "order": 0},
                        {"name": "Actor Two", "order": 1},
                        {"name": "Actor Three", "order": 2},
                        {"name": "Actor Four", "order": 3},
                        {"name": "Actor Five", "order": 4},
                    ],
                },
                "release_dates": {
                    "results": [
                        {
                            "iso_3166_1": "US",
                            "release_dates": [
                                {"type": 3, "release_date": "2026-03-14T00:00:00.000Z"},
                            ],
                        }
                    ]
                },
            },
        )
    )

    details = await tmdb.get_movie_details(123)
    assert details["imdb_id"] == "tt1234567"
    assert details["director"] == "Jane Director"
    assert details["cast"] == ["Actor One", "Actor Two", "Actor Three", "Actor Four"]
    assert details["genres"] == ["Action", "Adventure"]
    assert details["release_date"] == "2026-03-14"  # US theatrical, not the generic 2025-09-01


@respx.mock
@pytest.mark.asyncio
async def test_tmdb_get_movie_details_no_director(tmdb):
    respx.get("https://api.themoviedb.org/3/movie/123").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 123,
                "imdb_id": "tt1234567",
                "genres": [],
                "release_date": "2026-01-01",
                "credits": {
                    "crew": [{"job": "Producer", "name": "Bob"}],
                    "cast": [],
                },
            },
        )
    )

    details = await tmdb.get_movie_details(123)
    assert details["director"] is None
    assert details["cast"] == []
