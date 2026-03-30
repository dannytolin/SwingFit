from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database import Base, get_db
from backend.app.models.user import User
from backend.app.routers.auth import get_current_user
from backend.app.services.subscription import require_pro

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine)

test_app = FastAPI()

def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

test_app.dependency_overrides[get_db] = _override_get_db

@test_app.get("/pro-only")
def pro_endpoint(user: User = Depends(require_pro)):
    return {"message": "welcome pro", "user_id": user.id}

test_client = TestClient(test_app)

_free_user_id = None
_pro_user_id = None

def setup_module():
    Base.metadata.create_all(engine)
    db = TestSession()
    free_user = User(email="free@test.com", username="free",
        hashed_password="h", subscription_tier="free")
    pro_user = User(email="pro@test.com", username="pro",
        hashed_password="h", subscription_tier="pro")
    db.add(free_user)
    db.add(pro_user)
    db.commit()
    global _free_user_id, _pro_user_id
    _free_user_id = free_user.id
    _pro_user_id = pro_user.id
    db.close()

def teardown_module():
    test_app.dependency_overrides.pop(get_db, None)
    test_app.dependency_overrides.pop(get_current_user, None)
    Base.metadata.drop_all(engine)

def test_pro_user_allowed():
    def _override_pro(db: Session = Depends(get_db)):
        return db.query(User).filter(User.id == _pro_user_id).first()
    test_app.dependency_overrides[get_current_user] = _override_pro
    response = test_client.get("/pro-only")
    assert response.status_code == 200
    assert response.json()["message"] == "welcome pro"

def test_free_user_blocked():
    def _override_free(db: Session = Depends(get_db)):
        return db.query(User).filter(User.id == _free_user_id).first()
    test_app.dependency_overrides[get_current_user] = _override_free
    response = test_client.get("/pro-only")
    assert response.status_code == 403
    assert "Pro subscription required" in response.json()["detail"]

def test_no_token_blocked():
    test_app.dependency_overrides.pop(get_current_user, None)
    response = test_client.get("/pro-only")
    assert response.status_code == 401
