from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.user import User


engine = create_engine("sqlite:///:memory:")
TestSession = sessionmaker(bind=engine)


def setup_module():
    Base.metadata.create_all(engine)


def teardown_module():
    Base.metadata.drop_all(engine)


def test_create_user():
    session = TestSession()
    user = User(
        email="golfer@example.com",
        username="golfer123",
        hashed_password="fakehash",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.id is not None
    assert user.email == "golfer@example.com"
    assert user.username == "golfer123"
    assert isinstance(user.created_at, datetime)
    session.close()


def test_user_email_unique():
    session = TestSession()
    user1 = User(email="dupe@example.com", username="a", hashed_password="h")
    user2 = User(email="dupe@example.com", username="b", hashed_password="h")
    session.add(user1)
    session.commit()
    session.add(user2)
    try:
        session.commit()
        assert False, "Should have raised IntegrityError"
    except Exception:
        session.rollback()
    session.close()
