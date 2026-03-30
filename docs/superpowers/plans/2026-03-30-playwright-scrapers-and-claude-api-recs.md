# Playwright Scrapers + Claude API Recommendations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static club database and scoring algorithm with automated Playwright scrapers that keep club data fresh and a Claude API recommendation engine that provides expert-quality fitting advice.

**Architecture:** Two independent subsystems. (A) Playwright scrapers in `scripts/scrapers/` that run on demand to populate `club_specs` and `price_cache` tables. (B) A Claude API service in `backend/app/services/claude_fitter.py` that replaces the deterministic scoring in `fitting_engine.py` with LLM-powered recommendations, cached in a `recommendations` table. The swing profile computation (`compute_swing_profile`) is unchanged — only what happens after profile computation changes.

**Tech Stack:** Playwright (headless Chromium), Anthropic Python SDK (claude-sonnet-4-20250514), FastAPI, SQLAlchemy, SQLite, React/TypeScript frontend.

---

## Part A: Playwright Scrapers

### Task 1: Add Playwright dependency and create scraper base module

**Files:**
- Modify: `backend/requirements.txt`
- Create: `scripts/scrapers/__init__.py`
- Create: `scripts/scrapers/base.py`

- [ ] **Step 1: Add playwright to requirements.txt**

Add this line to `backend/requirements.txt`:

```
playwright==1.52.0
```

- [ ] **Step 2: Install Playwright and Chromium**

Run:
```bash
source .venv/Scripts/activate
pip install playwright==1.52.0
playwright install chromium
```

- [ ] **Step 3: Create scripts/scrapers/__init__.py**

```python
```

(Empty init file to make it a package.)

- [ ] **Step 4: Create scripts/scrapers/base.py**

```python
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
```

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt scripts/scrapers/
git commit -m "feat: add Playwright dependency and scraper base module"
```

---

### Task 2: Add scrape_logs model and review_summary column

**Files:**
- Create: `backend/app/models/scrape_log.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/club_spec.py`
- Modify: `backend/app/models/price_cache.py`

- [ ] **Step 1: Create backend/app/models/scrape_log.py**

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scraper_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # "success" or "error"
    clubs_found: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    ran_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 2: Add review_summary to ClubSpec model**

In `backend/app/models/club_spec.py`, add after the `still_in_production` field:

```python
    review_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Add `Text` to the sqlalchemy imports at the top of the file.

- [ ] **Step 3: Add is_available and product_url to PriceCache model**

In `backend/app/models/price_cache.py`, add after the `last_checked` field:

```python
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    product_url: Mapped[str | None] = mapped_column(String, nullable=True)
```

Add `Boolean` to the sqlalchemy imports.

- [ ] **Step 4: Register ScrapeLog in models/__init__.py**

```python
from backend.app.models.scrape_log import ScrapeLog
# Add to __all__ list
```

- [ ] **Step 5: Generate and run Alembic migration**

```bash
cd backend && ../.venv/Scripts/python.exe -m alembic revision --autogenerate -m "add scrape_logs table, review_summary, price_cache fields"
```

Review the migration. If SQLite constraint issues arise, edit to use `batch_alter_table`. Then run:

```bash
../.venv/Scripts/python.exe -m alembic upgrade head
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/ backend/alembic/
git commit -m "feat: add scrape_logs model, review_summary column, price_cache fields"
```

---

### Task 3: Titleist specs scraper

**Files:**
- Create: `scripts/scrapers/titleist_specs.py`
- Create: `backend/tests/test_scraper_titleist.py`

- [ ] **Step 1: Write the test**

```python
import pytest
from scripts.scrapers.titleist_specs import parse_club_card


def test_parse_club_card_extracts_fields():
    """Test that a mock club card HTML produces the expected dict."""
    html = """
    <div class="product-card">
        <h3 class="product-name">TSR3 Driver</h3>
        <span class="product-price">$599.99</span>
        <span class="product-year">2025</span>
        <ul class="loft-options"><li>8.0°</li><li>9.0°</li><li>10.0°</li></ul>
    </div>
    """
    result = parse_club_card(html)
    assert result["brand"] == "Titleist"
    assert result["model_name"] == "TSR3"
    assert result["club_type"] == "driver"
    assert result["msrp"] == 599.99
    assert "9.0" in str(result["loft"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest backend/tests/test_scraper_titleist.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Create scripts/scrapers/titleist_specs.py**

```python
import re
from bs4 import BeautifulSoup

from scripts.scrapers.base import get_browser, new_page, delay, logger, utc_now

TITLEIST_DRIVERS_URL = "https://www.titleist.com/golf-clubs/drivers"


def parse_club_card(html: str) -> dict:
    """Parse a single club product card HTML into a spec dict."""
    soup = BeautifulSoup(html, "html.parser")
    name_el = soup.select_one(".product-name, h3, [class*='name']")
    price_el = soup.select_one(".product-price, [class*='price']")

    raw_name = name_el.get_text(strip=True) if name_el else ""
    model_name = raw_name.replace("Driver", "").replace("driver", "").strip()

    price_text = price_el.get_text(strip=True) if price_el else ""
    price_match = re.search(r"\$?([\d,]+\.?\d*)", price_text)
    msrp = float(price_match.group(1).replace(",", "")) if price_match else None

    loft_els = soup.select(".loft-options li, [class*='loft'] option")
    lofts = []
    for el in loft_els:
        loft_match = re.search(r"([\d.]+)", el.get_text())
        if loft_match:
            lofts.append(float(loft_match.group(1)))

    return {
        "brand": "Titleist",
        "model_name": model_name,
        "club_type": "driver",
        "msrp": msrp,
        "loft": lofts[len(lofts) // 2] if lofts else None,  # middle loft as default
        "loft_range_min": min(lofts) if lofts else None,
        "loft_range_max": max(lofts) if lofts else None,
        "adjustable": len(lofts) > 1,
        "still_in_production": True,
        "model_year": 2025,
    }


async def scrape_titleist_drivers() -> list[dict]:
    """Scrape current Titleist drivers from titleist.com."""
    clubs = []
    async with get_browser() as browser:
        page = await new_page(browser)
        logger.info("Navigating to Titleist drivers page")
        try:
            await page.goto(TITLEIST_DRIVERS_URL, wait_until="networkidle", timeout=30000)
            await delay()

            cards = await page.query_selector_all("[class*='product-card'], [class*='ProductCard'], .product-tile")
            logger.info(f"Found {len(cards)} product cards")

            for card in cards:
                html = await card.inner_html()
                try:
                    club = parse_club_card(html)
                    if club["model_name"]:
                        clubs.append(club)
                except Exception as e:
                    logger.warning(f"Failed to parse card: {e}")
        except Exception as e:
            logger.error(f"Titleist scrape failed: {e}")
            raise
        finally:
            await page.close()

    logger.info(f"Scraped {len(clubs)} Titleist drivers")
    return clubs
```

- [ ] **Step 4: Add beautifulsoup4 to requirements.txt**

```
beautifulsoup4==4.13.4
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest backend/tests/test_scraper_titleist.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/scrapers/titleist_specs.py backend/tests/test_scraper_titleist.py backend/requirements.txt
git commit -m "feat: add Titleist driver specs scraper with Playwright"
```

---

### Task 4: TaylorMade and Callaway specs scrapers

**Files:**
- Create: `scripts/scrapers/taylormade_specs.py`
- Create: `scripts/scrapers/callaway_specs.py`

- [ ] **Step 1: Create scripts/scrapers/taylormade_specs.py**

Follow the same pattern as Titleist. Target URL: `https://www.taylormadegolf.com/drivers/`. Extract model name, MSRP, loft options. The page structure will differ — use Playwright to wait for product tiles to render, then parse with BeautifulSoup. Set `brand = "TaylorMade"`.

- [ ] **Step 2: Create scripts/scrapers/callaway_specs.py**

Same pattern. Target URL: `https://www.callawaygolf.com/golf-clubs/drivers/`. Set `brand = "Callaway"`.

- [ ] **Step 3: Commit**

```bash
git add scripts/scrapers/taylormade_specs.py scripts/scrapers/callaway_specs.py
git commit -m "feat: add TaylorMade and Callaway driver specs scrapers"
```

---

### Task 5: GlobalGolf price scraper

**Files:**
- Create: `scripts/scrapers/globalgolf_prices.py`
- Create: `backend/tests/test_scraper_globalgolf.py`

- [ ] **Step 1: Write the test**

```python
from scripts.scrapers.globalgolf_prices import parse_search_results


def test_parse_search_results():
    html = """
    <div class="product-result">
        <span class="product-title">Titleist TSR3 Driver</span>
        <span class="price-new">$549.99</span>
        <span class="price-used">$379.99</span>
        <a class="product-link" href="/titleist-tsr3-driver/p-123456">View</a>
    </div>
    """
    results = parse_search_results(html, club_spec_id=1)
    assert len(results) >= 1
    assert results[0]["retailer"] == "global_golf"
    assert results[0]["price"] > 0
    assert results[0]["condition"] in ("new", "used")
```

- [ ] **Step 2: Create scripts/scrapers/globalgolf_prices.py**

```python
import re
from bs4 import BeautifulSoup

from scripts.scrapers.base import get_browser, new_page, delay, logger

GLOBALGOLF_SEARCH_URL = "https://www.globalgolf.com/search/?q={query}"


def parse_search_results(html: str, club_spec_id: int) -> list[dict]:
    """Parse GlobalGolf search results into price_cache entries."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    price_new_el = soup.select_one("[class*='price-new'], [class*='newPrice']")
    price_used_el = soup.select_one("[class*='price-used'], [class*='usedPrice']")
    link_el = soup.select_one("a[class*='product-link'], a[href*='/p-']")

    base_url = "https://www.globalgolf.com"
    product_url = base_url + link_el["href"] if link_el and link_el.get("href") else None

    for el, condition in [(price_new_el, "new"), (price_used_el, "used")]:
        if el:
            price_match = re.search(r"\$?([\d,]+\.?\d*)", el.get_text())
            if price_match:
                results.append({
                    "club_spec_id": club_spec_id,
                    "retailer": "global_golf",
                    "price": float(price_match.group(1).replace(",", "")),
                    "condition": condition,
                    "product_url": product_url,
                    "is_available": True,
                })

    return results


async def scrape_globalgolf_prices(clubs: list[dict]) -> list[dict]:
    """Search GlobalGolf for pricing on each club in the list.

    Each club dict should have: id, brand, model_name, club_type.
    Returns list of price_cache entries.
    """
    all_prices = []
    async with get_browser() as browser:
        page = await new_page(browser)
        for club in clubs:
            query = f"{club['brand']} {club['model_name']} {club['club_type']}"
            url = GLOBALGOLF_SEARCH_URL.format(query=query.replace(" ", "+"))
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await delay()
                content = await page.content()
                prices = parse_search_results(content, club_spec_id=club["id"])
                all_prices.extend(prices)
                logger.info(f"Found {len(prices)} prices for {club['brand']} {club['model_name']}")
            except Exception as e:
                logger.warning(f"Failed to scrape prices for {club['brand']} {club['model_name']}: {e}")
        await page.close()

    return all_prices
```

- [ ] **Step 3: Run tests**

Run: `.venv/Scripts/python.exe -m pytest backend/tests/test_scraper_globalgolf.py -v`

- [ ] **Step 4: Commit**

```bash
git add scripts/scrapers/globalgolf_prices.py backend/tests/test_scraper_globalgolf.py
git commit -m "feat: add GlobalGolf price scraper"
```

---

### Task 6: MyGolfSpy review scraper

**Files:**
- Create: `scripts/scrapers/mygolfspy_reviews.py`

- [ ] **Step 1: Create scripts/scrapers/mygolfspy_reviews.py**

```python
import re
from bs4 import BeautifulSoup

from scripts.scrapers.base import get_browser, new_page, delay, logger

MYGOLFSPY_SEARCH = "https://mygolfspy.com/?s={query}"


def extract_review_text(html: str, max_chars: int = 1500) -> str | None:
    """Extract the first ~1000 words of review content."""
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("article, .entry-content, .post-content, [class*='review-body']")
    if not article:
        return None
    text = article.get_text(separator=" ", strip=True)
    # Trim to max_chars, break at word boundary
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "..."
    return text


async def scrape_mygolfspy_reviews(clubs: list[dict]) -> dict[int, str]:
    """Scrape MyGolfSpy reviews for each club.

    Returns: {club_spec_id: review_summary_text}
    """
    reviews = {}
    async with get_browser() as browser:
        page = await new_page(browser)
        for club in clubs:
            query = f"{club['brand']} {club['model_name']} review"
            url = MYGOLFSPY_SEARCH.format(query=query.replace(" ", "+"))
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await delay()
                # Click first search result
                first_result = await page.query_selector("article a, .search-result a, h2 a")
                if first_result:
                    await first_result.click()
                    await page.wait_for_load_state("networkidle")
                    await delay()
                    content = await page.content()
                    review = extract_review_text(content)
                    if review:
                        reviews[club["id"]] = review
                        logger.info(f"Got review for {club['brand']} {club['model_name']} ({len(review)} chars)")
                    else:
                        logger.info(f"No review content found for {club['brand']} {club['model_name']}")
                else:
                    logger.info(f"No search results for {club['brand']} {club['model_name']}")
            except Exception as e:
                logger.warning(f"Failed to scrape review for {club['brand']} {club['model_name']}: {e}")
        await page.close()

    return reviews
```

- [ ] **Step 2: Commit**

```bash
git add scripts/scrapers/mygolfspy_reviews.py
git commit -m "feat: add MyGolfSpy review scraper"
```

---

### Task 7: Scraper orchestrator (run_all.py)

**Files:**
- Create: `scripts/scrapers/run_all.py`

- [ ] **Step 1: Create scripts/scrapers/run_all.py**

```python
"""Orchestrator: run all scrapers, upsert results, log outcomes."""

import asyncio
import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models.club_spec import ClubSpec
from backend.app.models.price_cache import PriceCache
from backend.app.models.scrape_log import ScrapeLog
from scripts.scrapers.base import logger, utc_now
from scripts.scrapers.titleist_specs import scrape_titleist_drivers
from scripts.scrapers.taylormade_specs import scrape_taylormade_drivers
from scripts.scrapers.callaway_specs import scrape_callaway_drivers
from scripts.scrapers.globalgolf_prices import scrape_globalgolf_prices
from scripts.scrapers.mygolfspy_reviews import scrape_mygolfspy_reviews


def upsert_club(db: Session, club_data: dict) -> ClubSpec:
    """Insert or update a club spec by brand + model_name + model_year."""
    existing = db.query(ClubSpec).filter(
        ClubSpec.brand == club_data["brand"],
        ClubSpec.model_name == club_data["model_name"],
        ClubSpec.model_year == club_data.get("model_year", 2025),
        ClubSpec.club_type == club_data["club_type"],
    ).first()
    if existing:
        for key, val in club_data.items():
            if val is not None:
                setattr(existing, key, val)
        return existing
    club = ClubSpec(**club_data)
    db.add(club)
    return club


def upsert_price(db: Session, price_data: dict):
    """Insert or update a price cache entry."""
    existing = db.query(PriceCache).filter(
        PriceCache.club_spec_id == price_data["club_spec_id"],
        PriceCache.retailer == price_data["retailer"],
        PriceCache.condition == price_data["condition"],
    ).first()
    if existing:
        existing.price = price_data["price"]
        existing.product_url = price_data.get("product_url")
        existing.is_available = price_data.get("is_available", True)
        existing.last_checked = utc_now()
    else:
        db.add(PriceCache(**price_data))


def log_scrape(db: Session, scraper_name: str, status: str, clubs_found: int = 0, errors: str | None = None):
    db.add(ScrapeLog(scraper_name=scraper_name, status=status, clubs_found=clubs_found, errors=errors))
    db.commit()


async def run_all():
    db = SessionLocal()
    try:
        # --- OEM Spec Scrapers ---
        for scraper_name, scraper_fn in [
            ("titleist_specs", scrape_titleist_drivers),
            ("taylormade_specs", scrape_taylormade_drivers),
            ("callaway_specs", scrape_callaway_drivers),
        ]:
            try:
                logger.info(f"Running {scraper_name}...")
                clubs = await scraper_fn()
                for club_data in clubs:
                    upsert_club(db, club_data)
                db.commit()
                log_scrape(db, scraper_name, "success", clubs_found=len(clubs))
            except Exception as e:
                logger.error(f"{scraper_name} failed: {e}")
                db.rollback()
                log_scrape(db, scraper_name, "error", errors=str(e))

        # --- Price Scraper ---
        try:
            logger.info("Running globalgolf_prices...")
            all_clubs = db.query(ClubSpec).filter(ClubSpec.club_type == "driver").all()
            club_dicts = [{"id": c.id, "brand": c.brand, "model_name": c.model_name, "club_type": c.club_type} for c in all_clubs]
            prices = await scrape_globalgolf_prices(club_dicts)
            for price_data in prices:
                upsert_price(db, price_data)
            db.commit()
            log_scrape(db, "globalgolf_prices", "success", clubs_found=len(prices))
        except Exception as e:
            logger.error(f"globalgolf_prices failed: {e}")
            db.rollback()
            log_scrape(db, "globalgolf_prices", "error", errors=str(e))

        # --- Review Scraper ---
        try:
            logger.info("Running mygolfspy_reviews...")
            all_clubs = db.query(ClubSpec).filter(ClubSpec.club_type == "driver").all()
            club_dicts = [{"id": c.id, "brand": c.brand, "model_name": c.model_name} for c in all_clubs]
            reviews = await scrape_mygolfspy_reviews(club_dicts)
            for club_id, review_text in reviews.items():
                club = db.query(ClubSpec).filter(ClubSpec.id == club_id).first()
                if club:
                    club.review_summary = review_text
            db.commit()
            log_scrape(db, "mygolfspy_reviews", "success", clubs_found=len(reviews))
        except Exception as e:
            logger.error(f"mygolfspy_reviews failed: {e}")
            db.rollback()
            log_scrape(db, "mygolfspy_reviews", "error", errors=str(e))

        logger.info("All scrapers complete.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_all())
```

- [ ] **Step 2: Commit**

```bash
git add scripts/scrapers/run_all.py
git commit -m "feat: add scraper orchestrator (run_all.py)"
```

---

## Part B: Claude API Recommendation Engine

### Task 8: Add recommendation and api_usage models

**Files:**
- Create: `backend/app/models/recommendation.py`
- Create: `backend/app/models/api_usage.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/config.py`

- [ ] **Step 1: Create backend/app/models/recommendation.py**

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    club_type: Mapped[str] = mapped_column(String, nullable=False)
    club_spec_id: Mapped[int] = mapped_column(Integer, nullable=False)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    projected_changes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    best_for: Mapped[str | None] = mapped_column(String, nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 2: Create backend/app/models/api_usage.py**

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ApiUsage(Base):
    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 3: Register models in __init__.py**

Add to `backend/app/models/__init__.py`:

```python
from backend.app.models.recommendation import Recommendation
from backend.app.models.api_usage import ApiUsage
```

Update `__all__` to include both.

- [ ] **Step 4: Add anthropic_api_key to config.py**

In `backend/app/config.py`, add to the Settings class:

```python
    anthropic_api_key: str = ""
```

- [ ] **Step 5: Add ANTHROPIC_API_KEY to .env**

Add to root `.env`:

```
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

- [ ] **Step 6: Generate and run migration**

```bash
cd backend && ../.venv/Scripts/python.exe -m alembic revision --autogenerate -m "add recommendations and api_usage tables"
```

Fix any SQLite batch_alter_table issues. Then:

```bash
../.venv/Scripts/python.exe -m alembic upgrade head
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/ backend/app/config.py backend/alembic/ .env
git commit -m "feat: add recommendation cache and API usage tracking models"
```

---

### Task 9: Create Claude fitter service

**Files:**
- Create: `backend/app/services/claude_fitter.py`
- Create: `backend/tests/test_claude_fitter.py`

- [ ] **Step 1: Write the test**

```python
import json
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.claude_fitter import build_fitting_prompt, parse_claude_response
from backend.app.services.swing_profile import SwingProfile


def _sample_profile() -> SwingProfile:
    return SwingProfile(
        club_type="driver",
        avg_club_speed=105.0,
        avg_ball_speed=149.8,
        avg_launch_angle=14.2,
        avg_spin_rate=3100.0,
        avg_carry=248.0,
        avg_attack_angle=-1.2,
        avg_club_path=2.1,
        avg_face_angle=0.8,
        std_carry=8.5,
        std_offline=12.0,
        shot_shape_tendency="fade",
        miss_direction="right",
        smash_factor=1.42,
        spin_loft_estimate=15.4,
        sample_size=50,
        data_quality="high",
        data_quality_tier="platinum",
        shot_count=50,
    )


def _sample_clubs() -> list[dict]:
    return [
        {
            "id": 1, "brand": "Titleist", "model_name": "TSR3",
            "model_year": 2025, "club_type": "driver", "loft": 9.0,
            "launch_bias": "low", "spin_bias": "low",
            "forgiveness_rating": 5, "workability_rating": 9,
            "swing_speed_min": 90.0, "swing_speed_max": 120.0,
            "msrp": 599.99, "avg_used_price": 380.0,
            "review_summary": "The TSR3 is a low-spin option for better players.",
        },
    ]


def test_build_fitting_prompt_contains_profile_data():
    prompt = build_fitting_prompt(_sample_profile(), _sample_clubs())
    assert "105.0" in prompt  # club speed
    assert "3100" in prompt or "3,100" in prompt  # spin rate
    assert "TSR3" in prompt  # club name


def test_parse_claude_response_valid_json():
    raw = json.dumps([{
        "club_spec_id": 1,
        "match_score": 94,
        "explanation": "Great fit for your swing.",
        "projected_changes": {"spin_delta": "-400 to -600 rpm"},
        "best_for": "Low spin seekers",
    }])
    result = parse_claude_response(raw)
    assert len(result) == 1
    assert result[0]["match_score"] == 94
    assert result[0]["club_spec_id"] == 1


def test_parse_claude_response_extracts_json_from_text():
    """Claude may wrap JSON in markdown code fences."""
    raw = "Here are the recommendations:\n```json\n" + json.dumps([{
        "club_spec_id": 1, "match_score": 90,
        "explanation": "Good fit.", "projected_changes": {},
        "best_for": "All-around",
    }]) + "\n```"
    result = parse_claude_response(raw)
    assert len(result) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest backend/tests/test_claude_fitter.py -v`

- [ ] **Step 3: Create backend/app/services/claude_fitter.py**

```python
import json
import re
from dataclasses import asdict

import anthropic

from backend.app.config import settings
from backend.app.services.swing_profile import SwingProfile

MODEL = "claude-sonnet-4-20250514"

# Cost per 1M tokens (Sonnet 4)
INPUT_COST_PER_M = 3.0
OUTPUT_COST_PER_M = 15.0

FITTING_SYSTEM_PROMPT = """You are an expert golf club fitter with 20 years of experience at top fitting studios. You combine deep technical knowledge of launch monitor data with editorial insight from testing hundreds of club models.

Your job: given a golfer's swing profile and a list of candidate clubs, recommend the top 5 clubs ranked by fit quality.

Rules:
- Reference the golfer's specific numbers in every explanation (e.g., "Your 3,100 rpm spin rate is 600 rpm above the optimal 2,500 rpm window for your 105 mph club speed")
- Write in a conversational, editorial tone — like a knowledgeable friend, not a data readout
- Consider real fitting principles: optimal launch/spin windows vary by swing speed, higher MOI helps inconsistent ball strikers, attack angle affects spin, forgiveness matters for high-dispersion players
- Projected changes should use conservative ranges ("8-12 yards") not exact numbers
- Return ONLY valid JSON — no markdown, no commentary outside the JSON array

Optimal windows by club type:
- Driver: launch 12-15°, spin 2000-2500 rpm (varies by speed: faster swings need less spin)
- 3-wood: launch 11-14°, spin 3000-4000 rpm
- 7-iron: launch 16-20°, spin 6000-7000 rpm
- PW: launch 24-28°, spin 8000-9500 rpm

Return a JSON array of objects with these exact fields:
- club_spec_id (int): the id of the club from the candidate list
- match_score (int, 0-100): how well this club fits the golfer
- explanation (string): 2-3 sentence editorial explanation referencing the golfer's numbers
- projected_changes (object): keys like "spin_delta", "carry_delta", "launch_delta" with string range values
- best_for (string): one-line tag like "Low spin seekers with above-average speed"
"""


def build_fitting_prompt(profile: SwingProfile, clubs: list[dict]) -> str:
    """Build the user message containing the golfer's profile and candidate clubs."""
    profile_dict = asdict(profile)

    clubs_text = ""
    for c in clubs:
        clubs_text += f"\n- ID {c['id']}: {c['brand']} {c['model_name']} ({c.get('model_year', '?')})"
        clubs_text += f"\n  Loft: {c.get('loft', '?')}° | Launch bias: {c.get('launch_bias', '?')} | Spin bias: {c.get('spin_bias', '?')}"
        clubs_text += f"\n  Forgiveness: {c.get('forgiveness_rating', '?')}/10 | Workability: {c.get('workability_rating', '?')}/10"
        clubs_text += f"\n  Speed range: {c.get('swing_speed_min', '?')}-{c.get('swing_speed_max', '?')} mph"
        clubs_text += f"\n  MSRP: ${c.get('msrp', '?')} | Used: ${c.get('avg_used_price', '?')}"
        if c.get("review_summary"):
            clubs_text += f"\n  Review: {c['review_summary'][:300]}"

    return f"""## Golfer's Swing Profile ({profile.club_type})

- Club Speed: {profile.avg_club_speed} mph
- Ball Speed: {profile.avg_ball_speed} mph
- Launch Angle: {profile.avg_launch_angle}°
- Spin Rate: {profile.avg_spin_rate} rpm
- Carry Distance: {profile.avg_carry} yd
- Attack Angle: {profile.avg_attack_angle}°
- Club Path: {profile.avg_club_path}°
- Face Angle: {profile.avg_face_angle}°
- Carry Std Dev: {profile.std_carry} yd
- Offline Std Dev: {profile.std_offline} yd
- Shot Shape: {profile.shot_shape_tendency}
- Miss Direction: {profile.miss_direction}
- Smash Factor: {profile.smash_factor}
- Sample Size: {profile.sample_size} shots
- Data Quality: {profile.data_quality}

## Candidate Clubs
{clubs_text}

Recommend the top 5 clubs from this list, ranked by fit. Return only the JSON array."""


def parse_claude_response(raw_text: str) -> list[dict]:
    """Extract and parse the JSON array from Claude's response."""
    # Try direct parse first
    text = raw_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from code fences
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1).strip())

    # Try finding array brackets
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"Could not parse Claude response as JSON: {text[:200]}")


def call_claude_for_recommendations(
    profile: SwingProfile,
    clubs: list[dict],
) -> tuple[list[dict], dict]:
    """Call Claude API for fitting recommendations.

    Returns: (recommendations_list, usage_dict)
    usage_dict has keys: input_tokens, output_tokens, estimated_cost
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    user_message = build_fitting_prompt(profile, clubs)

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=FITTING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text
    recommendations = parse_claude_response(raw_text)

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "estimated_cost": round(
            (response.usage.input_tokens / 1_000_000 * INPUT_COST_PER_M)
            + (response.usage.output_tokens / 1_000_000 * OUTPUT_COST_PER_M),
            4,
        ),
    }

    return recommendations, usage


COMPARE_SYSTEM_PROMPT = """You are an expert golf club fitter. Compare two clubs for this specific golfer's swing profile. Write a detailed side-by-side analysis in a conversational tone, referencing the golfer's specific numbers. Return only valid JSON.

Return a JSON object with these fields:
- current_analysis (string): 2-3 sentences about how the current club performs for this golfer
- recommended_analysis (string): 2-3 sentences about how the recommended club would perform
- key_differences (array of strings): 3-5 bullet points comparing the clubs
- projected_improvement (string): one sentence with conservative estimated gains
- verdict (string): one sentence recommendation
"""


def call_claude_for_comparison(
    profile: SwingProfile,
    current_club: dict,
    recommended_club: dict,
) -> tuple[dict, dict]:
    """Call Claude API for club comparison.

    Returns: (comparison_dict, usage_dict)
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    profile_dict = asdict(profile)
    user_message = f"""## Golfer's Swing Profile
{json.dumps(profile_dict, indent=2)}

## Current Club
{json.dumps(current_club, indent=2)}

## Recommended Club
{json.dumps(recommended_club, indent=2)}

Provide a side-by-side comparison. Return only the JSON object."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=COMPARE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text
    comparison = parse_claude_response(raw_text)
    # parse_claude_response returns a list, but compare returns a single object
    if isinstance(comparison, list):
        comparison = comparison[0] if comparison else {}

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "estimated_cost": round(
            (response.usage.input_tokens / 1_000_000 * INPUT_COST_PER_M)
            + (response.usage.output_tokens / 1_000_000 * OUTPUT_COST_PER_M),
            4,
        ),
    }

    return comparison, usage
```

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python.exe -m pytest backend/tests/test_claude_fitter.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/claude_fitter.py backend/tests/test_claude_fitter.py
git commit -m "feat: add Claude fitter service with prompt builder and response parser"
```

---

### Task 10: Update fitting router to use Claude API

**Files:**
- Modify: `backend/app/routers/fitting.py`
- Create: `backend/tests/test_routers_fitting_claude.py`

- [ ] **Step 1: Write the test**

```python
import json
from unittest.mock import patch, MagicMock

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.models.club_spec import ClubSpec
from backend.app.routers.auth import get_current_user

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine)

_user_id = None


def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module():
    app.dependency_overrides[get_db] = _override_get_db
    Base.metadata.create_all(engine)
    db = TestSession()

    user = User(email="claude_test@test.com", username="ct", hashed_password="")
    db.add(user)
    db.commit()
    global _user_id
    _user_id = user.id

    def _override_current_user(db: Session = Depends(get_db)):
        return db.query(User).filter(User.id == _user_id).first()
    app.dependency_overrides[get_current_user] = _override_current_user

    session = SwingSession(user_id=user.id, launch_monitor_type="trackman_4", data_source="file_upload")
    db.add(session)
    db.commit()
    for i in range(5):
        db.add(Shot(session_id=session.id, club_used="driver", ball_speed=149.0+i,
                     launch_angle=14.0, spin_rate=3100.0, carry_distance=248.0+i,
                     club_speed=105.0, offline_distance=8.0, smash_factor=1.42, shot_number=i+1))
    db.add(ClubSpec(brand="Titleist", model_name="TSR3", model_year=2025, club_type="driver",
                    loft=9.0, launch_bias="low", spin_bias="low", forgiveness_rating=5,
                    workability_rating=9, swing_speed_min=90.0, swing_speed_max=120.0,
                    msrp=599.99, still_in_production=True))
    db.commit()
    db.close()


def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    Base.metadata.drop_all(engine)


client = TestClient(app)

MOCK_CLAUDE_RECS = [
    {"club_spec_id": 1, "match_score": 94, "explanation": "Great fit.",
     "projected_changes": {"spin_delta": "-400 rpm"}, "best_for": "Low spin"}
]


@patch("backend.app.routers.fitting.call_claude_for_recommendations")
def test_recommend_calls_claude(mock_call):
    mock_call.return_value = (MOCK_CLAUDE_RECS, {"input_tokens": 500, "output_tokens": 300, "estimated_cost": 0.006})
    response = client.post("/fitting/recommend", json={"club_type": "driver"})
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) >= 1
    assert data["recommendations"][0]["match_score"] == 94
    mock_call.assert_called_once()
```

- [ ] **Step 2: Rewrite backend/app/routers/fitting.py**

Replace the `recommend_clubs` function to call Claude instead of `score_club` / `rank_recommendations`. Keep the hard-filter logic. Add a `GET /fitting/recommendations` endpoint that reads from cache.

Key changes:
- `POST /fitting/recommend` now calls `call_claude_for_recommendations` instead of `score_club`
- Saves results to the `Recommendation` model
- Logs usage to `ApiUsage`
- Falls back to cached recommendations if Claude fails
- `GET /fitting/recommendations` reads cached recommendations without an API call
- `POST /fitting/compare` now calls `call_claude_for_comparison`

The existing `score_club` and `rank_recommendations` functions in `fitting_engine.py` remain untouched as fallback/legacy code.

- [ ] **Step 3: Run tests**

Run: `.venv/Scripts/python.exe -m pytest backend/tests/test_routers_fitting_claude.py -v`

- [ ] **Step 4: Run ALL tests to check for regressions**

Run: `.venv/Scripts/python.exe -m pytest backend/tests/ -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/fitting.py backend/tests/test_routers_fitting_claude.py
git commit -m "feat: replace static scoring with Claude API recommendations"
```

---

### Task 11: Update frontend to use cached recommendations

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/ShopPage.tsx`

- [ ] **Step 1: Add getCachedRecommendations to api.ts**

Add to `frontend/src/lib/api.ts`:

```typescript
export async function getCachedRecommendations(clubType: string) {
  const res = await authFetch(
    `${API_URL}/fitting/recommendations?club_type=${encodeURIComponent(clubType)}`
  );
  if (!res.ok) {
    if (res.status === 404) return null;
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to fetch cached recommendations');
  }
  return res.json();
}
```

- [ ] **Step 2: Update ShopPage.tsx to try cache first**

In `ShopPage.tsx`, update the React Query hook to first call `getCachedRecommendations`. If it returns null (no cache), show a "Generate Recommendations" button that calls `getRecommendations` (which triggers Claude). Show a loading state: "Finding your perfect clubs..."

- [ ] **Step 3: Verify frontend builds**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/pages/ShopPage.tsx
git commit -m "feat: wire frontend to cached + generated recommendations"
```

---

### Task 12: Final verification and push

- [ ] **Step 1: Run all backend tests**

```bash
.venv/Scripts/python.exe -m pytest backend/tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Verify frontend builds**

```bash
cd frontend && npx tsc --noEmit && npx vite build
```

- [ ] **Step 3: Commit process map update**

```bash
git add SwingFit_ProcessMap.md docs/superpowers/plans/
git commit -m "docs: update process map sections 2.2 (Playwright scrapers) and 2.3 (Claude API recs)"
```

- [ ] **Step 4: Push all commits**

```bash
git push origin main
```
