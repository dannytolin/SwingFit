# Phase 3: Affiliate & Purchase Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the affiliate link routing system that generates purchase URLs with tracking tags, caches pricing data, logs outbound clicks for revenue attribution, and integrates buy links into recommendation responses.

**Architecture:** An affiliate service generates parameterized purchase URLs per retailer with brand restrictions and used-club support. A PriceCache model stores manually-entered or scraped prices per club/retailer. A click tracking model logs every outbound purchase click. The buy-links endpoint returns ranked purchase options sorted by price. Recommendations are enhanced with buy links.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, Pydantic

---

### Task 1: Affiliate URL Builder Service

**Files:**
- Create: `backend/app/services/affiliate.py`
- Create: `backend/tests/test_affiliate.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_affiliate.py`:

```python
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
    # Callaway Pre-Owned only sells Callaway/Odyssey
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
    # TaylorMade direct doesn't support used clubs
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_affiliate.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `backend/app/services/affiliate.py`:

```python
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
    """Build a parameterized affiliate URL for a club at a retailer."""
    query = quote_plus(f"{club.get('brand', '')} {club.get('model_name', '')} {club.get('club_type', '')}")
    return config["url_template"].format(
        base_url=config["base_url"],
        query=query,
        affiliate_id=config["affiliate_id"],
    )


def get_buy_links(club: dict, include_used: bool = True) -> list[dict]:
    """Return ranked list of purchase options with affiliate links.

    Args:
        club: Club dict with brand, model_name, club_type, msrp, avg_used_price, still_in_production.
        include_used: Whether to include used-club retailers.

    Returns:
        List of dicts sorted by estimated_price ascending.
    """
    links = []
    for retailer_key, config in AFFILIATE_CONFIGS.items():
        # Check brand restrictions
        if config.get("brands") and club.get("brand") not in config["brands"]:
            continue
        # Skip retailers that don't support used if club is out of production
        if not config["supports_used"] and not club.get("still_in_production", True):
            continue

        url = build_affiliate_url(config, club)

        # Estimate price: use avg_used_price if available and retailer supports used
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

    # Sort by price ascending (None prices last)
    links.sort(key=lambda x: x["estimated_price"] if x["estimated_price"] is not None else float("inf"))
    return links
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_affiliate.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/affiliate.py backend/tests/test_affiliate.py
git commit -m "feat: add affiliate URL builder with retailer configs"
```

---

### Task 2: Click Tracking Model

**Files:**
- Create: `backend/app/models/click.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_models_click.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_models_click.py`:

```python
from datetime import datetime

from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.user import User
from backend.app.models.click import AffiliateClick


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)


def setup_module():
    Base.metadata.create_all(engine)


def teardown_module():
    Base.metadata.drop_all(engine)


def test_create_click():
    db = TestSession()
    user = User(email="click@test.com", username="clicker", hashed_password="h")
    db.add(user)
    db.commit()

    click = AffiliateClick(
        user_id=user.id,
        club_spec_id=1,
        retailer="global_golf",
        url="https://www.globalgolf.com/search?q=test&tag=abc",
    )
    db.add(click)
    db.commit()
    db.refresh(click)

    assert click.id is not None
    assert click.user_id == user.id
    assert click.retailer == "global_golf"
    assert isinstance(click.clicked_at, datetime)
    db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_models_click.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `backend/app/models/click.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class AffiliateClick(Base):
    __tablename__ = "affiliate_clicks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    club_spec_id: Mapped[int] = mapped_column(Integer, nullable=False)
    retailer: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 4: Update models __init__.py**

Read `backend/app/models/__init__.py` and add the AffiliateClick import. The file currently exports ClubSpec, User, SwingSession, Shot. Add AffiliateClick:

```python
from backend.app.models.club_spec import ClubSpec
from backend.app.models.user import User
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.models.click import AffiliateClick

__all__ = ["ClubSpec", "User", "SwingSession", "Shot", "AffiliateClick"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_models_click.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/click.py backend/app/models/__init__.py backend/tests/test_models_click.py
git commit -m "feat: add AffiliateClick model for click tracking"
```

---

### Task 3: PriceCache Model

**Files:**
- Create: `backend/app/models/price_cache.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_models_price_cache.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_models_price_cache.py`:

```python
from datetime import datetime

from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.price_cache import PriceCache


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_models_price_cache.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `backend/app/models/price_cache.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class PriceCache(Base):
    __tablename__ = "price_cache"
    __table_args__ = (
        UniqueConstraint("club_spec_id", "retailer", name="uq_club_retailer"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    club_spec_id: Mapped[int] = mapped_column(Integer, nullable=False)
    retailer: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    condition: Mapped[str] = mapped_column(String, nullable=False)  # "new" or "used"
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    last_checked: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 4: Update models __init__.py**

Add PriceCache import to `backend/app/models/__init__.py`:

```python
from backend.app.models.club_spec import ClubSpec
from backend.app.models.user import User
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.models.click import AffiliateClick
from backend.app.models.price_cache import PriceCache

__all__ = ["ClubSpec", "User", "SwingSession", "Shot", "AffiliateClick", "PriceCache"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_models_price_cache.py -v`
Expected: Both tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/price_cache.py backend/app/models/__init__.py backend/tests/test_models_price_cache.py
git commit -m "feat: add PriceCache model with club+retailer unique constraint"
```

---

### Task 4: Alembic Migration for New Models

**Files:**
- Create: new migration in `backend/alembic/versions/`

- [ ] **Step 1: Generate migration**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit/backend"
source ../.venv/Scripts/activate
alembic revision --autogenerate -m "add affiliate_clicks and price_cache tables"
```

- [ ] **Step 2: Run migration**

```bash
alembic upgrade head
```

- [ ] **Step 3: Verify tables exist**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
python -c "
from sqlalchemy import inspect
from backend.app.database import engine
inspector = inspect(engine)
tables = inspector.get_table_names()
assert 'affiliate_clicks' in tables, f'Missing affiliate_clicks, got: {tables}'
assert 'price_cache' in tables, f'Missing price_cache, got: {tables}'
print('New tables verified:', [t for t in tables if t in ('affiliate_clicks', 'price_cache')])
"
```

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/
git commit -m "feat: add migration for affiliate_clicks and price_cache tables"
```

---

### Task 5: Affiliate Router & Buy Links Endpoint

**Files:**
- Create: `backend/app/routers/affiliate.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_routers_affiliate.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_routers_affiliate.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User
from backend.app.models.club_spec import ClubSpec

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)

USER_ID = None
CLUB_ID = None


def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def setup_module():
    app.dependency_overrides[get_db] = _override_get_db
    Base.metadata.create_all(engine)
    db = TestSession()

    user = User(email="aff@test.com", username="affiliate", hashed_password="h")
    db.add(user)
    db.commit()
    global USER_ID
    USER_ID = user.id

    club = ClubSpec(
        brand="TaylorMade", model_name="Qi10 Max", model_year=2025, club_type="driver",
        loft=10.5, launch_bias="high", spin_bias="low",
        forgiveness_rating=9, workability_rating=3,
        swing_speed_min=80.0, swing_speed_max=115.0,
        msrp=599.99, avg_used_price=450.0, still_in_production=True,
    )
    db.add(club)
    db.commit()
    global CLUB_ID
    CLUB_ID = club.id

    db.close()


def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)


client = TestClient(app)


def test_get_buy_links():
    response = client.get(f"/clubs/{CLUB_ID}/buy-links")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    for link in data:
        assert "retailer" in link
        assert "url" in link
        assert "estimated_price" in link
        assert "condition" in link


def test_get_buy_links_club_not_found():
    response = client.get("/clubs/9999/buy-links")
    assert response.status_code == 404


def test_track_click():
    response = client.post("/affiliate/click", json={
        "user_id": USER_ID,
        "club_spec_id": CLUB_ID,
        "retailer": "global_golf",
        "url": "https://www.globalgolf.com/search?q=test",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["retailer"] == "global_golf"


def test_track_click_user_not_found():
    response = client.post("/affiliate/click", json={
        "user_id": 9999,
        "club_spec_id": CLUB_ID,
        "retailer": "amazon",
        "url": "https://www.amazon.com/test",
    })
    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_routers_affiliate.py -v`
Expected: FAIL — routes don't exist

- [ ] **Step 3: Write implementation**

Create `backend/app/routers/affiliate.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.club_spec import ClubSpec
from backend.app.models.click import AffiliateClick
from backend.app.models.user import User
from backend.app.services.affiliate import get_buy_links

router = APIRouter(tags=["affiliate"])


@router.get("/clubs/{club_id}/buy-links")
def get_club_buy_links(club_id: int, db: Session = Depends(get_db)):
    club = db.query(ClubSpec).filter(ClubSpec.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")

    club_dict = {
        "id": club.id,
        "brand": club.brand,
        "model_name": club.model_name,
        "club_type": club.club_type,
        "msrp": club.msrp,
        "avg_used_price": club.avg_used_price,
        "still_in_production": club.still_in_production,
    }
    return get_buy_links(club_dict)


class ClickTrackRequest(BaseModel):
    user_id: int
    club_spec_id: int
    retailer: str
    url: str


@router.post("/affiliate/click", status_code=201)
def track_click(req: ClickTrackRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    click = AffiliateClick(
        user_id=req.user_id,
        club_spec_id=req.club_spec_id,
        retailer=req.retailer,
        url=req.url,
    )
    db.add(click)
    db.commit()
    db.refresh(click)

    return {
        "id": click.id,
        "user_id": click.user_id,
        "club_spec_id": click.club_spec_id,
        "retailer": click.retailer,
        "clicked_at": click.clicked_at.isoformat(),
    }
```

- [ ] **Step 4: Register affiliate router in main.py**

Read `backend/app/main.py` then add:

```python
from backend.app.routers.affiliate import router as affiliate_router
# ...
app.include_router(affiliate_router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_routers_affiliate.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/affiliate.py backend/app/main.py backend/tests/test_routers_affiliate.py
git commit -m "feat: add affiliate buy-links and click tracking endpoints"
```

---

### Task 6: Integrate Buy Links into Recommendations

**Files:**
- Modify: `backend/app/routers/fitting.py`
- Modify: `backend/tests/test_routers_fitting.py`

Add buy links to each recommendation in the `/fitting/recommend` response.

- [ ] **Step 1: Add test for buy links in recommendations**

Append to `backend/tests/test_routers_fitting.py`:

```python
def test_recommend_clubs_include_buy_links():
    response = client.post("/fitting/recommend", json={
        "user_id": USER_ID,
        "club_type": "driver",
    })
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    for r in recs:
        assert "buy_links" in r
        assert isinstance(r["buy_links"], list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_routers_fitting.py::test_recommend_clubs_include_buy_links -v`
Expected: FAIL — `buy_links` not in response

- [ ] **Step 3: Add buy links to recommend endpoint**

In `backend/app/routers/fitting.py`, add the import at the top:

```python
from backend.app.services.affiliate import get_buy_links
```

Then in the `recommend_clubs` function, after the line `rec["explanation"] = generate_explanation(profile, rec["club"])`, add:

```python
        rec["buy_links"] = get_buy_links(rec["club"], include_used=req.include_used)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_routers_fitting.py -v`
Expected: All tests PASS (including new one)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/fitting.py backend/tests/test_routers_fitting.py
git commit -m "feat: include buy links in recommendation responses"
```

---

### Task 7: Full Test Suite & Integration Verification

**Files:** None new — integration verification only.

- [ ] **Step 1: Run all tests**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
source .venv/Scripts/activate
python -m pytest backend/tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: End-to-end integration test**

```bash
python -c "
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import User, ClubSpec, SwingSession, Shot
from scripts.seed_clubs import seed_clubs_from_csv

Base.metadata.create_all(engine)
db = SessionLocal()
user = User(email='e2e@test.com', username='e2e', hashed_password='h')
db.add(user)
db.commit()
uid = user.id
seed_clubs_from_csv(db, 'data/club_specs/initial_seed.csv')

session = SwingSession(user_id=uid, launch_monitor_type='trackman_4', data_source='file_upload')
db.add(session)
db.commit()
for i in range(10):
    db.add(Shot(session_id=session.id, club_used='driver',
        ball_speed=149+i, launch_angle=14.0, spin_rate=3100.0,
        carry_distance=248+i, club_speed=105.0, smash_factor=1.42,
        offline_distance=8.0+i, shot_number=i+1))
db.commit()
db.close()

client = TestClient(app)

# Buy links for a club
r = client.get('/clubs/1/buy-links')
links = r.json()
print(f'Buy links for club 1: {len(links)} retailers')
for l in links:
    print(f'  {l[\"retailer\"]}: \${l[\"estimated_price\"]} ({l[\"condition\"]})')

# Recommendations with buy links
r = client.post('/fitting/recommend', json={'user_id': uid, 'club_type': 'driver'})
recs = r.json()['recommendations']
print(f'\nTop recommendation: {recs[0][\"club\"][\"brand\"]} {recs[0][\"club\"][\"model_name\"]}')
print(f'  Score: {recs[0][\"score\"]}/100')
print(f'  Buy links: {len(recs[0][\"buy_links\"])} retailers')
for l in recs[0]['buy_links'][:2]:
    print(f'    {l[\"retailer\"]}: \${l[\"estimated_price\"]}')

# Click tracking
r = client.post('/affiliate/click', json={
    'user_id': uid, 'club_spec_id': 1,
    'retailer': 'global_golf', 'url': links[0]['url'],
})
print(f'\nClick tracked: {r.json()[\"retailer\"]} at {r.json()[\"clicked_at\"]}')

print('\nPhase 3 integration checks passed!')
"
```

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "chore: Phase 3 complete — affiliate purchase layer"
```
