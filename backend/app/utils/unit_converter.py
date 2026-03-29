import re

_MPS_TO_MPH = 2.23694
_METERS_TO_YARDS = 1.09361
_METERS_TO_FEET = 3.28084
_METRIC_PATTERNS = re.compile(r"\(m/?s\)|\(mps\)|\(m\)|\(meters?\)", re.IGNORECASE)


def mps_to_mph(value: float) -> float:
    return value * _MPS_TO_MPH


def meters_to_yards(value: float) -> float:
    return value * _METERS_TO_YARDS


def meters_to_feet(value: float) -> float:
    return value * _METERS_TO_FEET


def is_metric_header(header: str) -> bool:
    return bool(_METRIC_PATTERNS.search(header))
