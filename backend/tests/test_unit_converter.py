from backend.app.utils.unit_converter import (
    mps_to_mph,
    meters_to_yards,
    meters_to_feet,
    is_metric_header,
)


def test_mps_to_mph():
    assert round(mps_to_mph(44.7), 1) == 100.0
    assert round(mps_to_mph(0.0), 1) == 0.0


def test_meters_to_yards():
    assert round(meters_to_yards(100.0), 1) == 109.4
    assert round(meters_to_yards(0.0), 1) == 0.0


def test_meters_to_feet():
    assert round(meters_to_feet(30.0), 1) == 98.4
    assert round(meters_to_feet(0.0), 1) == 0.0


def test_is_metric_header_detects_metric():
    assert is_metric_header("Club Speed (m/s)") is True
    assert is_metric_header("Carry (m)") is True
    assert is_metric_header("Ball Speed (mps)") is True


def test_is_metric_header_detects_imperial():
    assert is_metric_header("Club Speed (mph)") is False
    assert is_metric_header("Carry (yd)") is False
    assert is_metric_header("Carry (yds)") is False
