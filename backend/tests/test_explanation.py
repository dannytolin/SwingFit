from backend.app.services.swing_profile import SwingProfile
from backend.app.services.explanation import generate_explanation


def _make_profile(**overrides) -> SwingProfile:
    defaults = {
        "club_type": "driver",
        "avg_club_speed": 105.0,
        "avg_ball_speed": 150.0,
        "avg_launch_angle": 14.0,
        "avg_spin_rate": 3100.0,
        "avg_carry": 248.0,
        "avg_attack_angle": -1.2,
        "avg_club_path": 2.0,
        "avg_face_angle": 0.5,
        "std_carry": 8.0,
        "std_offline": 12.0,
        "shot_shape_tendency": "straight",
        "miss_direction": "right",
        "smash_factor": 1.42,
        "spin_loft_estimate": 15.2,
        "sample_size": 50,
        "data_quality": "high",
    }
    defaults.update(overrides)
    return SwingProfile(**defaults)


def _make_club(**overrides) -> dict:
    defaults = {
        "brand": "Titleist",
        "model_name": "TSR3",
        "model_year": 2025,
        "club_type": "driver",
        "loft": 9.0,
        "launch_bias": "low",
        "spin_bias": "low",
        "forgiveness_rating": 5,
        "workability_rating": 9,
        "swing_speed_min": 90.0,
        "swing_speed_max": 120.0,
    }
    defaults.update(overrides)
    return defaults


def test_explanation_mentions_club():
    profile = _make_profile(avg_spin_rate=3200.0)
    club = _make_club(brand="Titleist", model_name="TSR3")
    explanation = generate_explanation(profile, club)
    assert "Titleist TSR3" in explanation


def test_explanation_addresses_high_spin():
    profile = _make_profile(avg_spin_rate=3200.0)
    club = _make_club(spin_bias="low")
    explanation = generate_explanation(profile, club)
    assert "spin" in explanation.lower()


def test_explanation_addresses_high_launch():
    profile = _make_profile(avg_launch_angle=17.0)
    club = _make_club(launch_bias="low")
    explanation = generate_explanation(profile, club)
    assert "launch" in explanation.lower()


def test_explanation_addresses_forgiveness():
    profile = _make_profile(std_offline=20.0)
    club = _make_club(forgiveness_rating=9)
    explanation = generate_explanation(profile, club)
    assert "forgiv" in explanation.lower()


def test_explanation_is_nonempty():
    profile = _make_profile()
    club = _make_club()
    explanation = generate_explanation(profile, club)
    assert len(explanation) > 20
