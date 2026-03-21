import re

import httpx

_STRIP_PATTERNS = [
    r"\s+in\s+IMAX$",
    r"\s+IMAX$",
    r"\s+3D$",
    r"\s*\(\d{4}\)$",
]


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str):
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def search_movie(self, title: str) -> dict | None:
        async with httpx.AsyncClient(headers=self._headers, timeout=10) as client:
            result = await self._search(client, title)
            if result:
                return result

            stripped = title
            for pattern in _STRIP_PATTERNS:
                stripped = re.sub(pattern, "", stripped, flags=re.IGNORECASE)
            if stripped != title:
                result = await self._search(client, stripped)
                if result:
                    return result

            words = title.split()[:3]
            if len(words) >= 3:
                short_title = " ".join(words)
                if short_title != title and short_title != stripped:
                    result = await self._search(client, short_title)
                    if result:
                        return result

            return None

    async def _search(self, client: httpx.AsyncClient, query: str) -> dict | None:
        from datetime import datetime

        resp = await client.get(
            f"{self.BASE_URL}/search/movie",
            params={"query": query, "year": datetime.now().year},
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None

    async def get_movie_details(self, movie_id: int) -> dict:
        async with httpx.AsyncClient(headers=self._headers, timeout=10) as client:
            resp = await client.get(
                f"{self.BASE_URL}/movie/{movie_id}",
                params={"append_to_response": "credits,release_dates"},
            )
            resp.raise_for_status()
            data = resp.json()

            crew = data.get("credits", {}).get("crew", [])
            director = next((c["name"] for c in crew if c["job"] == "Director"), None)

            cast_list = data.get("credits", {}).get("cast", [])
            cast = [c["name"] for c in cast_list[:4]]

            genres = [g["name"] for g in data.get("genres", [])]

            # Use US theatrical release date if available, fall back to generic
            release_date = data.get("release_date")
            us_theatrical = self._get_us_theatrical_date(data)
            if us_theatrical:
                release_date = us_theatrical

            runtime = data.get("runtime")
            mpaa_rating = self._get_us_certification(data)

            return {
                "imdb_id": data.get("imdb_id"),
                "director": director,
                "cast": cast,
                "genres": genres,
                "release_date": release_date,
                "runtime": runtime,
                "mpaa_rating": mpaa_rating,
            }

    @staticmethod
    def _get_us_certification(data: dict) -> str | None:
        """Extract MPAA rating from TMDB release_dates data."""
        for country in data.get("release_dates", {}).get("results", []):
            if country.get("iso_3166_1") != "US":
                continue
            for preferred_type in (3, 2):
                for release in country.get("release_dates", []):
                    if release.get("type") == preferred_type and release.get("certification"):
                        return release["certification"]
        return None

    @staticmethod
    def _get_us_theatrical_date(data: dict) -> str | None:
        """Extract US theatrical release date from TMDB release_dates data.

        TMDB release types: 1=Premiere, 2=Theatrical (limited), 3=Theatrical,
        4=Digital, 5=Physical, 6=TV
        """
        for country in data.get("release_dates", {}).get("results", []):
            if country.get("iso_3166_1") != "US":
                continue
            # Prefer type 3 (wide theatrical), then 2 (limited theatrical)
            for preferred_type in (3, 2):
                for release in country.get("release_dates", []):
                    if release.get("type") == preferred_type:
                        date_str = release.get("release_date", "")
                        if date_str:
                            return date_str[:10]  # "2026-03-14T00:00:00.000Z" → "2026-03-14"
        return None
