import csv
import io
from backend.app.schemas.shot import ShotCreate
from backend.app.utils.club_normalizer import normalize_club_name

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

_REQUIRED_FIELDS = {"ball_speed", "carry_distance"}


def match_headers(headers: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for header in headers:
        if header.strip().lower() == "club":
            continue
        cleaned = header.split("(")[0].strip().lower()
        for field_name, synonyms in _SYNONYMS.items():
            if cleaned in synonyms:
                mapping[header] = field_name
                break
    mapped_fields = set(mapping.values())
    missing = _REQUIRED_FIELDS - mapped_fields
    if missing:
        raise ValueError(f"Could not map required fields: {missing}")
    return mapping


def parse_generic_csv(csv_text: str) -> list[ShotCreate]:
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
