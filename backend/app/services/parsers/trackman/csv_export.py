import csv
import io

from backend.app.schemas.shot import ShotCreate
from backend.app.utils.club_normalizer import normalize_club_name
from backend.app.utils.unit_converter import is_metric_header, mps_to_mph, meters_to_yards, meters_to_feet

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

_SPEED_FIELDS = {"club_speed", "ball_speed"}
_DISTANCE_FIELDS = {"carry_distance", "offline_distance", "total_distance"}
_HEIGHT_FIELDS = {"apex_height"}
_TRACKMAN_SIGNATURE = {"Club Speed", "Attack Angle", "Ball Speed", "Carry"}
# Fields that require higher precision than 1 decimal place
_PRECISION_MAP: dict[str, int] = {
    "smash_factor": 2,
}


def is_trackman_csv(header_line: str) -> bool:
    headers = set()
    for col in header_line.strip().split(","):
        base = col.split("(")[0].strip()
        headers.add(base)
    return _TRACKMAN_SIGNATURE.issubset(headers)


def parse_trackman_csv(csv_text: str) -> list[ShotCreate]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("No data rows found in CSV")

    header_map: dict[str, str] = {}
    is_metric = False
    for header in reader.fieldnames:
        if header == "Club":
            continue
        if is_metric_header(header):
            is_metric = True
        base = header.split("(")[0].strip()
        if base in _COLUMN_MAP:
            header_map[header] = _COLUMN_MAP[base]

    shots: list[ShotCreate] = []
    shot_num = 0

    for row in reader:
        ball_speed_header = _find_header(reader.fieldnames, "Ball Speed")
        carry_header = _find_header(reader.fieldnames, "Carry")
        if not ball_speed_header or not carry_header:
            continue
        raw_ball = row.get(ball_speed_header, "").strip()
        raw_carry = row.get(carry_header, "").strip()
        if not raw_ball and not raw_carry:
            continue

        shot_num += 1
        data: dict[str, float | None] = {}
        for csv_header, shot_field in header_map.items():
            raw_val = row.get(csv_header, "").strip()
            if not raw_val or raw_val.upper() == "N/A":
                data[shot_field] = None
                continue
            val = float(raw_val)
            if is_metric:
                if shot_field in _SPEED_FIELDS:
                    val = mps_to_mph(val)
                elif shot_field in _DISTANCE_FIELDS:
                    val = meters_to_yards(val)
                elif shot_field in _HEIGHT_FIELDS:
                    val = meters_to_feet(val)
            precision = _PRECISION_MAP.get(shot_field, 1)
            data[shot_field] = round(val, precision)

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
    for h in fieldnames:
        if h.split("(")[0].strip() == base_name:
            return h
    return None
