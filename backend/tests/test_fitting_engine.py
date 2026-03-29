from backend.app.services.swing_profile import SwingProfile
from backend.app.services.fitting_engine import (
    score_club,
    rank_recommendations,
    OPTIMAL_LAUNCH,
    OPTIMAL_SPIN,
)


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
        "id": 1,
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
        "msrp": 599.99,
        "avg_used_price": 380.0,
        "still_in_production": True,
    }
    defaults.update(overrides)
    return defaults


def test_score_club_returns_float():
    profile = _make_profile()
    club = _make_club()
    score = score_club(profile, club)
    assert isinstance(score, float)
    assert 0 <= score <= 100


def test_high_spin_user_prefers_low_spin_club():
    profile = _make_profile(avg_spin_rate=3200.0)
    low_spin = _make_club(spin_bias="low")
    high_spin = _make_club(spin_bias="high")
    assert score_club(profile, low_spin) > score_club(profile, high_spin)


def test_high_launch_user_prefers_low_launch_club():
    profile = _make_profile(avg_launch_angle=16.0)
    low_launch = _make_club(launch_bias="low")
    high_launch = _make_club(launch_bias="high")
    assert score_club(profile, low_launch) > score_club(profile, high_launch)


def test_high_dispersion_prefers_forgiveness():
    profile = _make_profile(std_offline=20.0)
    forgiving = _make_club(forgiveness_rating=9, workability_rating=3)
    workable = _make_club(forgiveness_rating=3, workability_rating=9)
    assert score_club(profile, forgiving) > score_club(profile, workable)


def test_low_dispersion_prefers_workability():
    profile = _make_profile(std_offline=5.0)
    forgiving = _make_club(forgiveness_rating=9, workability_rating=3)
    workable = _make_club(forgiveness_rating=3, workability_rating=9)
    assert score_club(profile, workable) > score_club(profile, forgiving)


def test_speed_fit_centered_scores_higher():
    profile = _make_profile(avg_club_speed=105.0)
    centered = _make_club(swing_speed_min=90.0, swing_speed_max=120.0)  # center=105
    off_center = _make_club(swing_speed_min=110.0, swing_speed_max=140.0)  # center=125
    assert score_club(profile, centered) > score_club(profile, off_center)


def test_newer_club_scores_higher():
    profile = _make_profile()
    new_club = _make_club(model_year=2025)
    old_club = _make_club(model_year=2020)
    assert score_club(profile, new_club) > score_club(profile, old_club)


def test_rank_recommendations():
    profile = _make_profile(avg_spin_rate=3200.0, avg_launch_angle=15.0, std_offline=18.0)
    clubs = [
        _make_club(id=1, brand="Titleist", model_name="TSR3", launch_bias="low", spin_bias="low",
                   forgiveness_rating=5, workability_rating=9),
        _make_club(id=2, brand="TaylorMade", model_name="Qi10 Max", launch_bias="high", spin_bias="mid",
                   forgiveness_rating=9, workability_rating=3),
        _make_club(id=3, brand="Ping", model_name="G430 Max", launch_bias="mid", spin_bias="mid",
                   forgiveness_rating=9, workability_rating=4),
    ]
    ranked = rank_recommendations(profile, clubs, top_n=3)
    assert len(ranked) == 3
    assert all("score" in r for r in ranked)
    assert all("club" in r for r in ranked)
    scores = [r["score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_optimal_constants_exist():
    assert "driver" in OPTIMAL_LAUNCH
    assert "driver" in OPTIMAL_SPIN
    assert "7-iron" in OPTIMAL_LAUNCH
