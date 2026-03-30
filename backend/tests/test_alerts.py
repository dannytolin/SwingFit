from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.user import User
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.models.club_spec import ClubSpec
from backend.app.services.alerts import compute_new_club_alerts

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine)

def setup_module():
    Base.metadata.create_all(engine)
    db = TestSession()

    # Pro user with driver shots
    pro = User(email="pro@test.com", username="pro", hashed_password="h", subscription_tier="pro")
    db.add(pro)
    db.commit()

    session = SwingSession(user_id=pro.id, launch_monitor_type="trackman_4", data_source="file_upload")
    db.add(session)
    db.commit()

    for i in range(5):
        db.add(Shot(session_id=session.id, club_used="driver",
            ball_speed=150.0+i, launch_angle=14.0, spin_rate=3100.0,
            carry_distance=248.0+i, club_speed=105.0, smash_factor=1.42,
            offline_distance=8.0, shot_number=i+1))

    # Free user (should not get alerts)
    free = User(email="free@test.com", username="free", hashed_password="h", subscription_tier="free")
    db.add(free)
    db.commit()

    session2 = SwingSession(user_id=free.id, launch_monitor_type="trackman_4", data_source="file_upload")
    db.add(session2)
    db.commit()

    for i in range(5):
        db.add(Shot(session_id=session2.id, club_used="driver",
            ball_speed=150.0, launch_angle=14.0, spin_rate=3100.0,
            carry_distance=248.0, club_speed=105.0, smash_factor=1.42,
            offline_distance=8.0, shot_number=i+1))

    # Existing club
    db.add(ClubSpec(brand="Existing", model_name="Club A", model_year=2024, club_type="driver",
        launch_bias="mid", spin_bias="mid", forgiveness_rating=7, workability_rating=5,
        swing_speed_min=85.0, swing_speed_max=120.0))

    db.commit()
    db.close()

def teardown_module():
    Base.metadata.drop_all(engine)

def test_alerts_for_high_scoring_new_club():
    db = TestSession()
    new_club = ClubSpec(brand="NewBrand", model_name="SuperDriver", model_year=2026, club_type="driver",
        launch_bias="low", spin_bias="low", forgiveness_rating=8, workability_rating=7,
        swing_speed_min=90.0, swing_speed_max=120.0)
    db.add(new_club)
    db.commit()
    alerts = compute_new_club_alerts(db, new_club.id)
    db.close()
    assert len(alerts) >= 1
    user_ids = [a["user_id"] for a in alerts]
    assert 1 in user_ids  # pro user
    assert 2 not in user_ids  # free user

def test_alerts_include_score():
    db = TestSession()
    new_club = db.query(ClubSpec).filter(ClubSpec.model_name == "SuperDriver").first()
    alerts = compute_new_club_alerts(db, new_club.id)
    db.close()
    for alert in alerts:
        assert "score" in alert
        assert "club_name" in alert
        assert alert["score"] > 0

def test_no_alerts_for_irrelevant_club():
    db = TestSession()
    iron = ClubSpec(brand="IronCo", model_name="IronX", model_year=2026, club_type="iron",
        launch_bias="mid", spin_bias="mid", forgiveness_rating=6, workability_rating=6,
        swing_speed_min=70.0, swing_speed_max=100.0)
    db.add(iron)
    db.commit()
    alerts = compute_new_club_alerts(db, iron.id)
    db.close()
    assert len(alerts) == 0
