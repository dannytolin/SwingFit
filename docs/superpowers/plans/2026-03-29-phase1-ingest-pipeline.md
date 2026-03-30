# Phase 1: Ingest Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data ingest pipeline that parses swing data from Trackman CSV exports, Trackman report images/PDFs (via Claude Vision), Garmin R10 CSVs, generic CSVs, and manual entry — with auto-detection, deduplication, and data quality tiering.

**Architecture:** Each parser is a standalone module that takes raw input (CSV string, image bytes, or form data) and returns a list of `ShotCreate` Pydantic objects. A unified upload endpoint auto-detects the format by trying parsers in priority order. A shared club name normalizer standardizes club labels across all sources. Data quality tiering tags each session by source fidelity.

**Tech Stack:** Python, FastAPI, csv module, anthropic SDK (Claude Vision for OCR), hashlib (file dedup), Pydantic

---

### Task 1: Club Name Normalizer Utility

**Files:**
- Create: `backend/app/utils/club_normalizer.py`
- Create: `backend/tests/test_club_normalizer.py`

Every parser needs to map raw club labels ("Driver", "3 Wood", "7 Iron", "PW", "56°") to a consistent internal format. Build this shared utility first.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_club_normalizer.py`:

```python
from backend.app.utils.club_normalizer import normalize_club_name


def test_driver():
    assert normalize_club_name("Driver") == "driver"
    assert normalize_club_name("DRIVER") == "driver"
    assert normalize_club_name("driver") == "driver"


def test_fairway_woods():
    assert normalize_club_name("3 Wood") == "3-wood"
    assert normalize_club_name("3-Wood") == "3-wood"
    assert normalize_club_name("3W") == "3-wood"
    assert normalize_club_name("5 Wood") == "5-wood"
    assert normalize_club_name("7 Wood") == "7-wood"


def test_hybrids():
    assert normalize_club_name("4 Hybrid") == "4-hybrid"
    assert normalize_club_name("3 Hybrid") == "3-hybrid"
    assert normalize_club_name("3H") == "3-hybrid"
    assert normalize_club_name("5 Hybrid") == "5-hybrid"


def test_irons():
    assert normalize_club_name("5 Iron") == "5-iron"
    assert normalize_club_name("7 Iron") == "7-iron"
    assert normalize_club_name("7I") == "7-iron"
    assert normalize_club_name("7-iron") == "7-iron"
    assert normalize_club_name("9 Iron") == "9-iron"


def test_wedges():
    assert normalize_club_name("PW") == "PW"
    assert normalize_club_name("pw") == "PW"
    assert normalize_club_name("GW") == "GW"
    assert normalize_club_name("SW") == "SW"
    assert normalize_club_name("LW") == "LW"
    assert normalize_club_name("56°") == "56-degree"
    assert normalize_club_name("60 Degree") == "60-degree"


def test_putter():
    assert normalize_club_name("Putter") == "putter"


def test_unknown_passthrough():
    assert normalize_club_name("Custom Club") == "custom-club"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_club_normalizer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `backend/app/utils/club_normalizer.py`:

```python
import re


# Wedge abbreviations that should stay uppercase
_WEDGE_ABBREVS = {"pw", "gw", "sw", "lw", "aw"}

# Regex patterns for club types
_WOOD_RE = re.compile(r"^(\d)\s*[-]?\s*(?:wood|w)$", re.IGNORECASE)
_HYBRID_RE = re.compile(r"^(\d)\s*[-]?\s*(?:hybrid|h)$", re.IGNORECASE)
_IRON_RE = re.compile(r"^(\d)\s*[-]?\s*(?:iron|i)$", re.IGNORECASE)
_DEGREE_RE = re.compile(r"^(\d{2})\s*[°]?\s*(?:degree)?$", re.IGNORECASE)


def normalize_club_name(raw: str) -> str:
    """Normalize a raw club name to a consistent internal format.

    Examples:
        "Driver" -> "driver"
        "3 Wood" -> "3-wood"
        "7 Iron" -> "7-iron"
        "PW" -> "PW"
        "56°" -> "56-degree"
    """
    cleaned = raw.strip()

    # Driver / putter — simple lowercase
    if cleaned.lower() == "driver":
        return "driver"
    if cleaned.lower() == "putter":
        return "putter"

    # Wedge abbreviations — uppercase
    if cleaned.lower() in _WEDGE_ABBREVS:
        return cleaned.upper()

    # Numbered wood: "3 Wood", "3W", "3-Wood"
    m = _WOOD_RE.match(cleaned)
    if m:
        return f"{m.group(1)}-wood"

    # Hybrid: "4 Hybrid", "3H"
    m = _HYBRID_RE.match(cleaned)
    if m:
        return f"{m.group(1)}-hybrid"

    # Iron: "7 Iron", "7I", "7-iron"
    m = _IRON_RE.match(cleaned)
    if m:
        return f"{m.group(1)}-iron"

    # Degree wedge: "56°", "60 Degree"
    m = _DEGREE_RE.match(cleaned)
    if m:
        return f"{m.group(1)}-degree"

    # Fallback: lowercase, spaces to hyphens
    return re.sub(r"\s+", "-", cleaned.lower())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_club_normalizer.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/club_normalizer.py backend/tests/test_club_normalizer.py
git commit -m "feat: add club name normalizer utility"
```

---

### Task 2: Unit Conversion Utility

**Files:**
- Create: `backend/app/utils/unit_converter.py`
- Create: `backend/tests/test_unit_converter.py`

Trackman can export in metric. Range API uses metric. We need reliable conversions.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_unit_converter.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_unit_converter.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `backend/app/utils/unit_converter.py`:

```python
import re

# Conversion factors
_MPS_TO_MPH = 2.23694
_METERS_TO_YARDS = 1.09361
_METERS_TO_FEET = 3.28084

# Patterns that indicate metric units in column headers
_METRIC_PATTERNS = re.compile(r"\(m/?s\)|\(mps\)|\(m\)|\(meters?\)", re.IGNORECASE)


def mps_to_mph(value: float) -> float:
    """Convert meters per second to miles per hour."""
    return value * _MPS_TO_MPH


def meters_to_yards(value: float) -> float:
    """Convert meters to yards."""
    return value * _METERS_TO_YARDS


def meters_to_feet(value: float) -> float:
    """Convert meters to feet."""
    return value * _METERS_TO_FEET


def is_metric_header(header: str) -> bool:
    """Check if a CSV column header indicates metric units."""
    return bool(_METRIC_PATTERNS.search(header))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_unit_converter.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/unit_converter.py backend/tests/test_unit_converter.py
git commit -m "feat: add unit conversion utility for metric/imperial"
```

---

### Task 3: Trackman CSV Parser

**Files:**
- Create: `backend/app/services/parsers/trackman/csv_export.py`
- Create: `backend/tests/test_trackman_csv_parser.py`
- Create: `data/sample_sessions/trackman_sample.csv`

- [ ] **Step 1: Create sample Trackman CSV test fixture**

Create `data/sample_sessions/trackman_sample.csv`:

```csv
Club,Club Speed (mph),Attack Angle (deg),Club Path (deg),Face Angle (deg),Face to Path (deg),Ball Speed (mph),Smash Factor,Launch Angle (deg),Launch Direction (deg),Spin Rate (rpm),Spin Axis (deg),Carry (yd),Carry Side (yd),Total (yd),Total Side (yd),Apex Height (ft),Landing Angle (deg)
Driver,105.2,-1.2,2.1,0.8,-1.3,149.8,1.42,12.3,-0.5,2845,3.2,248,8,271,12,98,38.5
Driver,107.1,-0.8,1.5,0.3,-1.2,151.0,1.41,11.8,-0.2,2650,2.1,255,4,278,6,95,37.2
Driver,,,,,,,,,,,,,,,,
7 Iron,82.3,-3.2,0.5,-0.2,-0.7,120.5,1.46,18.4,0.3,6420,-1.5,165,-3,172,-4,78,45.1
PW,72.1,-4.5,0.2,-0.1,-0.3,99.8,1.38,24.1,0.1,8900,-0.8,125,-2,128,-2,82,50.3
```

Note: Row 3 is an empty/mishit row with all blank values except Club — this tests the blank-handling logic.

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_trackman_csv_parser.py`:

```python
import pytest

from backend.app.services.parsers.trackman.csv_export import parse_trackman_csv
from backend.app.schemas.shot import ShotCreate


def _read_sample() -> str:
    with open("data/sample_sessions/trackman_sample.csv") as f:
        return f.read()


def test_parse_trackman_csv_returns_shots():
    shots = parse_trackman_csv(_read_sample())
    # 5 rows total, but row 3 is all blank — should produce 4 valid shots
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
    # 47.0 m/s ≈ 105.1 mph
    assert round(shots[0].club_speed, 0) == 105.0
    # 227 m ≈ 248.3 yd
    assert round(shots[0].carry_distance, 0) == 248.0


def test_parse_trackman_csv_empty_input():
    with pytest.raises(ValueError, match="No data rows"):
        parse_trackman_csv("Club,Ball Speed (mph)\n")


def test_can_detect_trackman_csv():
    from backend.app.services.parsers.trackman.csv_export import is_trackman_csv
    assert is_trackman_csv("Club,Club Speed (mph),Attack Angle (deg),Ball Speed (mph),Carry (yd)\n")
    assert not is_trackman_csv("Club,Ball Speed,Carry Distance\n")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_trackman_csv_parser.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Write implementation**

Create `backend/app/services/parsers/trackman/csv_export.py`:

```python
import csv
import io

from backend.app.schemas.shot import ShotCreate
from backend.app.utils.club_normalizer import normalize_club_name
from backend.app.utils.unit_converter import is_metric_header, mps_to_mph, meters_to_yards, meters_to_feet


# Trackman CSV column → Shot field mapping
_COLUMN_MAP = {
    "Club Speed": "club_speed",
    "Attack Angle": "attack_angle",
    "Club Path": "club_path",
    "Face Angle": "face_angle",
    "Face to Path": "face_to_path",
    "Ball Speed": "ball_speed",
    "Smash Factor": "smash_factor",
    "Launch Angle": "launch_angle",
    "Spin Rate": "spin_rate",
    "Spin Axis": "spin_axis",
    "Carry": "carry_distance",
    "Carry Side": "offline_distance",
    "Total": "total_distance",
    "Apex Height": "apex_height",
    "Landing Angle": "landing_angle",
}

# Columns whose values are speeds (need m/s → mph conversion if metric)
_SPEED_FIELDS = {"club_speed", "ball_speed"}
# Columns whose values are distances (need m → yd conversion if metric)
_DISTANCE_FIELDS = {"carry_distance", "offline_distance", "total_distance"}
# Columns whose values are heights (need m → ft conversion if metric)
_HEIGHT_FIELDS = {"apex_height"}

# Required columns to identify a Trackman CSV (base name, without unit suffix)
_TRACKMAN_SIGNATURE = {"Club Speed", "Attack Angle", "Ball Speed", "Carry"}


def is_trackman_csv(header_line: str) -> bool:
    """Check if a CSV header line looks like a Trackman export."""
    # Strip unit suffixes like "(mph)", "(deg)" to get base names
    headers = set()
    for col in header_line.strip().split(","):
        base = col.split("(")[0].strip()
        headers.add(base)
    return _TRACKMAN_SIGNATURE.issubset(headers)


def parse_trackman_csv(csv_text: str) -> list[ShotCreate]:
    """Parse a Trackman Performance Studio CSV export into Shot objects.

    Args:
        csv_text: Full CSV file contents as a string.

    Returns:
        List of ShotCreate objects, one per valid shot row.

    Raises:
        ValueError: If no data rows are found.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("No data rows found in CSV")

    # Build the mapping from actual CSV headers to Shot fields
    header_map: dict[str, str] = {}  # csv_header -> shot_field
    is_metric = False

    for header in reader.fieldnames:
        if header == "Club":
            continue
        # Check if any header indicates metric
        if is_metric_header(header):
            is_metric = True
        # Match by base name (strip unit suffix)
        base = header.split("(")[0].strip()
        if base in _COLUMN_MAP:
            header_map[header] = _COLUMN_MAP[base]

    shots: list[ShotCreate] = []
    shot_num = 0

    for row in reader:
        # Skip rows where required fields are all empty
        ball_speed_header = _find_header(reader.fieldnames, "Ball Speed")
        carry_header = _find_header(reader.fieldnames, "Carry")

        if not ball_speed_header or not carry_header:
            continue

        raw_ball = row.get(ball_speed_header, "").strip()
        raw_carry = row.get(carry_header, "").strip()

        if not raw_ball and not raw_carry:
            continue

        shot_num += 1

        # Parse all mapped fields
        data: dict[str, float | None] = {}
        for csv_header, shot_field in header_map.items():
            raw_val = row.get(csv_header, "").strip()
            if not raw_val or raw_val.upper() == "N/A":
                data[shot_field] = None
                continue

            val = float(raw_val)

            # Convert metric to imperial if needed
            if is_metric:
                if shot_field in _SPEED_FIELDS:
                    val = mps_to_mph(val)
                elif shot_field in _DISTANCE_FIELDS:
                    val = meters_to_yards(val)
                elif shot_field in _HEIGHT_FIELDS:
                    val = meters_to_feet(val)

            data[shot_field] = round(val, 1)

        # Build the ShotCreate — required fields must be present
        if data.get("ball_speed") is None or data.get("carry_distance") is None:
            continue

        club_raw = row.get("Club", "").strip()
        shot = ShotCreate(
            club_used=normalize_club_name(club_raw),
            ball_speed=data["ball_speed"],
            launch_angle=data.get("launch_angle") or 0.0,
            spin_rate=data.get("spin_rate") or 0.0,
            carry_distance=data["carry_distance"],
            total_distance=data.get("total_distance"),
            club_speed=data.get("club_speed"),
            smash_factor=data.get("smash_factor"),
            attack_angle=data.get("attack_angle"),
            club_path=data.get("club_path"),
            face_angle=data.get("face_angle"),
            face_to_path=data.get("face_to_path"),
            spin_axis=data.get("spin_axis"),
            offline_distance=data.get("offline_distance"),
            apex_height=data.get("apex_height"),
            landing_angle=data.get("landing_angle"),
            shot_number=shot_num,
        )
        shots.append(shot)

    if not shots:
        raise ValueError("No data rows found in CSV")

    return shots


def _find_header(fieldnames: list[str], base_name: str) -> str | None:
    """Find the full header that starts with a base name (e.g., 'Ball Speed' -> 'Ball Speed (mph)')."""
    for h in fieldnames:
        if h.split("(")[0].strip() == base_name:
            return h
    return None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_trackman_csv_parser.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/parsers/trackman/csv_export.py backend/tests/test_trackman_csv_parser.py data/sample_sessions/trackman_sample.csv
git commit -m "feat: add Trackman CSV parser with metric support"
```

---

### Task 4: Garmin R10 CSV Parser

**Files:**
- Create: `backend/app/services/parsers/garmin_r10.py`
- Create: `backend/tests/test_garmin_r10_parser.py`
- Create: `data/sample_sessions/garmin_r10_sample.csv`

- [ ] **Step 1: Create sample Garmin R10 CSV test fixture**

Create `data/sample_sessions/garmin_r10_sample.csv`:

```csv
Club,Ball Speed (mph),Launch Angle (°),Spin Rate (rpm),Carry (yd),Total (yd),Club Speed (mph),Smash Factor,Attack Angle (°),Club Path (°),Face Angle (°)
Driver,148.2,12.3,2845,245,268,105.2,1.41,-1.2,2.1,0.8
Driver,151.0,11.8,2650,252,275,107.1,1.41,-0.8,1.5,0.3
Driver,35.0,5.0,1200,40,45,50.0,0.70,2.0,10.0,8.0
7 Iron,120.5,18.4,6420,165,172,82.3,1.46,-3.2,0.5,-0.2
PW,99.8,24.1,8900,125,128,72.1,1.38,-4.5,0.2,-0.1
```

Note: Row 3 is a mishit driver shot (ball speed 35 mph — way too low) to test outlier flagging.

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_garmin_r10_parser.py`:

```python
import pytest

from backend.app.services.parsers.garmin_r10 import parse_garmin_r10_csv, is_garmin_r10_csv
from backend.app.schemas.shot import ShotCreate


def _read_sample() -> str:
    with open("data/sample_sessions/garmin_r10_sample.csv") as f:
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
    # Third driver shot has ball speed 35 mph — should be flagged
    assert driver_shots[2].is_valid is False
    # Normal shots should be valid
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_garmin_r10_parser.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Write implementation**

Create `backend/app/services/parsers/garmin_r10.py`:

```python
import csv
import io

from backend.app.schemas.shot import ShotCreate
from backend.app.utils.club_normalizer import normalize_club_name


# Garmin R10 column → Shot field mapping
# Garmin uses ° instead of (deg) and doesn't include all Trackman fields
_COLUMN_MAP = {
    "Ball Speed (mph)": "ball_speed",
    "Launch Angle (°)": "launch_angle",
    "Spin Rate (rpm)": "spin_rate",
    "Carry (yd)": "carry_distance",
    "Total (yd)": "total_distance",
    "Club Speed (mph)": "club_speed",
    "Smash Factor": "smash_factor",
    "Attack Angle (°)": "attack_angle",
    "Club Path (°)": "club_path",
    "Face Angle (°)": "face_angle",
}

# Minimum ball speeds (mph) to consider a shot valid per club type
_MIN_BALL_SPEED = {
    "driver": 80.0,
    "3-wood": 70.0,
    "5-wood": 65.0,
    "default": 50.0,
}

# Garmin R10 signature: uses ° symbol and specific column set
_GARMIN_SIGNATURE_COLS = {"Ball Speed (mph)", "Launch Angle (°)", "Spin Rate (rpm)", "Carry (yd)"}


def is_garmin_r10_csv(header_line: str) -> bool:
    """Check if a CSV header line looks like a Garmin R10 export."""
    headers = {col.strip() for col in header_line.strip().split(",")}
    return _GARMIN_SIGNATURE_COLS.issubset(headers)


def parse_garmin_r10_csv(csv_text: str) -> list[ShotCreate]:
    """Parse a Garmin R10 CSV export into Shot objects.

    Args:
        csv_text: Full CSV file contents as a string.

    Returns:
        List of ShotCreate objects, one per row.

    Raises:
        ValueError: If no data rows are found.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("No data rows found in CSV")

    shots: list[ShotCreate] = []
    shot_num = 0

    for row in reader:
        shot_num += 1

        # Parse mapped fields
        data: dict[str, float | None] = {}
        for csv_col, shot_field in _COLUMN_MAP.items():
            raw = row.get(csv_col, "").strip()
            if not raw or raw.upper() == "N/A":
                data[shot_field] = None
            else:
                data[shot_field] = float(raw)

        # Skip rows missing required fields
        if data.get("ball_speed") is None or data.get("carry_distance") is None:
            continue

        club_raw = row.get("Club", "").strip()
        club_name = normalize_club_name(club_raw)

        # Flag outlier shots
        min_speed = _MIN_BALL_SPEED.get(club_name, _MIN_BALL_SPEED["default"])
        is_valid = data["ball_speed"] >= min_speed

        shot = ShotCreate(
            club_used=club_name,
            ball_speed=data["ball_speed"],
            launch_angle=data.get("launch_angle") or 0.0,
            spin_rate=data.get("spin_rate") or 0.0,
            carry_distance=data["carry_distance"],
            total_distance=data.get("total_distance"),
            club_speed=data.get("club_speed"),
            smash_factor=data.get("smash_factor"),
            attack_angle=data.get("attack_angle"),
            club_path=data.get("club_path"),
            face_angle=data.get("face_angle"),
            is_valid=is_valid,
            shot_number=shot_num,
        )
        shots.append(shot)

    if not shots:
        raise ValueError("No data rows found in CSV")

    return shots
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_garmin_r10_parser.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/parsers/garmin_r10.py backend/tests/test_garmin_r10_parser.py data/sample_sessions/garmin_r10_sample.csv
git commit -m "feat: add Garmin R10 CSV parser with mishit detection"
```

---

### Task 5: Generic CSV Parser with Fuzzy Header Matching

**Files:**
- Create: `backend/app/services/parsers/generic_csv.py`
- Create: `backend/tests/test_generic_csv_parser.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_generic_csv_parser.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_generic_csv_parser.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `backend/app/services/parsers/generic_csv.py`:

```python
import csv
import io

from backend.app.schemas.shot import ShotCreate
from backend.app.utils.club_normalizer import normalize_club_name


# Synonym dictionary: maps common CSV header variations to Shot field names
_SYNONYMS: dict[str, list[str]] = {
    "ball_speed": ["ball speed", "ballspeed", "ball spd", "ball velocity"],
    "launch_angle": ["launch angle", "launch ang", "la", "launch"],
    "spin_rate": ["spin rate", "spin", "total spin", "spinrate"],
    "carry_distance": ["carry", "carry distance", "carry dist", "carry (yd)", "carry (yds)"],
    "total_distance": ["total", "total distance", "total dist", "total (yd)", "total (yds)"],
    "club_speed": ["club speed", "clubspeed", "club spd", "swing speed"],
    "smash_factor": ["smash factor", "smash", "efficiency"],
    "attack_angle": ["attack angle", "attack ang", "aoa", "angle of attack"],
    "club_path": ["club path", "path", "swing path"],
    "face_angle": ["face angle", "face"],
    "face_to_path": ["face to path", "ftp"],
    "spin_axis": ["spin axis", "axis"],
    "offline_distance": ["offline", "carry side", "lateral", "side"],
    "apex_height": ["apex", "apex height", "max height", "height"],
    "landing_angle": ["landing angle", "land angle", "descent angle"],
}

# Required fields that must be matched for parsing to work
_REQUIRED_FIELDS = {"ball_speed", "carry_distance"}


def match_headers(headers: list[str]) -> dict[str, str]:
    """Match CSV headers to Shot field names using fuzzy synonym matching.

    Args:
        headers: List of CSV column header strings.

    Returns:
        Dict mapping CSV header -> Shot field name.

    Raises:
        ValueError: If required fields (ball_speed, carry_distance) can't be matched.
    """
    mapping: dict[str, str] = {}

    for header in headers:
        if header.strip().lower() == "club":
            continue

        # Strip unit suffixes like "(mph)", "(yd)", "(°)", "(deg)", "(rpm)"
        cleaned = header.split("(")[0].strip().lower()

        for field_name, synonyms in _SYNONYMS.items():
            if cleaned in synonyms:
                mapping[header] = field_name
                break

    # Check required fields are mapped
    mapped_fields = set(mapping.values())
    missing = _REQUIRED_FIELDS - mapped_fields
    if missing:
        raise ValueError(f"Could not map required fields: {missing}")

    return mapping


def parse_generic_csv(csv_text: str) -> list[ShotCreate]:
    """Parse a generic launch monitor CSV using fuzzy header matching.

    Args:
        csv_text: Full CSV file contents as a string.

    Returns:
        List of ShotCreate objects.

    Raises:
        ValueError: If required fields can't be matched or no data rows found.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("No data rows found in CSV")

    header_map = match_headers(list(reader.fieldnames))

    shots: list[ShotCreate] = []
    shot_num = 0

    for row in reader:
        shot_num += 1

        data: dict[str, float | None] = {}
        for csv_header, shot_field in header_map.items():
            raw = row.get(csv_header, "").strip()
            if not raw or raw.upper() == "N/A":
                data[shot_field] = None
            else:
                data[shot_field] = float(raw)

        if data.get("ball_speed") is None or data.get("carry_distance") is None:
            continue

        club_raw = row.get("Club", row.get("club", "unknown")).strip()

        shot = ShotCreate(
            club_used=normalize_club_name(club_raw),
            ball_speed=data["ball_speed"],
            launch_angle=data.get("launch_angle") or 0.0,
            spin_rate=data.get("spin_rate") or 0.0,
            carry_distance=data["carry_distance"],
            total_distance=data.get("total_distance"),
            club_speed=data.get("club_speed"),
            smash_factor=data.get("smash_factor"),
            attack_angle=data.get("attack_angle"),
            club_path=data.get("club_path"),
            face_angle=data.get("face_angle"),
            face_to_path=data.get("face_to_path"),
            spin_axis=data.get("spin_axis"),
            offline_distance=data.get("offline_distance"),
            apex_height=data.get("apex_height"),
            landing_angle=data.get("landing_angle"),
            shot_number=shot_num,
        )
        shots.append(shot)

    if not shots:
        raise ValueError("No data rows found in CSV")

    return shots
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_generic_csv_parser.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/parsers/generic_csv.py backend/tests/test_generic_csv_parser.py
git commit -m "feat: add generic CSV parser with fuzzy header matching"
```

---

### Task 6: Data Quality Tiering

**Files:**
- Create: `backend/app/services/data_quality.py`
- Create: `backend/tests/test_data_quality.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_data_quality.py`:

```python
from backend.app.services.data_quality import get_data_quality, DATA_QUALITY_TIERS


def test_trackman_file_is_platinum():
    dq = get_data_quality("trackman_4", "file_upload")
    assert dq["tier"] == "platinum"
    assert dq["weight"] == 1.0
    assert dq["has_club_data"] is True


def test_trackman_ocr_is_silver():
    dq = get_data_quality("trackman_4", "ocr_vision")
    assert dq["tier"] == "silver"
    assert dq["weight"] == 0.7


def test_garmin_r10_is_silver():
    dq = get_data_quality("garmin_r10", "file_upload")
    assert dq["tier"] == "silver"
    assert dq["weight"] == 0.7


def test_manual_entry_is_bronze():
    dq = get_data_quality("manual", "manual_entry")
    assert dq["tier"] == "bronze"
    assert dq["weight"] == 0.3


def test_unknown_source_is_bronze():
    dq = get_data_quality("unknown_monitor", "file_upload")
    assert dq["tier"] == "bronze"
    assert dq["weight"] == 0.5


def test_all_tiers_have_required_keys():
    for key, tier in DATA_QUALITY_TIERS.items():
        assert "tier" in tier
        assert "weight" in tier
        assert "has_club_data" in tier
        assert "has_spin_axis" in tier
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_data_quality.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `backend/app/services/data_quality.py`:

```python
DATA_QUALITY_TIERS: dict[str, dict] = {
    "trackman_4_file": {
        "tier": "platinum",
        "weight": 1.0,
        "has_club_data": True,
        "has_spin_axis": True,
    },
    "trackman_4_bridge": {
        "tier": "platinum",
        "weight": 1.0,
        "has_club_data": True,
        "has_spin_axis": True,
    },
    "trackman_range_api": {
        "tier": "gold",
        "weight": 0.85,
        "has_club_data": False,
        "has_spin_axis": False,
    },
    "trackman_report_ocr": {
        "tier": "silver",
        "weight": 0.7,
        "has_club_data": True,
        "has_spin_axis": True,
    },
    "garmin_r10": {
        "tier": "silver",
        "weight": 0.7,
        "has_club_data": True,
        "has_spin_axis": False,
    },
    "rapsodo_mlm2": {
        "tier": "silver",
        "weight": 0.7,
        "has_club_data": True,
        "has_spin_axis": False,
    },
    "fullswing_kit": {
        "tier": "silver",
        "weight": 0.7,
        "has_club_data": True,
        "has_spin_axis": True,
    },
    "generic_csv": {
        "tier": "bronze",
        "weight": 0.5,
        "has_club_data": False,
        "has_spin_axis": False,
    },
    "manual_entry": {
        "tier": "bronze",
        "weight": 0.3,
        "has_club_data": False,
        "has_spin_axis": False,
    },
}

# Lookup key: (launch_monitor_type, data_source) -> tier key
_LOOKUP: dict[tuple[str, str], str] = {
    ("trackman_4", "file_upload"): "trackman_4_file",
    ("trackman_4", "bridge"): "trackman_4_bridge",
    ("trackman_range", "api_realtime"): "trackman_range_api",
    ("trackman_4", "ocr_vision"): "trackman_report_ocr",
    ("garmin_r10", "file_upload"): "garmin_r10",
    ("rapsodo_mlm2", "file_upload"): "rapsodo_mlm2",
    ("fullswing_kit", "file_upload"): "fullswing_kit",
    ("manual", "manual_entry"): "manual_entry",
}

_DEFAULT_TIER = DATA_QUALITY_TIERS["generic_csv"]


def get_data_quality(launch_monitor_type: str, data_source: str) -> dict:
    """Get data quality tier info for a given launch monitor and data source."""
    key = (launch_monitor_type, data_source)
    tier_key = _LOOKUP.get(key)
    if tier_key:
        return DATA_QUALITY_TIERS[tier_key]
    return _DEFAULT_TIER
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_data_quality.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/data_quality.py backend/tests/test_data_quality.py
git commit -m "feat: add data quality tiering for launch monitor sources"
```

---

### Task 7: Unified Upload Endpoint with Auto-Detection

**Files:**
- Create: `backend/app/routers/ingest.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_routers_ingest.py`

This is the main ingest endpoint: accepts a CSV file upload, auto-detects the format, parses it, creates the session + shots, and returns the summary.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_routers_ingest.py`:

```python
import hashlib
import io

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
    db.close()


def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)


client = TestClient(app)

TRACKMAN_CSV = b"""Club,Club Speed (mph),Attack Angle (deg),Club Path (deg),Face Angle (deg),Face to Path (deg),Ball Speed (mph),Smash Factor,Launch Angle (deg),Launch Direction (deg),Spin Rate (rpm),Spin Axis (deg),Carry (yd),Carry Side (yd),Total (yd),Total Side (yd),Apex Height (ft),Landing Angle (deg)
Driver,105.2,-1.2,2.1,0.8,-1.3,149.8,1.42,12.3,-0.5,2845,3.2,248,8,271,12,98,38.5
Driver,107.1,-0.8,1.5,0.3,-1.2,151.0,1.41,11.8,-0.2,2650,2.1,255,4,278,6,95,37.2
"""

GARMIN_CSV = b"""Club,Ball Speed (mph),Launch Angle (\xc2\xb0),Spin Rate (rpm),Carry (yd),Total (yd),Club Speed (mph),Smash Factor,Attack Angle (\xc2\xb0),Club Path (\xc2\xb0),Face Angle (\xc2\xb0)
Driver,148.2,12.3,2845,245,268,105.2,1.41,-1.2,2.1,0.8
"""

GENERIC_CSV = b"""Club,Ball Spd,Spin,Carry,Total
Driver,149.8,2845,248,271
"""


def test_upload_trackman_csv():
    response = client.post(
        f"/ingest/upload?user_id={USER_ID}",
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
        f"/ingest/upload?user_id={USER_ID}",
        files={"file": ("garmin_export.csv", io.BytesIO(GARMIN_CSV), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["session"]["launch_monitor_type"] == "garmin_r10"
    assert data["shot_count"] == 1
    assert data["data_quality"]["tier"] == "silver"


def test_upload_generic_csv():
    response = client.post(
        f"/ingest/upload?user_id={USER_ID}",
        files={"file": ("unknown_monitor.csv", io.BytesIO(GENERIC_CSV), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["session"]["launch_monitor_type"] == "generic"
    assert data["shot_count"] == 1
    assert data["data_quality"]["tier"] == "bronze"


def test_upload_duplicate_rejected():
    csv_data = TRACKMAN_CSV
    # First upload
    client.post(
        f"/ingest/upload?user_id={USER_ID}",
        files={"file": ("session.csv", io.BytesIO(csv_data), "text/csv")},
    )
    # Second upload of same content
    response = client.post(
        f"/ingest/upload?user_id={USER_ID}",
        files={"file": ("session.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert response.status_code == 409
    assert "duplicate" in response.json()["detail"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_routers_ingest.py -v`
Expected: FAIL — routes don't exist

- [ ] **Step 3: Write implementation**

Create `backend/app/routers/ingest.py`:

```python
import hashlib

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.models.user import User
from backend.app.schemas.shot import ShotCreate
from backend.app.services.data_quality import get_data_quality
from backend.app.services.parsers.trackman.csv_export import is_trackman_csv, parse_trackman_csv
from backend.app.services.parsers.garmin_r10 import is_garmin_r10_csv, parse_garmin_r10_csv
from backend.app.services.parsers.generic_csv import parse_generic_csv

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _detect_and_parse(csv_text: str) -> tuple[str, str, list[ShotCreate]]:
    """Auto-detect CSV format and parse. Returns (launch_monitor_type, data_source, shots)."""
    header_line = csv_text.split("\n", 1)[0]

    # Try Trackman first (highest fidelity)
    if is_trackman_csv(header_line):
        shots = parse_trackman_csv(csv_text)
        return "trackman_4", "file_upload", shots

    # Try Garmin R10
    if is_garmin_r10_csv(header_line):
        shots = parse_garmin_r10_csv(csv_text)
        return "garmin_r10", "file_upload", shots

    # Fallback to generic
    shots = parse_generic_csv(csv_text)
    return "generic", "file_upload", shots


@router.post("/upload", status_code=201)
async def upload_session_file(
    user_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    """Upload a CSV file from any launch monitor. Auto-detects format."""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Read file content
    content = await file.read()
    csv_text = content.decode("utf-8")
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate upload
    existing = db.query(SwingSession).filter(
        SwingSession.user_id == user_id,
        SwingSession.source_file_hash == file_hash,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Duplicate file — this session was already uploaded")

    # Detect format and parse
    launch_monitor_type, data_source, shots = _detect_and_parse(csv_text)

    # Create session
    swing_session = SwingSession(
        user_id=user_id,
        launch_monitor_type=launch_monitor_type,
        data_source=data_source,
        source_file_name=file.filename,
        source_file_hash=file_hash,
    )
    db.add(swing_session)
    db.commit()
    db.refresh(swing_session)

    # Create shot records
    for shot_data in shots:
        shot = Shot(session_id=swing_session.id, **shot_data.model_dump())
        db.add(shot)
    db.commit()

    # Get data quality info
    dq = get_data_quality(launch_monitor_type, data_source)

    return {
        "session": {
            "id": swing_session.id,
            "launch_monitor_type": launch_monitor_type,
            "data_source": data_source,
            "source_file_name": file.filename,
        },
        "shot_count": len(shots),
        "data_quality": dq,
    }


@router.post("/manual", status_code=201)
async def manual_entry(
    user_id: int,
    club_type: str,
    ball_speed: float,
    launch_angle: float,
    spin_rate: float,
    carry_distance: float,
    club_speed: float | None = None,
    total_distance: float | None = None,
    db: Session = Depends(get_db),
):
    """Manual entry of averaged swing data for a single club type."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from backend.app.utils.club_normalizer import normalize_club_name

    swing_session = SwingSession(
        user_id=user_id,
        launch_monitor_type="manual",
        data_source="manual_entry",
    )
    db.add(swing_session)
    db.commit()
    db.refresh(swing_session)

    shot = Shot(
        session_id=swing_session.id,
        club_used=normalize_club_name(club_type),
        ball_speed=ball_speed,
        launch_angle=launch_angle,
        spin_rate=spin_rate,
        carry_distance=carry_distance,
        total_distance=total_distance,
        club_speed=club_speed,
        shot_number=1,
    )
    db.add(shot)
    db.commit()

    dq = get_data_quality("manual", "manual_entry")

    return {
        "session": {
            "id": swing_session.id,
            "launch_monitor_type": "manual",
            "data_source": "manual_entry",
        },
        "shot_count": 1,
        "data_quality": dq,
    }
```

- [ ] **Step 4: Register ingest router in main.py**

Read `backend/app/main.py` first, then add the ingest router import alongside existing routers. The final state should include all three routers:

```python
from fastapi import FastAPI

from backend.app.config import settings
from backend.app.routers.clubs import router as clubs_router
from backend.app.routers.sessions import router as sessions_router
from backend.app.routers.ingest import router as ingest_router

app = FastAPI(title=settings.app_name)
app.include_router(clubs_router)
app.include_router(sessions_router)
app.include_router(ingest_router)


@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.app_name}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_routers_ingest.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest backend/tests/ -v`
Expected: All tests PASS (no regressions)

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/ingest.py backend/app/main.py backend/tests/test_routers_ingest.py
git commit -m "feat: add unified upload endpoint with format auto-detection and dedup"
```

---

### Task 8: Manual Entry Endpoint Tests

**Files:**
- Modify: `backend/tests/test_routers_ingest.py`

The manual entry endpoint was created in Task 7. This task adds tests for it.

- [ ] **Step 1: Add manual entry tests**

Append to `backend/tests/test_routers_ingest.py`:

```python
def test_manual_entry():
    response = client.post(
        f"/ingest/manual?user_id={USER_ID}&club_type=Driver&ball_speed=150.0&launch_angle=12.5&spin_rate=2700&carry_distance=250",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["session"]["launch_monitor_type"] == "manual"
    assert data["session"]["data_source"] == "manual_entry"
    assert data["shot_count"] == 1
    assert data["data_quality"]["tier"] == "bronze"


def test_manual_entry_with_optional_fields():
    response = client.post(
        f"/ingest/manual?user_id={USER_ID}&club_type=7 Iron&ball_speed=120.0&launch_angle=18.0&spin_rate=6400&carry_distance=165&club_speed=82.0&total_distance=172",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["shot_count"] == 1


def test_manual_entry_user_not_found():
    response = client.post(
        "/ingest/manual?user_id=9999&club_type=Driver&ball_speed=150&launch_angle=12&spin_rate=2700&carry_distance=250",
    )
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `python -m pytest backend/tests/test_routers_ingest.py -v`
Expected: All 7 tests PASS (4 from Task 7 + 3 new)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_routers_ingest.py
git commit -m "test: add manual entry endpoint tests"
```

---

### Task 9: Trackman Report Vision Parser (Claude Vision API)

**Files:**
- Create: `backend/app/services/parsers/trackman/report_vision.py`
- Create: `backend/tests/test_trackman_vision_parser.py`

This parser uses the Anthropic Claude Vision API to extract swing data from screenshots and photos of Trackman reports. Since we can't call the real API in tests, we'll mock the API response and test the parsing/normalization logic.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_trackman_vision_parser.py`:

```python
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
    parser = TrackmanReportParser()
    assert MOCK_VISION_RESPONSE["confidence"] == 0.92


@patch("backend.app.services.parsers.trackman.report_vision.anthropic")
def test_extract_from_image_calls_api(mock_anthropic):
    # Mock the API client and response
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(MOCK_VISION_RESPONSE))]
    mock_client.messages.create.return_value = mock_response

    parser = TrackmanReportParser()
    result = parser.extract_from_image(b"fake_image_bytes", "image/png")

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args
    assert call_kwargs.kwargs["model"] is not None
    assert result["confidence"] == 0.92
    assert len(result["clubs"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_trackman_vision_parser.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Install anthropic SDK**

Add `anthropic` to `backend/requirements.txt` and install:

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
source .venv/Scripts/activate
pip install anthropic
```

Then append `anthropic` to `backend/requirements.txt`.

- [ ] **Step 4: Write implementation**

Create `backend/app/services/parsers/trackman/report_vision.py`:

```python
import base64
import json

import anthropic

from backend.app.schemas.shot import ShotCreate
from backend.app.utils.club_normalizer import normalize_club_name


EXTRACTION_PROMPT = """Analyze this Trackman golf report/screenshot and extract all swing data.

Return a JSON object with this exact structure:
{
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
                "smash_factor": 1.42
            }
        }
    ],
    "data_type": "session_summary",
    "source": "trackman_app_screenshot",
    "confidence": 0.95
}

Rules:
- All speeds in mph, distances in yards, heights in feet, angles in degrees, spin in rpm
- If units are metric (m/s, meters), convert to imperial
- If a value is not visible or unreadable, set to null
- If you can see per-shot data (not just averages), include each shot separately
- Set confidence to how sure you are the extraction is accurate (0.0 to 1.0)
- Only return valid JSON, no other text"""


class TrackmanReportParser:
    """Uses Claude's vision API to extract swing data from Trackman reports."""

    def __init__(self):
        self.client = anthropic.Anthropic()

    def extract_from_image(self, image_bytes: bytes, media_type: str) -> dict:
        """Extract swing data from a Trackman screenshot or photo.

        Args:
            image_bytes: Raw image bytes.
            media_type: MIME type (e.g., "image/png", "image/jpeg").

        Returns:
            Parsed JSON dict with clubs, data_type, source, confidence.
        """
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.b64encode(image_bytes).decode(),
                            },
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT,
                        },
                    ],
                }
            ],
        )

        return json.loads(response.content[0].text)


def normalize_vision_response(response: dict) -> list[ShotCreate]:
    """Convert Claude Vision extraction response to ShotCreate objects.

    Each club in the response becomes one "synthetic" shot representing
    the averaged data for that club type.

    Args:
        response: Parsed JSON from Claude Vision API.

    Returns:
        List of ShotCreate objects, one per club type in the report.
    """
    shots: list[ShotCreate] = []
    shot_num = 0

    for club_data in response.get("clubs", []):
        shot_num += 1
        avgs = club_data.get("averages", {})

        # Skip if missing critical data
        if not avgs.get("ball_speed") or not avgs.get("carry_distance"):
            continue

        shot = ShotCreate(
            club_used=normalize_club_name(club_data.get("club_type", "unknown")),
            ball_speed=float(avgs["ball_speed"]),
            launch_angle=float(avgs.get("launch_angle") or 0.0),
            spin_rate=float(avgs.get("spin_rate") or 0.0),
            carry_distance=float(avgs["carry_distance"]),
            total_distance=_float_or_none(avgs.get("total_distance")),
            club_speed=_float_or_none(avgs.get("club_speed")),
            smash_factor=_float_or_none(avgs.get("smash_factor")),
            attack_angle=_float_or_none(avgs.get("attack_angle")),
            club_path=_float_or_none(avgs.get("club_path")),
            face_angle=_float_or_none(avgs.get("face_angle")),
            face_to_path=_float_or_none(avgs.get("face_to_path")),
            spin_axis=_float_or_none(avgs.get("spin_axis")),
            offline_distance=_float_or_none(avgs.get("offline_distance")),
            apex_height=_float_or_none(avgs.get("apex_height")),
            landing_angle=_float_or_none(avgs.get("landing_angle")),
            shot_number=shot_num,
        )
        shots.append(shot)

    return shots


def _float_or_none(val) -> float | None:
    if val is None:
        return None
    return float(val)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_trackman_vision_parser.py -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/parsers/trackman/report_vision.py backend/tests/test_trackman_vision_parser.py backend/requirements.txt
git commit -m "feat: add Trackman report vision parser using Claude Vision API"
```

---

### Task 10: Trackman Report Upload Endpoint

**Files:**
- Modify: `backend/app/routers/ingest.py`
- Create: `backend/tests/test_routers_ingest_report.py`

Add the `/ingest/trackman-report` endpoint for image/PDF uploads.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_routers_ingest_report.py`:

```python
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

    fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Fake PNG header

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_routers_ingest_report.py -v`
Expected: FAIL — endpoint doesn't exist

- [ ] **Step 3: Add trackman-report endpoint to ingest router**

Append to `backend/app/routers/ingest.py`, adding the import at the top and the new endpoint:

Add import at top of file:
```python
from backend.app.services.parsers.trackman.report_vision import (
    TrackmanReportParser,
    normalize_vision_response,
)
```

Add endpoint at bottom of file:
```python
@router.post("/trackman-report", status_code=201)
async def upload_trackman_report(
    user_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    """Upload a Trackman screenshot, photo, or PDF report for OCR extraction."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    content = await file.read()
    media_type = file.content_type or "image/png"

    # Extract data using Claude Vision
    parser = TrackmanReportParser()
    vision_result = parser.extract_from_image(content, media_type)

    # Normalize to shot objects
    shots = normalize_vision_response(vision_result)
    confidence = vision_result.get("confidence", 0.0)

    # Create session
    swing_session = SwingSession(
        user_id=user_id,
        launch_monitor_type="trackman_4",
        data_source="ocr_vision",
        source_file_name=file.filename,
    )
    db.add(swing_session)
    db.commit()
    db.refresh(swing_session)

    # Create shot records
    for shot_data in shots:
        shot = Shot(session_id=swing_session.id, **shot_data.model_dump())
        db.add(shot)
    db.commit()

    dq = get_data_quality("trackman_4", "ocr_vision")

    return {
        "session": {
            "id": swing_session.id,
            "launch_monitor_type": "trackman_4",
            "data_source": "ocr_vision",
            "source_file_name": file.filename,
        },
        "shot_count": len(shots),
        "confidence": confidence,
        "low_confidence_warning": confidence < 0.7,
        "data_quality": dq,
        "extracted_data": vision_result,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_routers_ingest_report.py -v`
Expected: Both tests PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/ingest.py backend/tests/test_routers_ingest_report.py
git commit -m "feat: add Trackman report upload endpoint with Claude Vision OCR"
```

---

### Task 11: Full Test Suite & Integration Verification

**Files:** None new — integration verification only.

- [ ] **Step 1: Run all tests**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
source .venv/Scripts/activate
python -m pytest backend/tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Boot server and test upload endpoint manually**

```bash
# Seed db if not already done
python -m scripts.seed_clubs

# Start server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
sleep 2

# Health check
curl http://localhost:8000/

# Upload the Trackman sample CSV
curl -X POST "http://localhost:8000/ingest/upload?user_id=1" \
  -F "file=@data/sample_sessions/trackman_sample.csv"

# Upload the Garmin R10 sample CSV
curl -X POST "http://localhost:8000/ingest/upload?user_id=1" \
  -F "file=@data/sample_sessions/garmin_r10_sample.csv"

# Manual entry
curl -X POST "http://localhost:8000/ingest/manual?user_id=1&club_type=Driver&ball_speed=150&launch_angle=12.5&spin_rate=2700&carry_distance=250"

kill %1
```

Expected: All requests return 201 with correct response bodies.

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "chore: Phase 1 complete — ingest pipeline with auto-detection"
```
