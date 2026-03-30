from scripts.scrapers.ping_specs import parse_ping_card
from scripts.scrapers.cobra_specs import parse_cobra_card
from scripts.scrapers.second_swing_prices import parse_second_swing_results


def test_parse_ping_card():
    html = """
    <div class="product-card">
        <h3 class="product-name">G430 Max 10K Driver</h3>
        <span class="product-price">$599.99</span>
        <ul class="loft-options"><li>9.0°</li><li>10.5°</li></ul>
    </div>
    """
    result = parse_ping_card(html)
    assert result["brand"] == "Ping"
    assert "G430" in result["model_name"]
    assert result["msrp"] == 599.99
    assert result["adjustable"] is True


def test_parse_cobra_card():
    html = """
    <div class="product-card">
        <h3 class="product-name">Darkspeed LS Driver</h3>
        <span class="product-price">$449.99</span>
        <ul class="loft-options"><li>9.0°</li></ul>
    </div>
    """
    result = parse_cobra_card(html)
    assert result["brand"] == "Cobra"
    assert "Darkspeed" in result["model_name"]
    assert result["msrp"] == 449.99


def test_parse_second_swing_new_and_used():
    html = """
    <div class="product-card">
        <span class="product-price">$349.99</span>
        <a href="/product/titleist-tsr3">TSR3</a>
        <span>Used - Good condition</span>
    </div>
    <div class="product-card">
        <span class="product-price">$549.99</span>
        <a href="/product/titleist-tsr3-new">TSR3</a>
        <span>New</span>
    </div>
    """
    results = parse_second_swing_results(html, club_spec_id=1)
    assert len(results) >= 1
    for r in results:
        assert r["retailer"] == "second_swing"
        assert r["price"] > 0
        assert r["condition"] in ("new", "used", "like_new")


def test_parse_second_swing_empty():
    html = "<div>No results found</div>"
    results = parse_second_swing_results(html, club_spec_id=1)
    assert len(results) == 0
