from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.user import User
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot


engine = create_engine("sqlite:///:memory:")
TestSession = sessionmaker(bind=engine)


def setup_module():
    Base.metadata.create_all(engine)


def teardown_module():
    Base.metadata.drop_all(engine)


def test_create_session_with_shots():
    db = TestSession()

    user = User(email="test@example.com", username="tester", hashed_password="h")
    db.add(user)
    db.commit()
    db.refresh(user)

    swing_session = SwingSession(
        user_id=user.id,
        session_date=datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc),
        launch_monitor_type="trackman_4",
        location="indoor",
        data_source="file_upload",
        source_file_name="session_export.csv",
    )
    db.add(swing_session)
    db.commit()
    db.refresh(swing_session)

    assert swing_session.id is not None
    assert swing_session.user_id == user.id

    shot = Shot(
        session_id=swing_session.id,
        club_used="driver",
        ball_speed=149.8,
        launch_angle=12.3,
        spin_rate=2845.0,
        carry_distance=248.0,
        total_distance=271.0,
        club_speed=105.2,
        smash_factor=1.42,
        attack_angle=-1.2,
        club_path=2.1,
        face_angle=0.8,
        face_to_path=-1.3,
        spin_axis=3.2,
        offline_distance=8.0,
        apex_height=98.0,
        landing_angle=38.5,
        shot_number=1,
    )
    db.add(shot)
    db.commit()
    db.refresh(shot)

    assert shot.id is not None
    assert shot.session_id == swing_session.id
    assert shot.ball_speed == 149.8
    assert shot.is_valid is True
    db.close()


def test_session_shots_relationship():
    db = TestSession()

    user = User(email="rel@example.com", username="rel", hashed_password="h")
    db.add(user)
    db.commit()

    swing_session = SwingSession(
        user_id=user.id,
        session_date=datetime(2025, 6, 15, tzinfo=timezone.utc),
        launch_monitor_type="garmin_r10",
        data_source="file_upload",
    )
    db.add(swing_session)
    db.commit()

    for i in range(3):
        shot = Shot(
            session_id=swing_session.id,
            club_used="7-iron",
            ball_speed=120.0 + i,
            launch_angle=18.0,
            spin_rate=6400.0,
            carry_distance=165.0 + i,
            shot_number=i + 1,
        )
        db.add(shot)
    db.commit()

    db.refresh(swing_session)
    assert len(swing_session.shots) == 3
    assert swing_session.shots[0].club_used == "7-iron"
    db.close()
