import numpy as np
import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.user import User
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.services.swing_profile import compute_swing_profile, SwingProfile


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)


def setup_module():
    Base.metadata.create_all(engine)
    db = TestSession()
    user = User(email="profile@test.com", username="profiler", hashed_password="h")
    db.add(user)
    db.commit()

    session = SwingSession(
        user_id=user.id,
        launch_monitor_type="trackman_4",
        data_source="file_upload",
    )
    db.add(session)
    db.commit()

    # 5 driver shots with realistic spread
    driver_shots = [
        {"ball_speed": 149.0, "launch_angle": 12.0, "spin_rate": 2800.0, "carry_distance": 248.0,
         "club_speed": 105.0, "attack_angle": -1.2, "club_path": 2.0, "face_angle": 0.5,
         "face_to_path": -1.5, "offline_distance": 8.0, "smash_factor": 1.42},
        {"ball_speed": 151.0, "launch_angle": 11.5, "spin_rate": 2650.0, "carry_distance": 255.0,
         "club_speed": 107.0, "attack_angle": -0.8, "club_path": 1.5, "face_angle": 0.3,
         "face_to_path": -1.2, "offline_distance": 4.0, "smash_factor": 1.41},
        {"ball_speed": 148.0, "launch_angle": 13.0, "spin_rate": 2900.0, "carry_distance": 245.0,
         "club_speed": 104.0, "attack_angle": -1.5, "club_path": 2.5, "face_angle": 1.0,
         "face_to_path": -1.5, "offline_distance": -5.0, "smash_factor": 1.42},
        {"ball_speed": 150.0, "launch_angle": 12.5, "spin_rate": 2750.0, "carry_distance": 250.0,
         "club_speed": 106.0, "attack_angle": -1.0, "club_path": 1.8, "face_angle": 0.6,
         "face_to_path": -1.2, "offline_distance": 6.0, "smash_factor": 1.42},
        {"ball_speed": 152.0, "launch_angle": 11.8, "spin_rate": 2700.0, "carry_distance": 258.0,
         "club_speed": 108.0, "attack_angle": -0.5, "club_path": 1.2, "face_angle": 0.2,
         "face_to_path": -1.0, "offline_distance": 3.0, "smash_factor": 1.41},
    ]
    for i, data in enumerate(driver_shots):
        shot = Shot(
            session_id=session.id,
            club_used="driver",
            shot_number=i + 1,
            **data,
        )
        db.add(shot)

    # 1 invalid shot (should be excluded)
    invalid_shot = Shot(
        session_id=session.id,
        club_used="driver",
        ball_speed=50.0, launch_angle=5.0, spin_rate=1000.0,
        carry_distance=80.0, shot_number=6, is_valid=False,
    )
    db.add(invalid_shot)

    # 2 iron shots
    for i in range(2):
        shot = Shot(
            session_id=session.id,
            club_used="7-iron",
            ball_speed=120.0 + i,
            launch_angle=18.0 + i * 0.5,
            spin_rate=6400.0 + i * 100,
            carry_distance=165.0 + i * 2,
            club_speed=82.0 + i,
            shot_number=7 + i,
        )
        db.add(shot)

    db.commit()
    db.close()


def teardown_module():
    Base.metadata.drop_all(engine)


def test_compute_swing_profile_driver():
    db = TestSession()
    profile = compute_swing_profile(db, user_id=1, club_type="driver")
    db.close()

    assert isinstance(profile, SwingProfile)
    assert profile.club_type == "driver"
    assert profile.sample_size == 5  # excludes invalid shot
    assert round(profile.avg_ball_speed, 1) == 150.0
    assert round(profile.avg_carry, 1) == 251.2
    assert round(profile.avg_club_speed, 1) == 106.0
    assert round(profile.avg_launch_angle, 1) == 12.2
    assert round(profile.avg_spin_rate, 1) == 2760.0
    assert profile.avg_attack_angle is not None
    assert profile.std_carry > 0
    assert profile.data_quality == "low"  # < 20 shots


def test_swing_profile_shot_shape():
    db = TestSession()
    profile = compute_swing_profile(db, user_id=1, club_type="driver")
    db.close()

    # avg face_to_path is around -1.3 (between -2 and 2) → straight
    assert profile.shot_shape_tendency == "straight"


def test_swing_profile_iron():
    db = TestSession()
    profile = compute_swing_profile(db, user_id=1, club_type="7-iron")
    db.close()

    assert profile.club_type == "7-iron"
    assert profile.sample_size == 2
    assert profile.data_quality == "low"


def test_swing_profile_no_shots():
    db = TestSession()
    profile = compute_swing_profile(db, user_id=1, club_type="putter")
    db.close()

    assert profile is None


def test_swing_profile_smash_factor():
    db = TestSession()
    profile = compute_swing_profile(db, user_id=1, club_type="driver")
    db.close()

    assert round(profile.smash_factor, 2) == 1.42
