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

_user_id = None

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
    user = User(email="me@example.com", username="myself", hashed_password="h",
                supabase_uid="test-uid-123", subscription_tier="free")
    db.add(user)
    db.commit()
    db.refresh(user)
    global _user_id
    _user_id = user.id
    db.close()

def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    Base.metadata.drop_all(engine)

client = TestClient(app)

def test_get_me():
    def _override_current_user(db: Session = Depends(get_db)):
        return db.query(User).filter(User.id == _user_id).first()
    app.dependency_overrides[get_current_user] = _override_current_user
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["username"] == "myself"
    assert data["supabase_uid"] == "test-uid-123"
    assert data["subscription_tier"] == "free"
    assert data["id"] is not None

def test_get_me_no_token():
    app.dependency_overrides.pop(get_current_user, None)
    response = client.get("/auth/me")
    assert response.status_code == 401
