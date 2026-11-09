#!/usr/bin/env bash
# Smoke test for the image. image-check passes the image tag as $1.
set -euo pipefail
image=$1

# Every module the server imports resolves against the installed dependencies.
docker run --rm "$image" python -c "import server"

# The image's user (not root) can launch Chromium the way scraper/regal.py does.
docker run --rm "$image" python -c '
import asyncio

from playwright.async_api import async_playwright


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()
        await page.set_content("<title>smoke</title>")
        assert await page.title() == "smoke"
        await browser.close()


asyncio.run(main())
'

echo "smoke ok"
