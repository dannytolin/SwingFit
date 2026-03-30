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

    user = User(email="fit@test.com", username="fitter", hashed_password="h")
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
            launch_angle=14.0 + i * 0.2,
            spin_rate=3100.0 + i * 50,
            carry_distance=248.0 + i,
            club_speed=105.0 + i * 0.5,
            attack_angle=-1.2,
            face_to_path=-1.3,
            offline_distance=8.0 + i,
            smash_factor=1.42,
            shot_number=i + 1,
        )
        db.add(shot)

    clubs_data = [
        {"brand": "Titleist", "model_name": "TSR3", "model_year": 2025, "club_type": "driver",
         "loft": 9.0, "launch_bias": "low", "spin_bias": "low",
         "forgiveness_rating": 5, "workability_rating": 9,
         "swing_speed_min": 90.0, "swing_speed_max": 120.0,
         "msrp": 599.99, "avg_used_price": 380.0, "still_in_production": True},
        {"brand": "TaylorMade", "model_name": "Qi10 Max", "model_year": 2025, "club_type": "driver",
         "loft": 10.5, "launch_bias": "high", "spin_bias": "mid",
         "forgiveness_rating": 9, "workability_rating": 3,
         "swing_speed_min": 80.0, "swing_speed_max": 115.0,
         "msrp": 599.99, "avg_used_price": 450.0, "still_in_production": True},
        {"brand": "Ping", "model_name": "G430 Max", "model_year": 2023, "club_type": "driver",
         "loft": 10.5, "launch_bias": "mid", "spin_bias": "mid",
         "forgiveness_rating": 9, "workability_rating": 4,
         "swing_speed_min": 75.0, "swing_speed_max": 115.0,
         "msrp": 549.99, "avg_used_price": 300.0, "still_in_production": True},
        {"brand": "Titleist", "model_name": "T150", "model_year": 2023, "club_type": "iron",
         "loft": 33.0, "launch_bias": "mid", "spin_bias": "mid",
         "forgiveness_rating": 5, "workability_rating": 8,
         "swing_speed_min": 80.0, "swing_speed_max": 115.0,
         "msrp": 1399.99, "still_in_production": True},
    ]
    for c in clubs_data:
        db.add(ClubSpec(**c))

    db.commit()
    db.close()


def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    Base.metadata.drop_all(engine)


client = TestClient(app)


def test_get_swing_profile():
    response = client.get("/users/me/swing-profile", params={"club_type": "driver"})
    assert response.status_code == 200
    data = response.json()
    assert data["club_type"] == "driver"
    assert data["sample_size"] == 5
    assert "avg_ball_speed" in data
    assert "shot_shape_tendency" in data
    assert "data_quality" in data


def test_get_swing_profile_no_shots():
    response = client.get("/users/me/swing-profile", params={"club_type": "putter"})
    assert response.status_code == 404


def test_recommend_clubs():
    response = client.post("/fitting/recommend", json={
        "club_type": "driver",
    })
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert "profile" in data
    recs = data["recommendations"]
    assert len(recs) >= 1
    assert len(recs) <= 5
    for r in recs:
        assert r["club"]["club_type"] == "driver"
    assert all("score" in r for r in recs)
    assert all("explanation" in r for r in recs)
    scores = [r["score"] for r in recs]
    assert scores == sorted(scores, reverse=True)


def test_recommend_with_budget():
    response = client.post("/fitting/recommend", json={
        "club_type": "driver",
        "budget_max": 400.0,
        "include_used": True,
    })
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    for r in recs:
        price = r["club"].get("avg_used_price") or r["club"].get("msrp")
        assert price is not None
        assert price <= 400.0


def test_recommend_no_profile():
    response = client.post("/fitting/recommend", json={
        "club_type": "putter",
    })
    assert response.status_code == 404


def test_recommend_clubs_include_buy_links():
    response = client.post("/fitting/recommend", json={
        "club_type": "driver",
    })
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    for r in recs:
        assert "buy_links" in r
        assert isinstance(r["buy_links"], list)
