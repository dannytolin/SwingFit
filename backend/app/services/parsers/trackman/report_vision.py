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
    def __init__(self):
        self.client = anthropic.Anthropic()

    def extract_from_image(self, image_bytes: bytes, media_type: str) -> dict:
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
                        {"type": "text", "text": EXTRACTION_PROMPT},
                    ],
                }
            ],
        )
        return json.loads(response.content[0].text)


def normalize_vision_response(response: dict) -> list[ShotCreate]:
    shots: list[ShotCreate] = []
    shot_num = 0
    for club_data in response.get("clubs", []):
        shot_num += 1
        avgs = club_data.get("averages", {})
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
