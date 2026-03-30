import json
import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.club_spec import ClubSpec
from backend.app.models.recommendation import Recommendation
from backend.app.models.api_usage import ApiUsage
from backend.app.models.user import User
from backend.app.routers.auth import get_current_user
from backend.app.services.swing_profile import compute_swing_profile
from backend.app.services.claude_fitter import (
    call_claude_for_recommendations,
    call_claude_for_comparison,
)
from backend.app.services.affiliate import get_buy_links

logger = logging.getLogger(__name__)

router = APIRouter(tags=["fitting"])


@router.get("/users/me/swing-profile")
def get_swing_profile(club_type: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = compute_swing_profile(db, user.id, club_type)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No valid shots found for {club_type}")
    return asdict(profile)


class RecommendRequest(BaseModel):
    club_type: str
    budget_max: float | None = None
    include_used: bool = False
    top_n: int = 5


def _club_to_dict(club: ClubSpec) -> dict:
    return {
        "id": club.id, "brand": club.brand, "model_name": club.model_name,
        "model_year": club.model_year, "club_type": club.club_type,
        "loft": club.loft, "launch_bias": club.launch_bias,
        "spin_bias": club.spin_bias, "forgiveness_rating": club.forgiveness_rating,
        "workability_rating": club.workability_rating,
        "swing_speed_min": club.swing_speed_min, "swing_speed_max": club.swing_speed_max,
        "msrp": club.msrp, "avg_used_price": club.avg_used_price,
        "still_in_production": club.still_in_production,
        "review_summary": getattr(club, "review_summary", None),
    }


def _hard_filter_clubs(db: Session, profile, req: RecommendRequest) -> list[dict]:
    """Hard-filter clubs by type, speed range, and budget. Returns list of dicts."""
    query = db.query(ClubSpec).filter(ClubSpec.club_type == req.club_type)
    if profile.avg_club_speed > 0:
        query = query.filter(
            ClubSpec.swing_speed_min <= profile.avg_club_speed,
            ClubSpec.swing_speed_max >= profile.avg_club_speed,
        )
    all_clubs = query.all()

    club_dicts = []
    for c in all_clubs:
        d = _club_to_dict(c)
        if req.budget_max is not None:
            if req.include_used and d.get("avg_used_price"):
                if d["avg_used_price"] > req.budget_max:
                    continue
            elif d.get("msrp") and d["msrp"] > req.budget_max:
                continue
        club_dicts.append(d)
    return club_dicts


def _log_api_usage(db: Session, user_id: int, endpoint: str, usage: dict):
    """Log a Claude API call for cost tracking."""
    db.add(ApiUsage(
        user_id=user_id,
        endpoint=endpoint,
        model="claude-sonnet-4-20250514",
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        estimated_cost=usage["estimated_cost"],
    ))
    db.commit()


def _cache_recommendations(db: Session, user_id: int, club_type: str, budget_max: float | None, recs: list[dict]):
    """Delete old cache and store new recommendations."""
    db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.club_type == club_type,
    ).delete()

    for rec in recs:
        db.add(Recommendation(
            user_id=user_id,
            club_type=club_type,
            club_spec_id=rec["club_spec_id"],
            match_score=rec["match_score"],
            explanation=rec["explanation"],
            projected_changes=json.dumps(rec.get("projected_changes", {})),
            best_for=rec.get("best_for"),
            recommended_build=json.dumps(rec.get("recommended_build", {})),
            budget_max=budget_max,
        ))
    db.commit()


def _read_cached_recommendations(db: Session, user_id: int, club_type: str) -> list[dict] | None:
    """Read cached recommendations. Returns None if no cache exists."""
    cached = db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.club_type == club_type,
    ).order_by(Recommendation.match_score.desc()).all()

    if not cached:
        return None

    results = []
    for rec in cached:
        club = db.query(ClubSpec).filter(ClubSpec.id == rec.club_spec_id).first()
        club_dict = _club_to_dict(club) if club else {"id": rec.club_spec_id}
        results.append({
            "club": club_dict,
            "score": rec.match_score,
            "explanation": rec.explanation,
            "projected_changes": json.loads(rec.projected_changes) if rec.projected_changes else {},
            "best_for": rec.best_for,
            "recommended_build": json.loads(rec.recommended_build) if rec.recommended_build else {},
            "buy_links": get_buy_links(club_dict) if club else [],
        })
    return results


@router.post("/fitting/recommend")
def recommend_clubs(req: RecommendRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = compute_swing_profile(db, user.id, req.club_type)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No valid shots found for {req.club_type}")

    club_dicts = _hard_filter_clubs(db, profile, req)
    if not club_dicts:
        return {"profile": asdict(profile), "recommendations": []}

    try:
        claude_recs, usage = call_claude_for_recommendations(profile, club_dicts)
        _log_api_usage(db, user.id, "fitting/recommend", usage)
        _cache_recommendations(db, user.id, req.club_type, req.budget_max, claude_recs)

        # Build response with club dicts and buy links
        club_lookup = {c["id"]: c for c in club_dicts}
        recommendations = []
        for rec in claude_recs:
            club = club_lookup.get(rec["club_spec_id"], {})
            recommendations.append({
                "club": club,
                "score": rec["match_score"],
                "explanation": rec["explanation"],
                "projected_changes": rec.get("projected_changes", {}),
                "best_for": rec.get("best_for"),
                "recommended_build": rec.get("recommended_build", {}),
                "buy_links": get_buy_links(club, include_used=req.include_used) if club else [],
            })

        return {"profile": asdict(profile), "recommendations": recommendations}

    except Exception as e:
        logger.error(f"Claude API call failed: {e}")
        # Fall back to cached recommendations
        cached = _read_cached_recommendations(db, user.id, req.club_type)
        if cached:
            return {"profile": asdict(profile), "recommendations": cached}
        raise HTTPException(status_code=503, detail="Recommendation engine temporarily unavailable")


@router.get("/fitting/recommendations")
def get_cached_recommendations(club_type: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Read cached recommendations without calling the Claude API."""
    cached = _read_cached_recommendations(db, user.id, club_type)
    if cached is None:
        raise HTTPException(status_code=404, detail="No cached recommendations. Call POST /fitting/recommend first.")

    profile = compute_swing_profile(db, user.id, club_type)
    return {
        "profile": asdict(profile) if profile else None,
        "recommendations": cached,
    }


class CompareRequest(BaseModel):
    club_type: str
    current_club_id: int
    recommended_club_id: int


@router.post("/fitting/compare")
def compare_clubs(req: CompareRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = compute_swing_profile(db, user.id, req.club_type)
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

    try:
        comparison, usage = call_claude_for_comparison(profile, current_dict, rec_dict)
        _log_api_usage(db, user.id, "fitting/compare", usage)

        return {
            "profile": asdict(profile),
            "current": current_dict,
            "recommended": rec_dict,
            "comparison": comparison,
        }
    except Exception as e:
        logger.error(f"Claude comparison failed: {e}")
        raise HTTPException(status_code=503, detail="Comparison engine temporarily unavailable")
