import json
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.claude_fitter import build_fitting_prompt, parse_claude_response
from backend.app.services.swing_profile import SwingProfile


def _sample_profile() -> SwingProfile:
    return SwingProfile(
        club_type="driver",
        avg_club_speed=105.0,
        avg_ball_speed=149.8,
        avg_launch_angle=14.2,
        avg_spin_rate=3100.0,
        avg_carry=248.0,
        avg_attack_angle=-1.2,
        avg_club_path=2.1,
        avg_face_angle=0.8,
        std_carry=8.5,
        std_offline=12.0,
        shot_shape_tendency="fade",
        miss_direction="right",
        smash_factor=1.42,
        spin_loft_estimate=15.4,
        sample_size=50,
        data_quality="high",
    )


def _sample_clubs() -> list[dict]:
    return [
        {
            "id": 1, "brand": "Titleist", "model_name": "TSR3",
            "model_year": 2025, "club_type": "driver", "loft": 9.0,
            "launch_bias": "low", "spin_bias": "low",
            "forgiveness_rating": 5, "workability_rating": 9,
            "swing_speed_min": 90.0, "swing_speed_max": 120.0,
            "msrp": 599.99, "avg_used_price": 380.0,
            "review_summary": "The TSR3 is a low-spin option for better players.",
        },
    ]


def test_build_fitting_prompt_contains_profile_data():
    prompt = build_fitting_prompt(_sample_profile(), _sample_clubs())
    assert "105.0" in prompt
    assert "3100" in prompt or "3,100" in prompt
    assert "TSR3" in prompt


def test_parse_claude_response_valid_json():
    raw = json.dumps([{
        "club_spec_id": 1,
        "match_score": 94,
        "explanation": "Great fit for your swing.",
        "projected_changes": {"spin_delta": "-400 to -600 rpm"},
        "best_for": "Low spin seekers",
    }])
    result = parse_claude_response(raw)
    assert len(result) == 1
    assert result[0]["match_score"] == 94
    assert result[0]["club_spec_id"] == 1


def test_parse_claude_response_extracts_json_from_text():
    raw = "Here are the recommendations:\n```json\n" + json.dumps([{
        "club_spec_id": 1, "match_score": 90,
        "explanation": "Good fit.", "projected_changes": {},
        "best_for": "All-around",
    }]) + "\n```"
    result = parse_claude_response(raw)
    assert len(result) == 1
