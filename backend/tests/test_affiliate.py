from backend.app.services.affiliate import (
    AFFILIATE_CONFIGS,
    build_affiliate_url,
    get_buy_links,
)


def _make_club(**overrides) -> dict:
    defaults = {
        "id": 1,
        "brand": "TaylorMade",
        "model_name": "Qi10 Max",
        "model_year": 2025,
        "club_type": "driver",
        "msrp": 599.99,
        "avg_used_price": 450.0,
        "still_in_production": True,
    }
    defaults.update(overrides)
    return defaults


def test_affiliate_configs_have_required_keys():
    for key, config in AFFILIATE_CONFIGS.items():
        assert "base_url" in config
        assert "affiliate_network" in config
        assert "affiliate_id" in config
        assert "commission_rate" in config
        assert "supports_used" in config


def test_build_affiliate_url_global_golf():
    config = AFFILIATE_CONFIGS["global_golf"]
    club = _make_club(brand="Titleist", model_name="TSR3")
    url = build_affiliate_url(config, club)
    assert config["base_url"] in url
    assert config["affiliate_id"] in url


def test_build_affiliate_url_amazon():
    config = AFFILIATE_CONFIGS["amazon"]
    club = _make_club(brand="Ping", model_name="G430 Max")
    url = build_affiliate_url(config, club)
    assert "amazon.com" in url
    assert config["affiliate_id"] in url


def test_get_buy_links_returns_list():
    club = _make_club()
    links = get_buy_links(club)
    assert isinstance(links, list)
    assert len(links) >= 1


def test_get_buy_links_brand_restriction():
    club = _make_club(brand="Titleist")
    links = get_buy_links(club)
    retailer_names = [l["retailer"] for l in links]
    assert "callaway_preowned" not in retailer_names


def test_get_buy_links_callaway_brand_included():
    club = _make_club(brand="Callaway")
    links = get_buy_links(club)
    retailer_names = [l["retailer"] for l in links]
    assert "callaway_preowned" in retailer_names


def test_get_buy_links_used_only_retailer_excluded_for_new():
    club = _make_club(brand="TaylorMade", still_in_production=False)
    links = get_buy_links(club)
    retailer_names = [l["retailer"] for l in links]
    assert "taylormade" not in retailer_names


def test_get_buy_links_sorted_by_price():
    club = _make_club()
    links = get_buy_links(club)
    prices = [l["estimated_price"] for l in links if l["estimated_price"] is not None]
    if len(prices) >= 2:
        assert prices == sorted(prices)


def test_get_buy_links_has_required_fields():
    club = _make_club()
    links = get_buy_links(club)
    for link in links:
        assert "retailer" in link
        assert "url" in link
        assert "estimated_price" in link
        assert "condition" in link
