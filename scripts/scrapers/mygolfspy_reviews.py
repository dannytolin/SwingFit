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
