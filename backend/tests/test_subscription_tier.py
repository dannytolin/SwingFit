from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.user import User

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine)

def setup_module():
    Base.metadata.create_all(engine)

def teardown_module():
    Base.metadata.drop_all(engine)

def test_user_default_tier_is_free():
    db = TestSession()
    user = User(email="free@test.com", username="free", hashed_password="h")
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.subscription_tier == "free"
    assert user.stripe_customer_id is None
    db.close()

def test_user_can_be_pro():
    db = TestSession()
    user = User(email="pro@test.com", username="pro", hashed_password="h",
                subscription_tier="pro", stripe_customer_id="cus_abc123")
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.subscription_tier == "pro"
    assert user.stripe_customer_id == "cus_abc123"
    db.close()
