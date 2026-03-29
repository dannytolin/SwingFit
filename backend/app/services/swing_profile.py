from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot


@dataclass
class SwingProfile:
    club_type: str
    avg_club_speed: float
    avg_ball_speed: float
    avg_launch_angle: float
    avg_spin_rate: float
    avg_carry: float
    avg_attack_angle: float | None
    avg_club_path: float | None
    avg_face_angle: float | None
    std_carry: float
    std_offline: float | None
    shot_shape_tendency: str
    miss_direction: str
    smash_factor: float
    spin_loft_estimate: float | None
    sample_size: int
    data_quality: str


def compute_swing_profile(
    db: Session,
    user_id: int,
    club_type: str,
) -> SwingProfile | None:
    session_ids = [
        s.id for s in db.query(SwingSession.id).filter(
            SwingSession.user_id == user_id
        ).all()
    ]
    if not session_ids:
        return None

    shots = db.query(Shot).filter(
        Shot.session_id.in_(session_ids),
        Shot.club_used == club_type,
        Shot.is_valid == True,
    ).all()

    if not shots:
        return None

    n = len(shots)

    def avg(attr: str) -> float | None:
        vals = [getattr(s, attr) for s in shots if getattr(s, attr) is not None]
        return float(np.mean(vals)) if vals else None

    def std(attr: str) -> float | None:
        vals = [getattr(s, attr) for s in shots if getattr(s, attr) is not None]
        return float(np.std(vals, ddof=0)) if len(vals) >= 2 else None

    avg_club_speed = avg("club_speed") or 0.0
    avg_ball_speed = avg("ball_speed") or 0.0
    avg_launch = avg("launch_angle") or 0.0
    avg_spin = avg("spin_rate") or 0.0
    avg_carry = avg("carry_distance") or 0.0
    avg_attack = avg("attack_angle")
    avg_path = avg("club_path")
    avg_face = avg("face_angle")
    avg_ftp = avg("face_to_path")
    std_ftp = std("face_to_path")

    if std_ftp is not None and std_ftp > 4.0:
        shot_shape = "variable"
    elif avg_ftp is not None and avg_ftp < -2.0:
        shot_shape = "draw"
    elif avg_ftp is not None and avg_ftp > 2.0:
        shot_shape = "fade"
    else:
        shot_shape = "straight"

    offlines = [s.offline_distance for s in shots if s.offline_distance is not None]
    if offlines:
        avg_offline = float(np.mean(offlines))
        if avg_offline > 3.0:
            miss_dir = "right"
        elif avg_offline < -3.0:
            miss_dir = "left"
        else:
            miss_dir = "both"
    else:
        miss_dir = "both"

    smash_vals = [s.smash_factor for s in shots if s.smash_factor is not None]
    smash = float(np.mean(smash_vals)) if smash_vals else (
        avg_ball_speed / avg_club_speed if avg_club_speed > 0 else 0.0
    )

    spin_loft = (avg_launch + abs(avg_attack)) if avg_attack is not None else None

    if n >= 50:
        quality = "high"
    elif n >= 20:
        quality = "medium"
    else:
        quality = "low"

    return SwingProfile(
        club_type=club_type,
        avg_club_speed=avg_club_speed,
        avg_ball_speed=avg_ball_speed,
        avg_launch_angle=avg_launch,
        avg_spin_rate=avg_spin,
        avg_carry=avg_carry,
        avg_attack_angle=avg_attack,
        avg_club_path=avg_path,
        avg_face_angle=avg_face,
        std_carry=std("carry_distance") or 0.0,
        std_offline=std("offline_distance"),
        shot_shape_tendency=shot_shape,
        miss_direction=miss_dir,
        smash_factor=smash,
        spin_loft_estimate=spin_loft,
        sample_size=n,
        data_quality=quality,
    )
