from datetime import datetime, timezone

from backend.app.services.swing_profile import SwingProfile

CURRENT_YEAR = datetime.now(timezone.utc).year

OPTIMAL_LAUNCH: dict[str, tuple[float, float]] = {
    "driver": (12.0, 15.0),
    "3-wood": (11.0, 14.0),
    "5-wood": (12.0, 15.0),
    "3-hybrid": (12.0, 15.0),
    "4-hybrid": (13.0, 16.0),
    "5-hybrid": (14.0, 17.0),
    "4-iron": (14.0, 17.0),
    "5-iron": (15.0, 18.0),
    "6-iron": (16.0, 19.0),
    "7-iron": (16.0, 20.0),
    "8-iron": (18.0, 22.0),
    "9-iron": (20.0, 25.0),
    "PW": (24.0, 28.0),
    "GW": (26.0, 30.0),
    "SW": (28.0, 34.0),
    "LW": (30.0, 36.0),
}

OPTIMAL_SPIN: dict[str, tuple[float, float]] = {
    "driver": (2000.0, 2500.0),
    "3-wood": (3000.0, 4000.0),
    "5-wood": (3500.0, 4500.0),
    "3-hybrid": (3500.0, 4500.0),
    "4-hybrid": (4000.0, 5000.0),
    "5-hybrid": (4500.0, 5500.0),
    "4-iron": (4500.0, 5500.0),
    "5-iron": (5000.0, 6000.0),
    "6-iron": (5500.0, 6500.0),
    "7-iron": (6000.0, 7000.0),
    "8-iron": (7000.0, 8000.0),
    "9-iron": (7500.0, 8500.0),
    "PW": (8000.0, 9500.0),
    "GW": (8500.0, 10000.0),
    "SW": (9000.0, 10500.0),
    "LW": (9500.0, 11000.0),
}

HIGH_DISPERSION_THRESHOLD = 12.0


def score_club(profile: SwingProfile, club: dict) -> float:
    score = 0.0

    # Launch optimization (20 points)
    optimal_launch = OPTIMAL_LAUNCH.get(profile.club_type, (12.0, 15.0))
    if profile.avg_launch_angle > optimal_launch[1]:
        score += {"low": 20, "mid": 10, "high": 0}.get(club.get("launch_bias", "mid"), 5)
    elif profile.avg_launch_angle < optimal_launch[0]:
        score += {"high": 20, "mid": 10, "low": 0}.get(club.get("launch_bias", "mid"), 5)
    else:
        score += {"mid": 20, "low": 10, "high": 10}.get(club.get("launch_bias", "mid"), 10)

    # Spin optimization (20 points)
    optimal_spin = OPTIMAL_SPIN.get(profile.club_type, (2000.0, 2500.0))
    if profile.avg_spin_rate > optimal_spin[1]:
        score += {"low": 20, "mid": 10, "high": 0}.get(club.get("spin_bias", "mid"), 5)
    elif profile.avg_spin_rate < optimal_spin[0]:
        score += {"high": 20, "mid": 10, "low": 0}.get(club.get("spin_bias", "mid"), 5)
    else:
        score += {"mid": 20, "low": 10, "high": 10}.get(club.get("spin_bias", "mid"), 10)

    # Forgiveness vs Workability (30 points)
    dispersion = profile.std_offline if profile.std_offline is not None else profile.std_carry
    forgiveness = club.get("forgiveness_rating") or 5
    workability = club.get("workability_rating") or 5
    if dispersion > HIGH_DISPERSION_THRESHOLD:
        score += forgiveness * 3
    else:
        score += workability * 3

    # Swing speed fit (20 points)
    speed_min = club.get("swing_speed_min")
    speed_max = club.get("swing_speed_max")
    if speed_min is not None and speed_max is not None and speed_max > speed_min:
        speed_center = (speed_min + speed_max) / 2
        speed_range = speed_max - speed_min
        speed_fit = 1.0 - abs(profile.avg_club_speed - speed_center) / (speed_range / 2)
        score += max(0.0, speed_fit * 20)

    # Recency bonus (10 points)
    model_year = club.get("model_year", CURRENT_YEAR)
    years_old = CURRENT_YEAR - model_year
    score += max(0, 10 - years_old * 2)

    return round(score, 1)


def rank_recommendations(
    profile: SwingProfile,
    clubs: list[dict],
    top_n: int = 5,
) -> list[dict]:
    scored = []
    for club in clubs:
        s = score_club(profile, club)
        scored.append({"club": club, "score": s})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]
