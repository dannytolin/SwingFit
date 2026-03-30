from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.models.user import User
from backend.app.services.auth import hash_password, create_token
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

FREE_TOKEN = None
PRO_TOKEN = None

def setup_module():
    Base.metadata.create_all(engine)
    db = TestSession()
    free_user = User(email="free@test.com", username="free",
        hashed_password=hash_password("pass"), subscription_tier="free")
    pro_user = User(email="pro@test.com", username="pro",
        hashed_password=hash_password("pass"), subscription_tier="pro")
    db.add(free_user)
    db.add(pro_user)
    db.commit()
    global FREE_TOKEN, PRO_TOKEN
    FREE_TOKEN = create_token(user_id=free_user.id)
    PRO_TOKEN = create_token(user_id=pro_user.id)
    db.close()

def teardown_module():
    test_app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)

def test_pro_user_allowed():
    response = test_client.get("/pro-only", headers={"Authorization": f"Bearer {PRO_TOKEN}"})
    assert response.status_code == 200
    assert response.json()["message"] == "welcome pro"

def test_free_user_blocked():
    response = test_client.get("/pro-only", headers={"Authorization": f"Bearer {FREE_TOKEN}"})
    assert response.status_code == 403
    assert "Pro subscription required" in response.json()["detail"]

def test_no_token_blocked():
    response = test_client.get("/pro-only")
    assert response.status_code == 401
