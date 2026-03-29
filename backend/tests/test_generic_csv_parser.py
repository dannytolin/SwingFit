import pytest
from backend.app.services.parsers.generic_csv import parse_generic_csv, match_headers
from backend.app.schemas.shot import ShotCreate

RAPSODO_STYLE_CSV = """Club,Ball Spd,Launch Ang,Total Spin,Carry Dist,Total Dist,Club Spd
Driver,149.8,12.3,2845,248,271,105.2
Driver,151.0,11.8,2650,255,278,107.1
7 Iron,120.5,18.4,6420,165,172,82.3
"""

FLIGHTSCOPE_STYLE_CSV = """Club,BallSpeed,LA,Spin,Carry,Total
Driver,149.8,12.3,2845,248,271
7 Iron,120.5,18.4,6420,165,172
"""


def test_match_headers_rapsodo():
    headers = ["Club", "Ball Spd", "Launch Ang", "Total Spin", "Carry Dist", "Total Dist", "Club Spd"]
    mapping = match_headers(headers)
    assert mapping["Ball Spd"] == "ball_speed"
    assert mapping["Launch Ang"] == "launch_angle"
    assert mapping["Total Spin"] == "spin_rate"
    assert mapping["Carry Dist"] == "carry_distance"
    assert mapping["Club Spd"] == "club_speed"


def test_match_headers_flightscope():
    headers = ["Club", "BallSpeed", "LA", "Spin", "Carry", "Total"]
    mapping = match_headers(headers)
    assert mapping["BallSpeed"] == "ball_speed"
    assert mapping["Spin"] == "spin_rate"
    assert mapping["Carry"] == "carry_distance"


def test_parse_generic_csv_rapsodo():
    shots = parse_generic_csv(RAPSODO_STYLE_CSV)
    assert len(shots) == 3
    assert shots[0].ball_speed == 149.8
    assert shots[0].carry_distance == 248.0
    assert shots[0].club_used == "driver"


def test_parse_generic_csv_flightscope():
    shots = parse_generic_csv(FLIGHTSCOPE_STYLE_CSV)
    assert len(shots) == 2
    assert shots[0].ball_speed == 149.8


def test_parse_generic_csv_missing_required():
    bad_csv = "Club,SomeField\nDriver,100\n"
    with pytest.raises(ValueError, match="Could not map required"):
        parse_generic_csv(bad_csv)


def test_parse_generic_csv_shot_numbers():
    shots = parse_generic_csv(RAPSODO_STYLE_CSV)
    assert [s.shot_number for s in shots] == [1, 2, 3]
