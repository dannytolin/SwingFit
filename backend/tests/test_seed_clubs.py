from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.club_spec import ClubSpec
from scripts.seed_clubs import seed_clubs_from_csv

engine = create_engine("sqlite:///:memory:")
TestSession = sessionmaker(bind=engine)


def setup_module():
    Base.metadata.create_all(engine)


def teardown_module():
    Base.metadata.drop_all(engine)


def test_seed_clubs_from_csv():
    db = TestSession()
    count = seed_clubs_from_csv(db, "data/club_specs/initial_seed.csv")
    assert count == 20
    db.close()


def test_seed_clubs_correct_data():
    db = TestSession()
    qi10 = db.query(ClubSpec).filter(
        ClubSpec.brand == "TaylorMade",
        ClubSpec.model_name == "Qi10 Max",
    ).first()
    assert qi10 is not None
    assert qi10.club_type == "driver"
    assert qi10.loft == 10.5
    assert qi10.adjustable is True
    assert qi10.swing_speed_min == 80.0

    drivers = db.query(ClubSpec).filter(ClubSpec.club_type == "driver").all()
    assert len(drivers) == 10

    irons = db.query(ClubSpec).filter(ClubSpec.club_type == "iron").all()
    assert len(irons) == 5

    wedges = db.query(ClubSpec).filter(ClubSpec.club_type == "wedge").all()
    assert len(wedges) == 5
    db.close()


def test_seed_clubs_idempotent():
    db = TestSession()
    count1 = seed_clubs_from_csv(db, "data/club_specs/initial_seed.csv")
    count2 = seed_clubs_from_csv(db, "data/club_specs/initial_seed.csv")
    # Second run should skip duplicates
    assert count2 == 0
    total = db.query(ClubSpec).count()
    assert total == 20
    db.close()
