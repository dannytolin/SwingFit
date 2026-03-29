import pytest
from backend.app.services.parsers.garmin_r10 import parse_garmin_r10_csv, is_garmin_r10_csv
from backend.app.schemas.shot import ShotCreate


def _read_sample() -> str:
    with open("data/sample_sessions/garmin_r10_sample.csv", encoding="utf-8") as f:
        return f.read()


def test_parse_garmin_r10_returns_shots():
    shots = parse_garmin_r10_csv(_read_sample())
    assert len(shots) == 5
    assert all(isinstance(s, ShotCreate) for s in shots)


def test_parse_garmin_r10_driver_data():
    shots = parse_garmin_r10_csv(_read_sample())
    first = shots[0]
    assert first.club_used == "driver"
    assert first.ball_speed == 148.2
    assert first.launch_angle == 12.3
    assert first.spin_rate == 2845.0
    assert first.carry_distance == 245.0
    assert first.total_distance == 268.0
    assert first.club_speed == 105.2
    assert first.smash_factor == 1.41
    assert first.attack_angle == -1.2
    assert first.club_path == 2.1
    assert first.face_angle == 0.8


def test_parse_garmin_r10_mishit_flagged():
    shots = parse_garmin_r10_csv(_read_sample())
    driver_shots = [s for s in shots if s.club_used == "driver"]
    assert driver_shots[2].is_valid is False
    assert driver_shots[0].is_valid is True


def test_parse_garmin_r10_club_normalization():
    shots = parse_garmin_r10_csv(_read_sample())
    clubs = [s.club_used for s in shots]
    assert "driver" in clubs
    assert "7-iron" in clubs
    assert "PW" in clubs


def test_parse_garmin_r10_shot_numbers():
    shots = parse_garmin_r10_csv(_read_sample())
    assert [s.shot_number for s in shots] == [1, 2, 3, 4, 5]


def test_can_detect_garmin_r10_csv():
    header = "Club,Ball Speed (mph),Launch Angle (°),Spin Rate (rpm),Carry (yd),Total (yd),Club Speed (mph)\n"
    assert is_garmin_r10_csv(header) is True
    assert is_garmin_r10_csv("Club,Club Speed (mph),Attack Angle (deg),Ball Speed (mph)\n") is False
