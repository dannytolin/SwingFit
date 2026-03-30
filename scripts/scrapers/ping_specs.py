import re
from bs4 import BeautifulSoup

from scripts.scrapers.base import get_browser, new_page, delay, logger

PING_DRIVERS_URL = "https://www.ping.com/en-us/clubs/drivers"


def parse_ping_card(html: str) -> dict:
    """Parse a single Ping product card HTML into a spec dict."""
    soup = BeautifulSoup(html, "html.parser")
    name_el = soup.select_one(".product-name, h3, [class*='name'], [class*='title']")
    price_el = soup.select_one(".product-price, [class*='price']")

    raw_name = name_el.get_text(strip=True) if name_el else ""
    model_name = raw_name.replace("Driver", "").replace("driver", "").strip()

    price_text = price_el.get_text(strip=True) if price_el else ""
    price_match = re.search(r"\$?([\d,]+\.?\d*)", price_text)
    msrp = float(price_match.group(1).replace(",", "")) if price_match else None

    loft_els = soup.select(".loft-options li, [class*='loft'] option, [class*='loft'] li")
    lofts = []
    for el in loft_els:
        loft_match = re.search(r"([\d.]+)", el.get_text())
        if loft_match:
            lofts.append(float(loft_match.group(1)))

    return {
        "brand": "Ping",
        "model_name": model_name,
        "club_type": "driver",
        "msrp": msrp,
        "loft": lofts[len(lofts) // 2] if lofts else None,
        "loft_range_min": min(lofts) if lofts else None,
        "loft_range_max": max(lofts) if lofts else None,
        "adjustable": len(lofts) > 1,
        "still_in_production": True,
        "model_year": 2025,
    }


async def scrape_ping_drivers() -> list[dict]:
    """Scrape current Ping drivers from ping.com."""
    clubs = []
    async with get_browser() as browser:
        page = await new_page(browser)
        logger.info("Navigating to Ping drivers page")
        try:
            await page.goto(PING_DRIVERS_URL, wait_until="networkidle", timeout=30000)
            await delay()

            cards = await page.query_selector_all(
                "[class*='product-card'], [class*='ProductCard'], .product-tile, [class*='club-card']"
            )
            logger.info(f"Found {len(cards)} product cards")

            for card in cards:
                html = await card.inner_html()
                try:
                    club = parse_ping_card(html)
                    if club["model_name"]:
                        clubs.append(club)
                except Exception as e:
                    logger.warning(f"Failed to parse Ping card: {e}")
        except Exception as e:
            logger.error(f"Ping scrape failed: {e}")
            raise
        finally:
            await page.close()

    logger.info(f"Scraped {len(clubs)} Ping drivers")
    return clubs
