from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base, get_db
from backend.app.main import app

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine)

def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

def setup_module():
    app.dependency_overrides[get_db] = _override_get_db
    Base.metadata.create_all(engine)

def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)

client = TestClient(app)

def test_register():
    response = client.post("/auth/register", json={
        "email": "golfer@example.com", "username": "golfer", "password": "swing123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "golfer@example.com"
    assert data["id"] is not None
    assert "password" not in data
    assert "hashed_password" not in data

def test_register_duplicate_email():
    client.post("/auth/register", json={"email": "dupe@example.com", "username": "a", "password": "pass123"})
    response = client.post("/auth/register", json={"email": "dupe@example.com", "username": "b", "password": "pass456"})
    assert response.status_code == 409

def test_login():
    client.post("/auth/register", json={"email": "login@example.com", "username": "logger", "password": "mypassword"})
    response = client.post("/auth/login", json={"email": "login@example.com", "password": "mypassword"})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["email"] == "login@example.com"

def test_login_wrong_password():
    client.post("/auth/register", json={"email": "wrong@example.com", "username": "wronger", "password": "correct"})
    response = client.post("/auth/login", json={"email": "wrong@example.com", "password": "incorrect"})
    assert response.status_code == 401

def test_login_nonexistent_user():
    response = client.post("/auth/login", json={"email": "noone@example.com", "password": "anything"})
    assert response.status_code == 401

def test_get_me():
    client.post("/auth/register", json={"email": "me@example.com", "username": "myself", "password": "secret"})
    login_resp = client.post("/auth/login", json={"email": "me@example.com", "password": "secret"})
    token = login_resp.json()["token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"

def test_get_me_no_token():
    response = client.get("/auth/me")
    assert response.status_code == 401
