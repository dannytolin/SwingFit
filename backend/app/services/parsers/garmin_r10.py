import csv
import io
from backend.app.schemas.shot import ShotCreate
from backend.app.utils.club_normalizer import normalize_club_name

_COLUMN_MAP = {
    "Ball Speed (mph)": "ball_speed",
    "Launch Angle (\u00b0)": "launch_angle",
    "Spin Rate (rpm)": "spin_rate",
    "Carry (yd)": "carry_distance",
    "Total (yd)": "total_distance",
    "Club Speed (mph)": "club_speed",
    "Smash Factor": "smash_factor",
    "Attack Angle (\u00b0)": "attack_angle",
    "Club Path (\u00b0)": "club_path",
    "Face Angle (\u00b0)": "face_angle",
}

_MIN_BALL_SPEED = {"driver": 80.0, "3-wood": 70.0, "5-wood": 65.0, "default": 50.0}
_GARMIN_SIGNATURE_COLS = {
    "Ball Speed (mph)",
    "Launch Angle (\u00b0)",
    "Spin Rate (rpm)",
    "Carry (yd)",
}


def is_garmin_r10_csv(header_line: str) -> bool:
    headers = {col.strip() for col in header_line.strip().split(",")}
    return _GARMIN_SIGNATURE_COLS.issubset(headers)


def parse_garmin_r10_csv(csv_text: str) -> list[ShotCreate]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("No data rows found in CSV")
    shots: list[ShotCreate] = []
    shot_num = 0
    for row in reader:
        shot_num += 1
        data: dict[str, float | None] = {}
        for csv_col, shot_field in _COLUMN_MAP.items():
            raw = row.get(csv_col, "").strip()
            if not raw or raw.upper() == "N/A":
                data[shot_field] = None
            else:
                data[shot_field] = float(raw)
        if data.get("ball_speed") is None or data.get("carry_distance") is None:
            continue
        club_raw = row.get("Club", "").strip()
        club_name = normalize_club_name(club_raw)
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
