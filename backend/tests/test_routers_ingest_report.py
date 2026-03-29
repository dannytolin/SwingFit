import io
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User

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


MOCK_VISION_RESPONSE = {
    "clubs": [
        {
            "club_type": "driver",
            "shots": 24,
            "averages": {
                "club_speed": 105.2,
                "ball_speed": 149.8,
                "launch_angle": 12.3,
                "spin_rate": 2845,
                "carry_distance": 248,
                "total_distance": 271,
                "attack_angle": -1.2,
                "club_path": 2.1,
                "face_angle": 0.8,
                "face_to_path": -1.3,
                "spin_axis": 3.2,
                "apex_height": 98,
                "landing_angle": 38.5,
                "offline_distance": 8,
                "smash_factor": 1.42,
            },
        },
    ],
    "data_type": "session_summary",
    "source": "trackman_app_screenshot",
    "confidence": 0.92,
}


def setup_module():
    app.dependency_overrides[get_db] = _override_get_db
    Base.metadata.create_all(engine)
    db = TestSession()
    user = User(email="report_test@example.com", username="reporter", hashed_password="h")
    db.add(user)
    db.commit()
    db.refresh(user)
    global USER_ID
    USER_ID = user.id
    db.close()


def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)


client = TestClient(app)


@patch("backend.app.routers.ingest.TrackmanReportParser")
def test_upload_trackman_report_image(MockParser):
    mock_instance = MagicMock()
    mock_instance.extract_from_image.return_value = MOCK_VISION_RESPONSE
    MockParser.return_value = mock_instance

    fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    response = client.post(
        f"/ingest/trackman-report?user_id={USER_ID}",
        files={"file": ("screenshot.png", io.BytesIO(fake_image), "image/png")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["session"]["launch_monitor_type"] == "trackman_4"
    assert data["session"]["data_source"] == "ocr_vision"
    assert data["shot_count"] == 1
    assert data["confidence"] == 0.92
    assert data["data_quality"]["tier"] == "silver"


@patch("backend.app.routers.ingest.TrackmanReportParser")
def test_upload_trackman_report_low_confidence(MockParser):
    low_confidence_response = {**MOCK_VISION_RESPONSE, "confidence": 0.5}
    mock_instance = MagicMock()
    mock_instance.extract_from_image.return_value = low_confidence_response
    MockParser.return_value = mock_instance

    fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    response = client.post(
        f"/ingest/trackman-report?user_id={USER_ID}",
        files={"file": ("blurry.png", io.BytesIO(fake_image), "image/png")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["confidence"] == 0.5
    assert data["low_confidence_warning"] is True
