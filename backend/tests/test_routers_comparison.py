from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User
from backend.app.routers.auth import get_current_user
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.models.club_spec import ClubSpec

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)

USER_ID = None
CURRENT_CLUB_ID = None
RECOMMENDED_CLUB_ID = None


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

    user = User(email="compare@test.com", username="comparer", hashed_password="h")
    db.add(user)
    db.commit()
    global USER_ID
    USER_ID = user.id
    _user_id = user.id
    def _override_current_user(db: Session = Depends(get_db)):
        return db.query(User).filter(User.id == _user_id).first()
    app.dependency_overrides[get_current_user] = _override_current_user

    session = SwingSession(
        user_id=user.id,
        launch_monitor_type="trackman_4",
        data_source="file_upload",
    )
    db.add(session)
    db.commit()

    for i in range(5):
        shot = Shot(
            session_id=session.id,
            club_used="driver",
            ball_speed=149.0 + i,
            launch_angle=14.0,
            spin_rate=3100.0,
            carry_distance=248.0 + i,
            club_speed=105.0,
            offline_distance=8.0,
            smash_factor=1.42,
            shot_number=i + 1,
        )
        db.add(shot)

    current = ClubSpec(
        brand="TaylorMade", model_name="SIM2 Max", model_year=2021, club_type="driver",
        loft=10.5, launch_bias="high", spin_bias="mid",
        forgiveness_rating=8, workability_rating=4,
        swing_speed_min=80.0, swing_speed_max=115.0,
        msrp=499.99, still_in_production=False,
    )
    db.add(current)
    db.commit()
    global CURRENT_CLUB_ID
    CURRENT_CLUB_ID = current.id

    recommended = ClubSpec(
        brand="Titleist", model_name="TSR3", model_year=2025, club_type="driver",
        loft=9.0, launch_bias="low", spin_bias="low",
        forgiveness_rating=5, workability_rating=9,
        swing_speed_min=90.0, swing_speed_max=120.0,
        msrp=599.99, avg_used_price=380.0, still_in_production=True,
    )
    db.add(recommended)
    db.commit()
    global RECOMMENDED_CLUB_ID
    RECOMMENDED_CLUB_ID = recommended.id

    db.close()


def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    Base.metadata.drop_all(engine)


client = TestClient(app)


def test_compare_clubs():
    response = client.post("/fitting/compare", json={
        "club_type": "driver",
        "current_club_id": CURRENT_CLUB_ID,
        "recommended_club_id": RECOMMENDED_CLUB_ID,
    })
    assert response.status_code == 200
    data = response.json()
    assert "current" in data
    assert "recommended" in data
    assert "profile" in data
    assert "explanation" in data
    assert data["current"]["brand"] == "TaylorMade"
    assert data["recommended"]["brand"] == "Titleist"
    assert "current_score" in data
    assert "recommended_score" in data
    assert data["recommended_score"] >= 0


def test_compare_club_not_found():
    response = client.post("/fitting/compare", json={
        "club_type": "driver",
        "current_club_id": 9999,
        "recommended_club_id": RECOMMENDED_CLUB_ID,
    })
    assert response.status_code == 404
