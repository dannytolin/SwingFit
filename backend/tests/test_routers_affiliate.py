from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User
from backend.app.routers.auth import get_current_user
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
    _user_id = user.id
    def _override_current_user(db: Session = Depends(get_db)):
        return db.query(User).filter(User.id == _user_id).first()
    app.dependency_overrides[get_current_user] = _override_current_user

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
    app.dependency_overrides.pop(get_current_user, None)
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
        "club_spec_id": CLUB_ID,
        "retailer": "global_golf",
        "url": "https://www.globalgolf.com/search?q=test",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["retailer"] == "global_golf"


