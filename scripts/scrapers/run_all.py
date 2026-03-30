"""Orchestrator: run all scrapers, upsert results, log outcomes."""

import asyncio
import sys
import os

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
from scripts.scrapers.ping_specs import scrape_ping_drivers
from scripts.scrapers.cobra_specs import scrape_cobra_drivers
from scripts.scrapers.globalgolf_prices import scrape_globalgolf_prices
from scripts.scrapers.second_swing_prices import scrape_second_swing_prices
from scripts.scrapers.mygolfspy_reviews import scrape_mygolfspy_reviews


def upsert_club(db: Session, club_data: dict) -> ClubSpec:
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
        for scraper_name, scraper_fn in [
            ("titleist_specs", scrape_titleist_drivers),
            ("taylormade_specs", scrape_taylormade_drivers),
            ("callaway_specs", scrape_callaway_drivers),
            ("ping_specs", scrape_ping_drivers),
            ("cobra_specs", scrape_cobra_drivers),
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

        # --- 2nd Swing Prices ---
        try:
            logger.info("Running second_swing_prices...")
            all_clubs = db.query(ClubSpec).filter(ClubSpec.club_type == "driver").all()
            club_dicts = [{"id": c.id, "brand": c.brand, "model_name": c.model_name, "club_type": c.club_type} for c in all_clubs]
            prices = await scrape_second_swing_prices(club_dicts)
            for price_data in prices:
                upsert_price(db, price_data)
            db.commit()
            log_scrape(db, "second_swing_prices", "success", clubs_found=len(prices))
        except Exception as e:
            logger.error(f"second_swing_prices failed: {e}")
            db.rollback()
            log_scrape(db, "second_swing_prices", "error", errors=str(e))

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
