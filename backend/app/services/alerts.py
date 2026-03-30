from sqlalchemy.orm import Session
from backend.app.models.club_spec import ClubSpec
from backend.app.models.user import User
from backend.app.services.swing_profile import compute_swing_profile
from backend.app.services.fitting_engine import score_club, rank_recommendations


def compute_new_club_alerts(db: Session, new_club_id: int) -> list[dict]:
    new_club = db.query(ClubSpec).filter(ClubSpec.id == new_club_id).first()
    if not new_club:
        return []

    club_type = new_club.club_type
    new_club_dict = {
        "id": new_club.id, "brand": new_club.brand, "model_name": new_club.model_name,
        "model_year": new_club.model_year, "club_type": new_club.club_type,
        "loft": new_club.loft, "launch_bias": new_club.launch_bias,
        "spin_bias": new_club.spin_bias, "forgiveness_rating": new_club.forgiveness_rating,
        "workability_rating": new_club.workability_rating,
        "swing_speed_min": new_club.swing_speed_min, "swing_speed_max": new_club.swing_speed_max,
        "msrp": new_club.msrp, "avg_used_price": new_club.avg_used_price,
        "still_in_production": new_club.still_in_production,
    }

    pro_users = db.query(User).filter(User.subscription_tier == "pro").all()

    alerts = []
    for user in pro_users:
        profile = compute_swing_profile(db, user.id, club_type)
        if profile is None:
            continue

        new_score = score_club(profile, new_club_dict)

        existing = db.query(ClubSpec).filter(ClubSpec.club_type == club_type, ClubSpec.id != new_club.id).all()
        existing_dicts = []
        for c in existing:
            existing_dicts.append({
                "id": c.id, "brand": c.brand, "model_name": c.model_name,
                "model_year": c.model_year, "club_type": c.club_type,
                "launch_bias": c.launch_bias, "spin_bias": c.spin_bias,
                "forgiveness_rating": c.forgiveness_rating, "workability_rating": c.workability_rating,
                "swing_speed_min": c.swing_speed_min, "swing_speed_max": c.swing_speed_max,
                "msrp": c.msrp, "avg_used_price": c.avg_used_price,
                "still_in_production": c.still_in_production,
            })

        all_clubs = existing_dicts + [new_club_dict]
        ranked = rank_recommendations(profile, all_clubs, top_n=3)
        top_3_ids = [r["club"]["id"] for r in ranked]

        if new_club.id in top_3_ids:
            alerts.append({
                "user_id": user.id, "email": user.email,
                "club_name": f"{new_club.brand} {new_club.model_name}",
                "club_type": club_type, "score": new_score,
            })

    return alerts
