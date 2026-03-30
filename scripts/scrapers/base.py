import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger("scrapers")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


def random_ua() -> str:
    return random.choice(USER_AGENTS)


async def delay(min_sec: float = 2.0, max_sec: float = 3.5):
    """Polite delay between page loads."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


@asynccontextmanager
async def get_browser():
    """Yield a headless Chromium browser instance."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            await browser.close()


async def new_page(browser: Browser) -> Page:
    """Create a new page with a random User-Agent."""
    context = await browser.new_context(user_agent=random_ua())
    page = await context.new_page()
    return page


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
