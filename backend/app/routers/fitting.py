from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.club_spec import ClubSpec
from backend.app.models.user import User
from backend.app.services.swing_profile import compute_swing_profile
from backend.app.services.fitting_engine import score_club, rank_recommendations
from backend.app.services.explanation import generate_explanation
from backend.app.services.affiliate import get_buy_links

router = APIRouter(tags=["fitting"])


@router.get("/users/{user_id}/swing-profile")
def get_swing_profile(user_id: int, club_type: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = compute_swing_profile(db, user_id, club_type)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No valid shots found for {club_type}")
    return asdict(profile)


class RecommendRequest(BaseModel):
    user_id: int
    club_type: str
    budget_max: float | None = None
    include_used: bool = False
    top_n: int = 5


@router.post("/fitting/recommend")
def recommend_clubs(req: RecommendRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = compute_swing_profile(db, req.user_id, req.club_type)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No valid shots found for {req.club_type}")

    query = db.query(ClubSpec).filter(ClubSpec.club_type == req.club_type)
    if profile.avg_club_speed > 0:
        query = query.filter(
            ClubSpec.swing_speed_min <= profile.avg_club_speed,
            ClubSpec.swing_speed_max >= profile.avg_club_speed,
        )
    all_clubs = query.all()

    club_dicts = []
    for c in all_clubs:
        d = {
            "id": c.id, "brand": c.brand, "model_name": c.model_name,
            "model_year": c.model_year, "club_type": c.club_type,
            "loft": c.loft, "launch_bias": c.launch_bias,
            "spin_bias": c.spin_bias, "forgiveness_rating": c.forgiveness_rating,
            "workability_rating": c.workability_rating,
            "swing_speed_min": c.swing_speed_min, "swing_speed_max": c.swing_speed_max,
            "msrp": c.msrp, "avg_used_price": c.avg_used_price,
            "still_in_production": c.still_in_production,
        }
        if req.budget_max is not None:
            if req.include_used and d.get("avg_used_price"):
                if d["avg_used_price"] > req.budget_max:
                    continue
            elif d.get("msrp") and d["msrp"] > req.budget_max:
                continue
        club_dicts.append(d)

    ranked = rank_recommendations(profile, club_dicts, top_n=req.top_n)
    for rec in ranked:
        rec["explanation"] = generate_explanation(profile, rec["club"])
        rec["buy_links"] = get_buy_links(rec["club"], include_used=req.include_used)

    return {
        "profile": asdict(profile),
        "recommendations": ranked,
    }


class CompareRequest(BaseModel):
    user_id: int
    club_type: str
    current_club_id: int
    recommended_club_id: int


def _club_to_dict(club: ClubSpec) -> dict:
    return {
        "id": club.id,
        "brand": club.brand,
        "model_name": club.model_name,
        "model_year": club.model_year,
        "club_type": club.club_type,
        "loft": club.loft,
        "launch_bias": club.launch_bias,
        "spin_bias": club.spin_bias,
        "forgiveness_rating": club.forgiveness_rating,
        "workability_rating": club.workability_rating,
        "swing_speed_min": club.swing_speed_min,
        "swing_speed_max": club.swing_speed_max,
        "msrp": club.msrp,
        "avg_used_price": club.avg_used_price,
        "still_in_production": club.still_in_production,
    }


@router.post("/fitting/compare")
def compare_clubs(req: CompareRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = compute_swing_profile(db, req.user_id, req.club_type)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No valid shots found for {req.club_type}")

    current_club = db.query(ClubSpec).filter(ClubSpec.id == req.current_club_id).first()
    if not current_club:
        raise HTTPException(status_code=404, detail="Current club not found")

    rec_club = db.query(ClubSpec).filter(ClubSpec.id == req.recommended_club_id).first()
    if not rec_club:
        raise HTTPException(status_code=404, detail="Recommended club not found")

    current_dict = _club_to_dict(current_club)
    rec_dict = _club_to_dict(rec_club)

    current_score = score_club(profile, current_dict)
    rec_score = score_club(profile, rec_dict)
    explanation = generate_explanation(profile, rec_dict)

    return {
        "profile": asdict(profile),
        "current": current_dict,
        "recommended": rec_dict,
        "current_score": current_score,
        "recommended_score": rec_score,
        "score_difference": round(rec_score - current_score, 1),
        "explanation": explanation,
    }
