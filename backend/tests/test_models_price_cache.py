from datetime import datetime
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.price_cache import PriceCache

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine)

def setup_module():
    Base.metadata.create_all(engine)

def teardown_module():
    Base.metadata.drop_all(engine)

def test_create_price_cache():
    db = TestSession()
    cache = PriceCache(
        club_spec_id=1,
        retailer="global_golf",
        price=380.00,
        condition="used",
        url="https://www.globalgolf.com/clubs/titleist-tsr3",
    )
    db.add(cache)
    db.commit()
    db.refresh(cache)
    assert cache.id is not None
    assert cache.price == 380.00
    assert cache.condition == "used"
    assert isinstance(cache.last_checked, datetime)
    db.close()

def test_price_cache_unique_constraint():
    db = TestSession()
    c1 = PriceCache(club_spec_id=2, retailer="amazon", price=599.99, condition="new")
    db.add(c1)
    db.commit()
    c2 = PriceCache(club_spec_id=2, retailer="amazon", price=549.99, condition="new")
    db.add(c2)
    try:
        db.commit()
        assert False, "Should have raised IntegrityError"
    except Exception:
        db.rollback()
    db.close()
