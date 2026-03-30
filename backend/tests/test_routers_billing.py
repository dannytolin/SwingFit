from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User
from backend.app.services.auth import hash_password, create_token

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine)

TOKEN = None
USER_ID = None

def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

def setup_module():
    app.dependency_overrides[get_db] = _override_get_db
    Base.metadata.create_all(engine)
    db = TestSession()
    user = User(email="billing@test.com", username="biller", hashed_password=hash_password("pass"))
    db.add(user)
    db.commit()
    global TOKEN, USER_ID
    TOKEN = create_token(user_id=user.id)
    USER_ID = user.id
    db.close()

def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)

client = TestClient(app)

@patch("backend.app.routers.billing.stripe")
def test_create_checkout_session(mock_stripe):
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/test")
    response = client.post("/billing/checkout", json={"plan": "monthly"},
        headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200
    assert response.json()["checkout_url"] == "https://checkout.stripe.com/test"

def test_checkout_requires_auth():
    response = client.post("/billing/checkout", json={"plan": "monthly"})
    assert response.status_code == 401

def test_get_subscription_status():
    response = client.get("/billing/status", headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "free"
    assert data["user_id"] == USER_ID
