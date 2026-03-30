from scripts.scrapers.globalgolf_prices import parse_search_results


def test_parse_search_results_new_and_used():
    html = """
    <div class="product-result">
        <span class="product-title">Titleist TSR3 Driver</span>
        <span class="price-new">$549.99</span>
        <span class="price-used">$379.99</span>
        <a class="product-link" href="/titleist-tsr3-driver/p-123456">View</a>
    </div>
    """
    results = parse_search_results(html, club_spec_id=1)
    assert len(results) == 2
    new_result = [r for r in results if r["condition"] == "new"][0]
    used_result = [r for r in results if r["condition"] == "used"][0]
    assert new_result["retailer"] == "global_golf"
    assert new_result["price"] == 549.99
    assert used_result["price"] == 379.99
    assert "globalgolf.com" in new_result["product_url"]


def test_parse_search_results_new_only():
    html = """
    <div class="product-result">
        <span class="price-new">$599.99</span>
        <a class="product-link" href="/test/p-999">View</a>
    </div>
    """
    results = parse_search_results(html, club_spec_id=2)
    assert len(results) == 1
    assert results[0]["condition"] == "new"


def test_parse_search_results_no_prices():
    html = "<div class='empty'>No results</div>"
    results = parse_search_results(html, club_spec_id=3)
    assert len(results) == 0
