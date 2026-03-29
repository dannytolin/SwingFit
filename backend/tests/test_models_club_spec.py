import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.club_spec import ClubSpec


engine = create_engine("sqlite:///:memory:")
TestSession = sessionmaker(bind=engine)


def setup_module():
    Base.metadata.create_all(engine)


def teardown_module():
    Base.metadata.drop_all(engine)


def test_create_driver_spec():
    session = TestSession()
    club = ClubSpec(
        brand="TaylorMade",
        model_name="Qi10 Max",
        model_year=2025,
        club_type="driver",
        loft=10.5,
        lie_angle=56.0,
        shaft_options=json.dumps(["Fujikura Speeder NX", "Project X HZRDUS"]),
        head_weight=200.0,
        adjustable=True,
        loft_range_min=8.5,
        loft_range_max=12.5,
        launch_bias="mid",
        spin_bias="low",
        forgiveness_rating=9,
        workability_rating=4,
        swing_speed_min=85.0,
        swing_speed_max=115.0,
        msrp=599.99,
        avg_used_price=420.0,
        still_in_production=True,
    )
    session.add(club)
    session.commit()
    session.refresh(club)

    assert club.id is not None
    assert club.brand == "TaylorMade"
    assert club.club_type == "driver"
    assert club.adjustable is True
    assert club.swing_speed_min == 85.0
    session.close()


def test_create_iron_spec():
    session = TestSession()
    club = ClubSpec(
        brand="Titleist",
        model_name="T150",
        model_year=2024,
        club_type="iron",
        loft=33.0,
        lie_angle=62.5,
        shaft_options=json.dumps(["True Temper AMT Black"]),
        head_weight=265.0,
        adjustable=False,
        launch_bias="mid",
        spin_bias="mid",
        forgiveness_rating=5,
        workability_rating=8,
        swing_speed_min=80.0,
        swing_speed_max=110.0,
        msrp=1399.99,
        still_in_production=True,
    )
    session.add(club)
    session.commit()
    session.refresh(club)

    assert club.id is not None
    assert club.club_type == "iron"
    assert club.adjustable is False
    assert club.loft_range_min is None
    session.close()
