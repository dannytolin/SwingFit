import pytest

from backend.app.services.parsers.trackman.csv_export import parse_trackman_csv
from backend.app.schemas.shot import ShotCreate


def _read_sample() -> str:
    with open("data/sample_sessions/trackman_sample.csv") as f:
        return f.read()


def test_parse_trackman_csv_returns_shots():
    shots = parse_trackman_csv(_read_sample())
    assert len(shots) == 4
    assert all(isinstance(s, ShotCreate) for s in shots)


def test_parse_trackman_csv_driver_data():
    shots = parse_trackman_csv(_read_sample())
    driver_shots = [s for s in shots if s.club_used == "driver"]
    assert len(driver_shots) == 2
    first = driver_shots[0]
    assert first.club_speed == 105.2
    assert first.attack_angle == -1.2
    assert first.club_path == 2.1
    assert first.face_angle == 0.8
    assert first.face_to_path == -1.3
    assert first.ball_speed == 149.8
    assert first.smash_factor == 1.42
    assert first.launch_angle == 12.3
    assert first.spin_rate == 2845.0
    assert first.spin_axis == 3.2
    assert first.carry_distance == 248.0
    assert first.offline_distance == 8.0
    assert first.total_distance == 271.0
    assert first.apex_height == 98.0
    assert first.landing_angle == 38.5


def test_parse_trackman_csv_club_normalization():
    shots = parse_trackman_csv(_read_sample())
    clubs = [s.club_used for s in shots]
    assert "driver" in clubs
    assert "7-iron" in clubs
    assert "PW" in clubs


def test_parse_trackman_csv_shot_numbers():
    shots = parse_trackman_csv(_read_sample())
    numbers = [s.shot_number for s in shots]
    assert numbers == [1, 2, 3, 4]


def test_parse_trackman_csv_metric():
    metric_csv = """Club,Club Speed (m/s),Attack Angle (deg),Club Path (deg),Face Angle (deg),Face to Path (deg),Ball Speed (m/s),Smash Factor,Launch Angle (deg),Launch Direction (deg),Spin Rate (rpm),Spin Axis (deg),Carry (m),Carry Side (m),Total (m),Total Side (m),Apex Height (m),Landing Angle (deg)
Driver,47.0,-1.2,2.1,0.8,-1.3,67.0,1.43,12.3,-0.5,2845,3.2,227,7.3,248,11,29.9,38.5"""
    shots = parse_trackman_csv(metric_csv)
    assert len(shots) == 1
    assert round(shots[0].club_speed, 0) == 105.0
    assert round(shots[0].carry_distance, 0) == 248.0


def test_parse_trackman_csv_empty_input():
    with pytest.raises(ValueError, match="No data rows"):
        parse_trackman_csv("Club,Ball Speed (mph)\n")


def test_can_detect_trackman_csv():
    from backend.app.services.parsers.trackman.csv_export import is_trackman_csv
    assert is_trackman_csv("Club,Club Speed (mph),Attack Angle (deg),Ball Speed (mph),Carry (yd)\n")
    assert not is_trackman_csv("Club,Ball Speed,Carry Distance\n")
