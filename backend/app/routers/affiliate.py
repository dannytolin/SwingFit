from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.club_spec import ClubSpec
from backend.app.models.click import AffiliateClick
from backend.app.models.user import User
from backend.app.routers.auth import get_current_user
from backend.app.services.affiliate import get_buy_links

router = APIRouter(tags=["affiliate"])


@router.get("/clubs/{club_id}/buy-links")
def get_club_buy_links(club_id: int, db: Session = Depends(get_db)):
    club = db.query(ClubSpec).filter(ClubSpec.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    club_dict = {
        "id": club.id,
        "brand": club.brand,
        "model_name": club.model_name,
        "club_type": club.club_type,
        "msrp": club.msrp,
        "avg_used_price": club.avg_used_price,
        "still_in_production": club.still_in_production,
    }
    return get_buy_links(club_dict)


class ClickTrackRequest(BaseModel):
    club_spec_id: int
    retailer: str
    url: str


@router.post("/affiliate/click", status_code=201)
def track_click(req: ClickTrackRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    click = AffiliateClick(
        user_id=user.id,
        club_spec_id=req.club_spec_id,
        retailer=req.retailer,
        url=req.url,
    )
    db.add(click)
    db.commit()
    db.refresh(click)
    return {
        "id": click.id,
        "user_id": click.user_id,
        "club_spec_id": click.club_spec_id,
        "retailer": click.retailer,
        "clicked_at": click.clicked_at.isoformat(),
    }
