from unittest.mock import MagicMock, patch
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import Session, sessionmaker
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User
from backend.app.routers.auth import get_current_user

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine)

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
    user = User(email="billing@test.com", username="biller", hashed_password="h")
    db.add(user)
    db.commit()
    global USER_ID
    USER_ID = user.id
    _user_id = user.id
    def _override_current_user(db: Session = Depends(get_db)):
        return db.query(User).filter(User.id == _user_id).first()
    app.dependency_overrides[get_current_user] = _override_current_user
    db.close()

def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    Base.metadata.drop_all(engine)

client = TestClient(app)

@patch("backend.app.routers.billing.stripe")
def test_create_checkout_session(mock_stripe):
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/test")
    response = client.post("/billing/checkout", json={"plan": "monthly"})
    assert response.status_code == 200
    assert response.json()["checkout_url"] == "https://checkout.stripe.com/test"

def test_checkout_requires_auth():
    # Temporarily remove the auth override to test unauthenticated access
    override = app.dependency_overrides.pop(get_current_user, None)
    try:
        response = client.post("/billing/checkout", json={"plan": "monthly"})
        assert response.status_code == 401
    finally:
        if override is not None:
            app.dependency_overrides[get_current_user] = override

def test_get_subscription_status():
    response = client.get("/billing/status")
    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "free"
    assert data["user_id"] == USER_ID
