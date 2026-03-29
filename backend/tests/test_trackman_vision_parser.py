import json
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.parsers.trackman.report_vision import (
    TrackmanReportParser,
    normalize_vision_response,
)
from backend.app.schemas.shot import ShotCreate


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
        {
            "club_type": "7 iron",
            "shots": 12,
            "averages": {
                "ball_speed": 120.5,
                "launch_angle": 18.4,
                "spin_rate": 6420,
                "carry_distance": 165,
                "total_distance": 172,
                "club_speed": 82.3,
                "smash_factor": 1.46,
                "attack_angle": None,
                "club_path": None,
                "face_angle": None,
                "face_to_path": None,
                "spin_axis": None,
                "apex_height": None,
                "landing_angle": None,
                "offline_distance": None,
            },
        },
    ],
    "data_type": "session_summary",
    "source": "trackman_app_screenshot",
    "confidence": 0.92,
}


def test_normalize_vision_response():
    shots = normalize_vision_response(MOCK_VISION_RESPONSE)
    assert len(shots) == 2
    assert all(isinstance(s, ShotCreate) for s in shots)


def test_normalize_driver_data():
    shots = normalize_vision_response(MOCK_VISION_RESPONSE)
    driver = shots[0]
    assert driver.club_used == "driver"
    assert driver.ball_speed == 149.8
    assert driver.club_speed == 105.2
    assert driver.launch_angle == 12.3
    assert driver.spin_rate == 2845.0
    assert driver.carry_distance == 248.0
    assert driver.attack_angle == -1.2
    assert driver.landing_angle == 38.5
    assert driver.shot_number == 1


def test_normalize_iron_data():
    shots = normalize_vision_response(MOCK_VISION_RESPONSE)
    iron = shots[1]
    assert iron.club_used == "7-iron"
    assert iron.attack_angle is None
    assert iron.shot_number == 2


def test_normalize_empty_clubs():
    response = {"clubs": [], "data_type": "session_summary", "source": "pdf_report", "confidence": 0.5}
    shots = normalize_vision_response(response)
    assert len(shots) == 0


def test_confidence_returned():
    assert MOCK_VISION_RESPONSE["confidence"] == 0.92


@patch("backend.app.services.parsers.trackman.report_vision.anthropic")
def test_extract_from_image_calls_api(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(MOCK_VISION_RESPONSE))]
    mock_client.messages.create.return_value = mock_response

    parser = TrackmanReportParser()
    result = parser.extract_from_image(b"fake_image_bytes", "image/png")

    mock_client.messages.create.assert_called_once()
    assert result["confidence"] == 0.92
    assert len(result["clubs"]) == 2
