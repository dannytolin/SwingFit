from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.models.user import User
from backend.app.schemas.session import SwingSessionCreate, SwingSessionRead
from backend.app.schemas.shot import ShotCreate, ShotRead

router = APIRouter(tags=["sessions"])


@router.post("/users/{user_id}/sessions", response_model=SwingSessionRead, status_code=201)
def create_session(user_id: int, session_data: SwingSessionCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    swing_session = SwingSession(user_id=user_id, **session_data.model_dump())
    db.add(swing_session)
    db.commit()
    db.refresh(swing_session)
    return swing_session


@router.post("/sessions/{session_id}/shots", response_model=list[ShotRead], status_code=201)
def add_shots(session_id: int, shots: list[ShotCreate], db: Session = Depends(get_db)):
    swing_session = db.query(SwingSession).filter(SwingSession.id == session_id).first()
    if not swing_session:
        raise HTTPException(status_code=404, detail="Session not found")
    db_shots = []
    for shot_data in shots:
        shot = Shot(session_id=session_id, **shot_data.model_dump())
        db.add(shot)
        db_shots.append(shot)
    db.commit()
    for shot in db_shots:
        db.refresh(shot)
    return db_shots


@router.get("/sessions/{session_id}/summary")
def get_session_summary(session_id: int, db: Session = Depends(get_db)):
    swing_session = db.query(SwingSession).filter(SwingSession.id == session_id).first()
    if not swing_session:
        raise HTTPException(status_code=404, detail="Session not found")

    shots = db.query(Shot).filter(
        Shot.session_id == session_id,
        Shot.is_valid == True,
    ).all()

    if not shots:
        return {}

    clubs: dict[str, list[Shot]] = {}
    for shot in shots:
        clubs.setdefault(shot.club_used, []).append(shot)

    summary = {}
    for club_name, club_shots in clubs.items():
        n = len(club_shots)

        def avg(attr: str, _shots=club_shots) -> float | None:
            vals = [getattr(s, attr) for s in _shots if getattr(s, attr) is not None]
            return round(sum(vals) / len(vals), 1) if vals else None

        summary[club_name] = {
            "shot_count": n,
            "avg_ball_speed": avg("ball_speed"),
            "avg_launch_angle": avg("launch_angle"),
            "avg_spin_rate": avg("spin_rate"),
            "avg_carry": avg("carry_distance"),
            "avg_total": avg("total_distance"),
            "avg_club_speed": avg("club_speed"),
            "avg_smash_factor": avg("smash_factor"),
            "avg_attack_angle": avg("attack_angle"),
            "avg_club_path": avg("club_path"),
            "avg_face_angle": avg("face_angle"),
            "avg_offline": avg("offline_distance"),
        }

    return summary
