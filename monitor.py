import logging
from urllib.parse import urlsplit, urlunsplit

import httpx

logger = logging.getLogger(__name__)


async def kuma_push(url: str, status: str, msg: str, ping_ms: int | None = None) -> None:
    """Report a pipeline run to an Uptime Kuma push monitor.

    No-op when url is empty. Never raises: a monitoring failure must not fail the run.
    """
    if not url:
        return
    # Kuma shows push URLs with a default "?status=up&msg=OK&ping=" query; ours replaces it.
    base = urlunsplit(urlsplit(url)._replace(query="", fragment=""))
    params = {"status": status, "msg": msg[:200]}
    if ping_ms is not None:
        params["ping"] = str(ping_ms)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(base, params=params)
            response.raise_for_status()
    except httpx.HTTPError:
        logger.warning("Kuma push failed", exc_info=True)
