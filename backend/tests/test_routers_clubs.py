import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


def setup_module():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(engine)


def teardown_module():
    Base.metadata.drop_all(engine)
    app.dependency_overrides.pop(get_db, None)


DRIVER_DATA = {
    "brand": "TaylorMade",
    "model_name": "Qi10 Max",
    "model_year": 2025,
    "club_type": "driver",
    "loft": 10.5,
    "launch_bias": "mid",
    "spin_bias": "low",
    "forgiveness_rating": 9,
    "workability_rating": 4,
    "swing_speed_min": 85.0,
    "swing_speed_max": 115.0,
    "msrp": 599.99,
    "still_in_production": True,
}


def test_create_club():
    response = client.post("/clubs", json=DRIVER_DATA)
    assert response.status_code == 201
    data = response.json()
    assert data["brand"] == "TaylorMade"
    assert data["id"] is not None


def test_get_club_by_id():
    create_resp = client.post("/clubs", json={
        **DRIVER_DATA,
        "model_name": "Stealth 2",
        "model_year": 2023,
    })
    club_id = create_resp.json()["id"]

    response = client.get(f"/clubs/{club_id}")
    assert response.status_code == 200
    assert response.json()["model_name"] == "Stealth 2"


def test_get_club_not_found():
    response = client.get("/clubs/9999")
    assert response.status_code == 404


def test_list_clubs():
    response = client.get("/clubs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_search_clubs_by_brand():
    response = client.get("/clubs/search", params={"brand": "TaylorMade"})
    assert response.status_code == 200
    data = response.json()
    assert all(c["brand"] == "TaylorMade" for c in data)


def test_search_clubs_by_type():
    response = client.get("/clubs/search", params={"club_type": "driver"})
    assert response.status_code == 200
    data = response.json()
    assert all(c["club_type"] == "driver" for c in data)


def test_search_clubs_by_swing_speed():
    response = client.get("/clubs/search", params={"swing_speed": 100.0})
    assert response.status_code == 200
    data = response.json()
    for club in data:
        if club["swing_speed_min"] and club["swing_speed_max"]:
            assert club["swing_speed_min"] <= 100.0 <= club["swing_speed_max"]
