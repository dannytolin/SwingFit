from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.club_spec import ClubSpec
from backend.app.schemas.club_spec import ClubSpecCreate, ClubSpecRead, ClubSpecSearch

router = APIRouter(prefix="/clubs", tags=["clubs"])


@router.post("", response_model=ClubSpecRead, status_code=201)
def create_club(club: ClubSpecCreate, db: Session = Depends(get_db)):
    db_club = ClubSpec(**club.model_dump())
    db.add(db_club)
    db.commit()
    db.refresh(db_club)
    return db_club


@router.get("", response_model=list[ClubSpecRead])
def list_clubs(db: Session = Depends(get_db)):
    return db.query(ClubSpec).all()


@router.get("/search", response_model=list[ClubSpecRead])
def search_clubs(
    brand: str | None = None,
    club_type: str | None = None,
    model_year: int | None = None,
    swing_speed: float | None = None,
    launch_bias: str | None = None,
    spin_bias: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(ClubSpec)
    if brand:
        query = query.filter(ClubSpec.brand == brand)
    if club_type:
        query = query.filter(ClubSpec.club_type == club_type)
    if model_year:
        query = query.filter(ClubSpec.model_year == model_year)
    if swing_speed is not None:
        query = query.filter(
            ClubSpec.swing_speed_min <= swing_speed,
            ClubSpec.swing_speed_max >= swing_speed,
        )
    if launch_bias:
        query = query.filter(ClubSpec.launch_bias == launch_bias)
    if spin_bias:
        query = query.filter(ClubSpec.spin_bias == spin_bias)
    return query.all()


@router.get("/{club_id}", response_model=ClubSpecRead)
def get_club(club_id: int, db: Session = Depends(get_db)):
    club = db.query(ClubSpec).filter(ClubSpec.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return club
