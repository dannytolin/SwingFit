from urllib.parse import quote_plus

AFFILIATE_CONFIGS: dict[str, dict] = {
    "global_golf": {
        "base_url": "https://www.globalgolf.com",
        "affiliate_network": "cj",
        "affiliate_id": "SWINGFIT_CJ_ID",
        "commission_rate": 0.08,
        "cookie_days": 30,
        "supports_used": True,
        "url_template": "{base_url}/search?q={query}&tag={affiliate_id}",
    },
    "callaway_preowned": {
        "base_url": "https://www.callawaygolfpreowned.com",
        "affiliate_network": "partnerize",
        "affiliate_id": "SWINGFIT_PARTNERIZE_ID",
        "commission_rate": 0.06,
        "cookie_days": 45,
        "supports_used": True,
        "brands": ["Callaway", "Odyssey"],
        "url_template": "{base_url}/search?q={query}&affiliate={affiliate_id}",
    },
    "taylormade": {
        "base_url": "https://www.taylormadegolf.com",
        "affiliate_network": "sovrn",
        "affiliate_id": "SWINGFIT_SOVRN_ID",
        "commission_rate": 0.05,
        "cookie_days": 30,
        "supports_used": False,
        "brands": ["TaylorMade"],
        "url_template": "{base_url}/search?q={query}&ref={affiliate_id}",
    },
    "second_swing": {
        "base_url": "https://www.2ndswing.com",
        "affiliate_network": "shareasale",
        "affiliate_id": "SWINGFIT_SAS_ID",
        "commission_rate": 0.07,
        "cookie_days": 30,
        "supports_used": True,
        "url_template": "{base_url}/search?q={query}&ref={affiliate_id}",
    },
    "amazon": {
        "base_url": "https://www.amazon.com",
        "affiliate_network": "associates",
        "affiliate_id": "swingfit-20",
        "commission_rate": 0.04,
        "cookie_days": 1,
        "supports_used": True,
        "url_template": "{base_url}/s?k={query}&tag={affiliate_id}",
    },
}


def build_affiliate_url(config: dict, club: dict) -> str:
    query = quote_plus(f"{club.get('brand', '')} {club.get('model_name', '')} {club.get('club_type', '')}")
    return config["url_template"].format(
        base_url=config["base_url"],
        query=query,
        affiliate_id=config["affiliate_id"],
    )


def get_buy_links(club: dict, include_used: bool = True) -> list[dict]:
    links = []
    for retailer_key, config in AFFILIATE_CONFIGS.items():
        if config.get("brands") and club.get("brand") not in config["brands"]:
            continue
        if not config["supports_used"] and not club.get("still_in_production", True):
            continue
        url = build_affiliate_url(config, club)
        if config["supports_used"] and club.get("avg_used_price") and include_used:
            price = club["avg_used_price"]
            condition = "used"
        else:
            price = club.get("msrp")
            condition = "new"
        links.append({
            "retailer": retailer_key,
            "url": url,
            "estimated_price": price,
            "condition": condition,
            "commission_rate": config["commission_rate"],
        })
    links.sort(key=lambda x: x["estimated_price"] if x["estimated_price"] is not None else float("inf"))
    return links
