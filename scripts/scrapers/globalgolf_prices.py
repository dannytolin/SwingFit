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
