import re
from bs4 import BeautifulSoup

from scripts.scrapers.base import get_browser, new_page, delay, logger

SECOND_SWING_SEARCH_URL = "https://www.2ndswing.com/search?q={query}"


def parse_second_swing_results(html: str, club_spec_id: int) -> list[dict]:
    """Parse 2nd Swing search results into price_cache entries."""
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # 2nd Swing primarily sells used clubs — look for product listings with prices
    product_cards = soup.select(
        "[class*='product-card'], [class*='product-item'], .search-result-item"
    )

    for card in product_cards:
        price_el = card.select_one("[class*='price'], .product-price")
        link_el = card.select_one("a[href*='/product/'], a[href*='/golf-clubs/']")

        if not price_el:
            continue

        price_match = re.search(r"\$?([\d,]+\.?\d*)", price_el.get_text())
        if not price_match:
            continue

        price = float(price_match.group(1).replace(",", ""))
        base_url = "https://www.2ndswing.com"
        product_url = base_url + link_el["href"] if link_el and link_el.get("href") else None

        # Determine condition from card text
        card_text = card.get_text().lower()
        if "new" in card_text and "like new" not in card_text:
            condition = "new"
        elif "like new" in card_text or "mint" in card_text:
            condition = "like_new"
        else:
            condition = "used"

        results.append({
            "club_spec_id": club_spec_id,
            "retailer": "second_swing",
            "price": price,
            "condition": condition,
            "product_url": product_url,
            "is_available": True,
        })

    # Deduplicate — keep lowest price per condition
    best_by_condition: dict[str, dict] = {}
    for r in results:
        key = r["condition"]
        if key not in best_by_condition or r["price"] < best_by_condition[key]["price"]:
            best_by_condition[key] = r

    return list(best_by_condition.values())


async def scrape_second_swing_prices(clubs: list[dict]) -> list[dict]:
    """Search 2nd Swing for pricing on each club in the list.

    Each club dict should have: id, brand, model_name, club_type.
    Returns list of price_cache entries.
    """
    all_prices = []
    async with get_browser() as browser:
        page = await new_page(browser)
        for club in clubs:
            query = f"{club['brand']} {club['model_name']} {club['club_type']}"
            url = SECOND_SWING_SEARCH_URL.format(query=query.replace(" ", "+"))
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await delay()
                content = await page.content()
                prices = parse_second_swing_results(content, club_spec_id=club["id"])
                all_prices.extend(prices)
                logger.info(
                    f"Found {len(prices)} prices for {club['brand']} {club['model_name']} on 2nd Swing"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to scrape 2nd Swing for {club['brand']} {club['model_name']}: {e}"
                )
        await page.close()

    return all_prices
