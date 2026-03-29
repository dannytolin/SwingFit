import hashlib

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.models.user import User
from backend.app.schemas.shot import ShotCreate
from backend.app.services.data_quality import get_data_quality
from backend.app.services.parsers.trackman.csv_export import is_trackman_csv, parse_trackman_csv
from backend.app.services.parsers.trackman.report_vision import (
    TrackmanReportParser,
    normalize_vision_response,
)
from backend.app.services.parsers.garmin_r10 import is_garmin_r10_csv, parse_garmin_r10_csv
from backend.app.services.parsers.generic_csv import parse_generic_csv
from backend.app.utils.club_normalizer import normalize_club_name

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _detect_and_parse(csv_text: str) -> tuple[str, str, list[ShotCreate]]:
    header_line = csv_text.split("\n", 1)[0]
    # Check Garmin before Trackman: Garmin uses exact column names with units,
    # while Trackman strips units for matching — Garmin headers overlap with
    # the Trackman base-name signature, so Garmin must be checked first.
    if is_garmin_r10_csv(header_line):
        shots = parse_garmin_r10_csv(csv_text)
        return "garmin_r10", "file_upload", shots
    if is_trackman_csv(header_line):
        shots = parse_trackman_csv(csv_text)
        return "trackman_4", "file_upload", shots
    shots = parse_generic_csv(csv_text)
    return "generic", "file_upload", shots


@router.post("/upload", status_code=201)
async def upload_session_file(
    user_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    content = await file.read()
    csv_text = content.decode("utf-8")
    file_hash = hashlib.sha256(content).hexdigest()
    existing = db.query(SwingSession).filter(
        SwingSession.user_id == user_id,
        SwingSession.source_file_hash == file_hash,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Duplicate file — this session was already uploaded")
    launch_monitor_type, data_source, shots = _detect_and_parse(csv_text)
    swing_session = SwingSession(
        user_id=user_id,
        launch_monitor_type=launch_monitor_type,
        data_source=data_source,
        source_file_name=file.filename,
        source_file_hash=file_hash,
    )
    db.add(swing_session)
    db.commit()
    db.refresh(swing_session)
    for shot_data in shots:
        shot = Shot(session_id=swing_session.id, **shot_data.model_dump())
        db.add(shot)
    db.commit()
    dq = get_data_quality(launch_monitor_type, data_source)
    return {
        "session": {
            "id": swing_session.id,
            "launch_monitor_type": launch_monitor_type,
            "data_source": data_source,
            "source_file_name": file.filename,
        },
        "shot_count": len(shots),
        "data_quality": dq,
    }


@router.post("/manual", status_code=201)
async def manual_entry(
    user_id: int,
    club_type: str,
    ball_speed: float,
    launch_angle: float,
    spin_rate: float,
    carry_distance: float,
    club_speed: float | None = None,
    total_distance: float | None = None,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    swing_session = SwingSession(
        user_id=user_id,
        launch_monitor_type="manual",
        data_source="manual_entry",
    )
    db.add(swing_session)
    db.commit()
    db.refresh(swing_session)
    shot = Shot(
        session_id=swing_session.id,
        club_used=normalize_club_name(club_type),
        ball_speed=ball_speed,
        launch_angle=launch_angle,
        spin_rate=spin_rate,
        carry_distance=carry_distance,
        total_distance=total_distance,
        club_speed=club_speed,
        shot_number=1,
    )
    db.add(shot)
    db.commit()
    dq = get_data_quality("manual", "manual_entry")
    return {
        "session": {
            "id": swing_session.id,
            "launch_monitor_type": "manual",
            "data_source": "manual_entry",
        },
        "shot_count": 1,
        "data_quality": dq,
    }


@router.post("/trackman-report", status_code=201)
async def upload_trackman_report(
    user_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    content = await file.read()
    media_type = file.content_type or "image/png"
    parser = TrackmanReportParser()
    vision_result = parser.extract_from_image(content, media_type)
    shots = normalize_vision_response(vision_result)
    confidence = vision_result.get("confidence", 0.0)
    swing_session = SwingSession(
        user_id=user_id,
        launch_monitor_type="trackman_4",
        data_source="ocr_vision",
        source_file_name=file.filename,
    )
    db.add(swing_session)
    db.commit()
    db.refresh(swing_session)
    for shot_data in shots:
        shot = Shot(session_id=swing_session.id, **shot_data.model_dump())
        db.add(shot)
    db.commit()
    dq = get_data_quality("trackman_4", "ocr_vision")
    return {
        "session": {
            "id": swing_session.id,
            "launch_monitor_type": "trackman_4",
            "data_source": "ocr_vision",
            "source_file_name": file.filename,
        },
        "shot_count": len(shots),
        "confidence": confidence,
        "low_confidence_warning": confidence < 0.7,
        "data_quality": dq,
        "extracted_data": vision_result,
    }
