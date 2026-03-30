from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User
from backend.app.routers.auth import get_current_user

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)

USER_ID = None


def setup_module():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(engine)
    db = TestSession()
    user = User(email="session_test@example.com", username="st", hashed_password="h")
    db.add(user)
    db.commit()
    db.refresh(user)
    global USER_ID
    USER_ID = user.id
    _user_id = user.id
    def _override_current_user(db: Session = Depends(get_db)):
        return db.query(User).filter(User.id == _user_id).first()
    app.dependency_overrides[get_current_user] = _override_current_user
    db.close()


def teardown_module():
    Base.metadata.drop_all(engine)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


def test_create_session():
    response = client.post("/users/me/sessions", json={
        "launch_monitor_type": "trackman_4",
        "data_source": "file_upload",
        "session_date": "2025-06-15T10:00:00Z",
        "location": "indoor",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == USER_ID
    assert data["launch_monitor_type"] == "trackman_4"


def test_add_shots_to_session():
    session_resp = client.post("/users/me/sessions", json={
        "launch_monitor_type": "garmin_r10",
        "data_source": "file_upload",
    })
    session_id = session_resp.json()["id"]

    shots = [
        {
            "club_used": "driver",
            "ball_speed": 149.8,
            "launch_angle": 12.3,
            "spin_rate": 2845.0,
            "carry_distance": 248.0,
            "total_distance": 271.0,
            "club_speed": 105.2,
            "shot_number": 1,
        },
        {
            "club_used": "driver",
            "ball_speed": 151.0,
            "launch_angle": 11.8,
            "spin_rate": 2650.0,
            "carry_distance": 255.0,
            "total_distance": 278.0,
            "club_speed": 107.1,
            "shot_number": 2,
        },
    ]
    response = client.post(f"/sessions/{session_id}/shots", json=shots)
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2
    assert data[0]["ball_speed"] == 149.8


def test_get_session_summary():
    session_resp = client.post("/users/me/sessions", json={
        "launch_monitor_type": "trackman_4",
        "data_source": "file_upload",
    })
    session_id = session_resp.json()["id"]

    shots = [
        {"club_used": "driver", "ball_speed": 150.0, "launch_angle": 12.0, "spin_rate": 2800.0, "carry_distance": 250.0, "club_speed": 105.0, "shot_number": 1},
        {"club_used": "driver", "ball_speed": 148.0, "launch_angle": 13.0, "spin_rate": 2900.0, "carry_distance": 245.0, "club_speed": 103.0, "shot_number": 2},
        {"club_used": "7-iron", "ball_speed": 120.0, "launch_angle": 18.0, "spin_rate": 6400.0, "carry_distance": 165.0, "club_speed": 82.0, "shot_number": 3},
    ]
    client.post(f"/sessions/{session_id}/shots", json=shots)

    response = client.get(f"/sessions/{session_id}/summary")
    assert response.status_code == 200
    data = response.json()

    assert "driver" in data
    assert "7-iron" in data
    assert data["driver"]["avg_ball_speed"] == 149.0
    assert data["driver"]["avg_carry"] == 247.5
    assert data["driver"]["shot_count"] == 2
    assert data["7-iron"]["shot_count"] == 1
