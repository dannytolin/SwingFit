import pytest
from pydantic import ValidationError

from backend.app.schemas.club_spec import ClubSpecCreate, ClubSpecRead, ClubSpecSearch
from backend.app.schemas.session import SwingSessionCreate, SwingSessionRead
from backend.app.schemas.shot import ShotCreate, ShotRead


def test_club_spec_create_valid():
    data = ClubSpecCreate(
        brand="TaylorMade",
        model_name="Qi10",
        model_year=2025,
        club_type="driver",
        loft=10.5,
        swing_speed_min=85.0,
        swing_speed_max=115.0,
        launch_bias="mid",
        spin_bias="low",
        forgiveness_rating=8,
        workability_rating=5,
        msrp=599.99,
        still_in_production=True,
    )
    assert data.brand == "TaylorMade"
    assert data.club_type == "driver"


def test_club_spec_create_invalid_club_type():
    with pytest.raises(ValidationError):
        ClubSpecCreate(
            brand="TaylorMade",
            model_name="Qi10",
            model_year=2025,
            club_type="bat",  # invalid
        )


def test_club_spec_search():
    search = ClubSpecSearch(brand="Titleist", club_type="driver")
    assert search.brand == "Titleist"
    assert search.swing_speed is None


def test_shot_create_valid():
    shot = ShotCreate(
        club_used="driver",
        ball_speed=149.8,
        launch_angle=12.3,
        spin_rate=2845.0,
        carry_distance=248.0,
        shot_number=1,
    )
    assert shot.ball_speed == 149.8
    assert shot.is_valid is True


def test_session_create_valid():
    session = SwingSessionCreate(
        launch_monitor_type="trackman_4",
        data_source="file_upload",
        session_date="2025-06-15T10:00:00Z",
    )
    assert session.launch_monitor_type == "trackman_4"
