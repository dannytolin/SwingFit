from datetime import datetime
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models.user import User
from backend.app.models.click import AffiliateClick

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine)

def setup_module():
    Base.metadata.create_all(engine)

def teardown_module():
    Base.metadata.drop_all(engine)

def test_create_click():
    db = TestSession()
    user = User(email="click@test.com", username="clicker", hashed_password="h")
    db.add(user)
    db.commit()
    click = AffiliateClick(
        user_id=user.id,
        club_spec_id=1,
        retailer="global_golf",
        url="https://www.globalgolf.com/search?q=test&tag=abc",
    )
    db.add(click)
    db.commit()
    db.refresh(click)
    assert click.id is not None
    assert click.user_id == user.id
    assert click.retailer == "global_golf"
    assert isinstance(click.clicked_at, datetime)
    db.close()
