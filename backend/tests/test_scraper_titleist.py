import pytest
from scripts.scrapers.titleist_specs import parse_club_card


def test_parse_club_card_extracts_fields():
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


def test_parse_club_card_missing_price():
    html = """
    <div class="product-card">
        <h3 class="product-name">GT2 Driver</h3>
        <ul class="loft-options"><li>9.0°</li></ul>
    </div>
    """
    result = parse_club_card(html)
    assert result["brand"] == "Titleist"
    assert result["model_name"] == "GT2"
    assert result["msrp"] is None


def test_parse_club_card_no_lofts():
    html = """
    <div class="product-card">
        <h3 class="product-name">TSR4 Driver</h3>
        <span class="product-price">$599.99</span>
    </div>
    """
    result = parse_club_card(html)
    assert result["loft"] is None
    assert result["adjustable"] is False
