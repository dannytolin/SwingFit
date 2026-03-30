import hashlib
import io

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import Session, sessionmaker

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
    user = User(email="ingest_test@example.com", username="ingester", hashed_password="h")
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
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    Base.metadata.drop_all(engine)


client = TestClient(app)

TRACKMAN_CSV = b"""Club,Club Speed (mph),Attack Angle (deg),Club Path (deg),Face Angle (deg),Face to Path (deg),Ball Speed (mph),Smash Factor,Launch Angle (deg),Launch Direction (deg),Spin Rate (rpm),Spin Axis (deg),Carry (yd),Carry Side (yd),Total (yd),Total Side (yd),Apex Height (ft),Landing Angle (deg)
Driver,105.2,-1.2,2.1,0.8,-1.3,149.8,1.42,12.3,-0.5,2845,3.2,248,8,271,12,98,38.5
Driver,107.1,-0.8,1.5,0.3,-1.2,151.0,1.41,11.8,-0.2,2650,2.1,255,4,278,6,95,37.2
"""

GARMIN_CSV = b"Club,Ball Speed (mph),Launch Angle (\xc2\xb0),Spin Rate (rpm),Carry (yd),Total (yd),Club Speed (mph),Smash Factor,Attack Angle (\xc2\xb0),Club Path (\xc2\xb0),Face Angle (\xc2\xb0)\nDriver,148.2,12.3,2845,245,268,105.2,1.41,-1.2,2.1,0.8\n"

GENERIC_CSV = b"""Club,Ball Spd,Spin,Carry,Total
Driver,149.8,2845,248,271
"""


def test_upload_trackman_csv():
    response = client.post(
        "/ingest/upload",
        files={"file": ("session.csv", io.BytesIO(TRACKMAN_CSV), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["session"]["launch_monitor_type"] == "trackman_4"
    assert data["session"]["data_source"] == "file_upload"
    assert data["shot_count"] == 2
    assert data["data_quality"]["tier"] == "platinum"


def test_upload_garmin_csv():
    response = client.post(
        "/ingest/upload",
        files={"file": ("garmin_export.csv", io.BytesIO(GARMIN_CSV), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["session"]["launch_monitor_type"] == "garmin_r10"
    assert data["shot_count"] == 1
    assert data["data_quality"]["tier"] == "silver"


def test_upload_generic_csv():
    response = client.post(
        "/ingest/upload",
        files={"file": ("unknown_monitor.csv", io.BytesIO(GENERIC_CSV), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["session"]["launch_monitor_type"] == "generic"
    assert data["shot_count"] == 1
    assert data["data_quality"]["tier"] == "bronze"


def test_upload_duplicate_rejected():
    csv_data = TRACKMAN_CSV
    client.post(
        "/ingest/upload",
        files={"file": ("session.csv", io.BytesIO(csv_data), "text/csv")},
    )
    response = client.post(
        "/ingest/upload",
        files={"file": ("session.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert response.status_code == 409
    assert "duplicate" in response.json()["detail"].lower()


def test_manual_entry():
    response = client.post(
        "/ingest/manual?club_type=Driver&ball_speed=150.0&launch_angle=12.5&spin_rate=2700&carry_distance=250",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["session"]["launch_monitor_type"] == "manual"
    assert data["session"]["data_source"] == "manual_entry"
    assert data["shot_count"] == 1
    assert data["data_quality"]["tier"] == "bronze"


def test_manual_entry_with_optional_fields():
    response = client.post(
        "/ingest/manual?club_type=7 Iron&ball_speed=120.0&launch_angle=18.0&spin_rate=6400&carry_distance=165&club_speed=82.0&total_distance=172",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["shot_count"] == 1


