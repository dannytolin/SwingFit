from backend.app.services.swing_profile import SwingProfile
from backend.app.services.fitting_engine import (
    OPTIMAL_LAUNCH,
    OPTIMAL_SPIN,
    HIGH_DISPERSION_THRESHOLD,
)


def generate_explanation(profile: SwingProfile, club: dict) -> str:
    brand = club.get("brand", "")
    model = club.get("model_name", "")
    club_name = f"{brand} {model}".strip()

    reasons: list[str] = []

    optimal_launch = OPTIMAL_LAUNCH.get(profile.club_type, (12.0, 15.0))
    if profile.avg_launch_angle > optimal_launch[1]:
        diff = round(profile.avg_launch_angle - optimal_launch[1], 1)
        if club.get("launch_bias") == "low":
            reasons.append(
                f"Your launch angle ({profile.avg_launch_angle:.1f}°) is {diff}° above optimal. "
                f"The {club_name}'s low-launch design should bring that down into the {optimal_launch[0]:.0f}-{optimal_launch[1]:.0f}° window."
            )
    elif profile.avg_launch_angle < optimal_launch[0]:
        diff = round(optimal_launch[0] - profile.avg_launch_angle, 1)
        if club.get("launch_bias") == "high":
            reasons.append(
                f"Your launch angle ({profile.avg_launch_angle:.1f}°) is {diff}° below optimal. "
                f"The {club_name}'s high-launch profile should help get the ball up."
            )

    optimal_spin = OPTIMAL_SPIN.get(profile.club_type, (2000.0, 2500.0))
    if profile.avg_spin_rate > optimal_spin[1]:
        excess = round(profile.avg_spin_rate - optimal_spin[1])
        if club.get("spin_bias") == "low":
            reasons.append(
                f"Your spin rate ({profile.avg_spin_rate:.0f} rpm) is ~{excess} rpm above optimal. "
                f"The {club_name} is a low-spin head that could reduce spin by 200-400 rpm and add 5-10 yards of carry."
            )
    elif profile.avg_spin_rate < optimal_spin[0]:
        deficit = round(optimal_spin[0] - profile.avg_spin_rate)
        if club.get("spin_bias") == "high":
            reasons.append(
                f"Your spin rate ({profile.avg_spin_rate:.0f} rpm) is ~{deficit} rpm below optimal. "
                f"The {club_name} adds spin to improve ball flight and stopping power."
            )

    dispersion = profile.std_offline if profile.std_offline is not None else profile.std_carry
    forgiveness = club.get("forgiveness_rating") or 5
    if dispersion > HIGH_DISPERSION_THRESHOLD and forgiveness >= 7:
        reasons.append(
            f"Your shot dispersion is {dispersion:.1f} yards — the {club_name} has a "
            f"forgiveness rating of {forgiveness}/10, which should tighten up your misses."
        )
    elif dispersion <= HIGH_DISPERSION_THRESHOLD:
        workability = club.get("workability_rating") or 5
        if workability >= 7:
            reasons.append(
                f"Your tight dispersion ({dispersion:.1f} yd) means you can benefit from "
                f"the {club_name}'s workability ({workability}/10) for shot shaping."
            )

    speed_min = club.get("swing_speed_min")
    speed_max = club.get("swing_speed_max")
    if speed_min and speed_max:
        reasons.append(
            f"Your club speed ({profile.avg_club_speed:.0f} mph) fits well in the "
            f"{club_name}'s designed range of {speed_min:.0f}-{speed_max:.0f} mph."
        )

    if not reasons:
        reasons.append(
            f"The {club_name} is a well-rounded match for your swing profile."
        )

    return " ".join(reasons)
