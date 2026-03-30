# Phase 5: Auth & Subscriptions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add JWT-based user authentication, Stripe subscription management with free/pro tiers, tier-gating middleware, and a new-club alert system that notifies Pro users when a high-scoring club is added.

**Architecture:** Auth uses password hashing (bcrypt) with JWT tokens. A `subscription_tier` field on the User model tracks free/pro status. Stripe handles payment — a checkout endpoint creates a session, webhooks update the tier. A middleware dependency checks the tier before allowing access to Pro-only endpoints. The alert service runs the fitting engine against all Pro users when a new club is added.

**Tech Stack:** Python, FastAPI, SQLAlchemy, PyJWT, passlib[bcrypt], stripe SDK

---

### Task 1: Password Hashing & JWT Auth Utilities

**Files:**
- Create: `backend/app/services/auth.py`
- Create: `backend/tests/test_auth_service.py`

- [ ] **Step 1: Install dependencies**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
source .venv/Scripts/activate
pip install "passlib[bcrypt]" PyJWT
```

Add to `backend/requirements.txt`:
```
passlib[bcrypt]
PyJWT
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_auth_service.py`:

```python
import pytest

from backend.app.services.auth import hash_password, verify_password, create_token, decode_token


def test_hash_and_verify():
    hashed = hash_password("golf123")
    assert hashed != "golf123"
    assert verify_password("golf123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_token():
    token = create_token(user_id=42)
    payload = decode_token(token)
    assert payload["user_id"] == 42


def test_decode_invalid_token():
    with pytest.raises(ValueError, match="Invalid token"):
        decode_token("garbage.token.here")


def test_token_contains_exp():
    token = create_token(user_id=1)
    payload = decode_token(token)
    assert "exp" in payload
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_auth_service.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Write implementation**

Create `backend/app/services/auth.py`:

```python
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from backend.app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_SECRET_KEY = getattr(settings, "jwt_secret", "swingfit-dev-secret-change-in-prod")
_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as e:
        raise ValueError(f"Invalid token: {e}")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_auth_service.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/auth.py backend/tests/test_auth_service.py backend/requirements.txt
git commit -m "feat: add password hashing and JWT token auth utilities"
```

---

### Task 2: User Registration & Login Endpoints

**Files:**
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_routers_auth.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_routers_auth.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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
        "email": "golfer@example.com",
        "username": "golfer",
        "password": "swing123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "golfer@example.com"
    assert data["id"] is not None
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email():
    client.post("/auth/register", json={
        "email": "dupe@example.com",
        "username": "a",
        "password": "pass123",
    })
    response = client.post("/auth/register", json={
        "email": "dupe@example.com",
        "username": "b",
        "password": "pass456",
    })
    assert response.status_code == 409


def test_login():
    client.post("/auth/register", json={
        "email": "login@example.com",
        "username": "logger",
        "password": "mypassword",
    })
    response = client.post("/auth/login", json={
        "email": "login@example.com",
        "password": "mypassword",
    })
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["email"] == "login@example.com"


def test_login_wrong_password():
    client.post("/auth/register", json={
        "email": "wrong@example.com",
        "username": "wronger",
        "password": "correct",
    })
    response = client.post("/auth/login", json={
        "email": "wrong@example.com",
        "password": "incorrect",
    })
    assert response.status_code == 401


def test_login_nonexistent_user():
    response = client.post("/auth/login", json={
        "email": "noone@example.com",
        "password": "anything",
    })
    assert response.status_code == 401


def test_get_me():
    # Register and login
    client.post("/auth/register", json={
        "email": "me@example.com",
        "username": "myself",
        "password": "secret",
    })
    login_resp = client.post("/auth/login", json={
        "email": "me@example.com",
        "password": "secret",
    })
    token = login_resp.json()["token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_get_me_no_token():
    response = client.get("/auth/me")
    assert response.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_routers_auth.py -v`
Expected: FAIL — routes don't exist

- [ ] **Step 3: Write implementation**

Create `backend/app/routers/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.services.auth import hash_password, verify_password, create_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=req.email,
        username=req.username,
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "username": user.username}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user_id=user.id)
    return {
        "token": token,
        "user": {"id": user.id, "email": user.email, "username": user.username},
    }


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
    }
```

- [ ] **Step 4: Register auth router in main.py**

Read `backend/app/main.py`, then add:

```python
from backend.app.routers.auth import router as auth_router
# ...
app.include_router(auth_router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_routers_auth.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/auth.py backend/app/main.py backend/tests/test_routers_auth.py
git commit -m "feat: add user registration, login, and JWT auth endpoints"
```

---

### Task 3: Subscription Tier on User Model

**Files:**
- Modify: `backend/app/models/user.py`
- Create: `backend/tests/test_subscription_tier.py`

Add `subscription_tier` and `stripe_customer_id` fields to the User model.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_subscription_tier.py`:

```python
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.user import User

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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
    user = User(
        email="pro@test.com",
        username="pro",
        hashed_password="h",
        subscription_tier="pro",
        stripe_customer_id="cus_abc123",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.subscription_tier == "pro"
    assert user.stripe_customer_id == "cus_abc123"
    db.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_subscription_tier.py -v`
Expected: FAIL — `subscription_tier` attribute doesn't exist

- [ ] **Step 3: Add fields to User model**

Edit `backend/app/models/user.py` — add two new columns after `is_active`:

```python
    subscription_tier: Mapped[str] = mapped_column(String, default="free")  # "free" or "pro"
    stripe_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
```

The full file should be:

```python
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    subscription_tier: Mapped[str] = mapped_column(String, default="free")
    stripe_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    sessions = relationship("SwingSession", back_populates="user")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_subscription_tier.py -v`
Expected: Both tests PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Generate Alembic migration**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit/backend"
source ../.venv/Scripts/activate
alembic revision --autogenerate -m "add subscription_tier and stripe_customer_id to users"
alembic upgrade head
```

- [ ] **Step 7: Commit**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
git add backend/app/models/user.py backend/tests/test_subscription_tier.py backend/alembic/
git commit -m "feat: add subscription_tier and stripe_customer_id to User model"
```

---

### Task 4: Subscription Tier Middleware

**Files:**
- Create: `backend/app/services/subscription.py`
- Create: `backend/tests/test_subscription_middleware.py`

A FastAPI dependency that checks if the current user has a Pro subscription.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_subscription_middleware.py`:

```python
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.models.user import User
from backend.app.services.auth import hash_password, create_token
from backend.app.services.subscription import require_pro
from backend.app.routers.auth import get_current_user

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)

# Create a test app with a Pro-only endpoint
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
    free_user = User(
        email="free@test.com", username="free",
        hashed_password=hash_password("pass"), subscription_tier="free",
    )
    pro_user = User(
        email="pro@test.com", username="pro",
        hashed_password=hash_password("pass"), subscription_tier="pro",
    )
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_subscription_middleware.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `backend/app/services/subscription.py`:

```python
from fastapi import Depends, HTTPException

from backend.app.models.user import User
from backend.app.routers.auth import get_current_user

# Free tier limits
FREE_SESSION_LIMIT = 1
FREE_CLUB_TYPES = {"driver"}


def require_pro(user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency that requires a Pro subscription."""
    if user.subscription_tier != "pro":
        raise HTTPException(
            status_code=403,
            detail="Pro subscription required. Upgrade to access this feature.",
        )
    return user


def check_free_tier_limits(user: User, club_type: str) -> None:
    """Check if a free user is within their tier limits.

    Raises HTTPException if they've exceeded limits.
    """
    if user.subscription_tier == "pro":
        return

    if club_type not in FREE_CLUB_TYPES:
        raise HTTPException(
            status_code=403,
            detail=f"Free tier only supports driver recommendations. Upgrade to Pro for {club_type}.",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_subscription_middleware.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/subscription.py backend/tests/test_subscription_middleware.py
git commit -m "feat: add subscription tier middleware with Pro requirement"
```

---

### Task 5: Stripe Checkout & Webhook Endpoints

**Files:**
- Create: `backend/app/routers/billing.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/config.py`
- Create: `backend/tests/test_routers_billing.py`

- [ ] **Step 1: Install stripe SDK**

```bash
pip install stripe
```

Add `stripe` to `backend/requirements.txt`.

- [ ] **Step 2: Add Stripe config to settings**

Edit `backend/app/config.py` — add Stripe fields:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SwingFit"
    database_url: str = "sqlite:///./swingfit.db"
    debug: bool = True
    jwt_secret: str = "swingfit-dev-secret-change-in-prod"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_monthly: str = ""
    stripe_price_yearly: str = ""
    frontend_url: str = "http://localhost:5173"

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 3: Write the failing test**

Create `backend/tests/test_routers_billing.py`:

```python
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User
from backend.app.services.auth import hash_password, create_token

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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
    user = User(
        email="billing@test.com", username="biller",
        hashed_password=hash_password("pass"),
    )
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
    response = client.post(
        "/billing/checkout",
        json={"plan": "monthly"},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 200
    assert response.json()["checkout_url"] == "https://checkout.stripe.com/test"


def test_checkout_requires_auth():
    response = client.post("/billing/checkout", json={"plan": "monthly"})
    assert response.status_code == 401


def test_get_subscription_status():
    response = client.get(
        "/billing/status",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tier"] == "free"
    assert data["user_id"] == USER_ID
```

- [ ] **Step 4: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_routers_billing.py -v`
Expected: FAIL — routes don't exist

- [ ] **Step 5: Write implementation**

Create `backend/app/routers/billing.py`:

```python
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.routers.auth import get_current_user

router = APIRouter(prefix="/billing", tags=["billing"])

stripe.api_key = settings.stripe_secret_key


class CheckoutRequest(BaseModel):
    plan: str  # "monthly" or "yearly"


@router.post("/checkout")
def create_checkout_session(
    req: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    price_id = settings.stripe_price_monthly if req.plan == "monthly" else settings.stripe_price_yearly
    if not price_id:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    # Create or retrieve Stripe customer
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
        user.stripe_customer_id = customer.id
        db.commit()

    checkout = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.frontend_url}/billing?status=success",
        cancel_url=f"{settings.frontend_url}/billing?status=cancelled",
        metadata={"user_id": str(user.id)},
    )
    return {"checkout_url": checkout.url}


@router.get("/status")
def get_subscription_status(user: User = Depends(get_current_user)):
    return {
        "user_id": user.id,
        "tier": user.subscription_tier,
        "stripe_customer_id": user.stripe_customer_id,
    }


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret,
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = int(session["metadata"]["user_id"])
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.subscription_tier = "pro"
            db.commit()

    elif event["type"] == "customer.subscription.deleted":
        customer_id = event["data"]["object"]["customer"]
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_tier = "free"
            db.commit()

    return {"status": "ok"}
```

- [ ] **Step 6: Register billing router in main.py**

Read `backend/app/main.py`, then add:

```python
from backend.app.routers.billing import router as billing_router
# ...
app.include_router(billing_router)
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_routers_billing.py -v`
Expected: All 3 tests PASS

- [ ] **Step 8: Run full test suite**

Run: `python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/routers/billing.py backend/app/main.py backend/app/config.py backend/tests/test_routers_billing.py backend/requirements.txt
git commit -m "feat: add Stripe checkout, webhook, and billing status endpoints"
```

---

### Task 6: New Club Alert Service

**Files:**
- Create: `backend/app/services/alerts.py`
- Create: `backend/tests/test_alerts.py`

When a new club is added to the database, check if it would score in the top 3 for any Pro user's swing profile. Returns a list of alerts (not sending emails yet — just computing who should be notified).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_alerts.py`:

```python
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.user import User
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.models.club_spec import ClubSpec
from backend.app.services.alerts import compute_new_club_alerts


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)


def setup_module():
    Base.metadata.create_all(engine)
    db = TestSession()

    # Pro user with driver shots
    pro = User(email="pro@test.com", username="pro", hashed_password="h", subscription_tier="pro")
    db.add(pro)
    db.commit()

    session = SwingSession(user_id=pro.id, launch_monitor_type="trackman_4", data_source="file_upload")
    db.add(session)
    db.commit()

    for i in range(5):
        db.add(Shot(
            session_id=session.id, club_used="driver",
            ball_speed=150.0 + i, launch_angle=14.0, spin_rate=3100.0,
            carry_distance=248.0 + i, club_speed=105.0, smash_factor=1.42,
            offline_distance=8.0, shot_number=i + 1,
        ))

    # Free user (should not get alerts)
    free = User(email="free@test.com", username="free", hashed_password="h", subscription_tier="free")
    db.add(free)
    db.commit()

    session2 = SwingSession(user_id=free.id, launch_monitor_type="trackman_4", data_source="file_upload")
    db.add(session2)
    db.commit()

    for i in range(5):
        db.add(Shot(
            session_id=session2.id, club_used="driver",
            ball_speed=150.0, launch_angle=14.0, spin_rate=3100.0,
            carry_distance=248.0, club_speed=105.0, smash_factor=1.42,
            offline_distance=8.0, shot_number=i + 1,
        ))

    # Existing clubs
    db.add(ClubSpec(
        brand="Existing", model_name="Club A", model_year=2024, club_type="driver",
        launch_bias="mid", spin_bias="mid", forgiveness_rating=7, workability_rating=5,
        swing_speed_min=85.0, swing_speed_max=120.0,
    ))

    db.commit()
    db.close()


def teardown_module():
    Base.metadata.drop_all(engine)


def test_alerts_for_high_scoring_new_club():
    db = TestSession()

    new_club = ClubSpec(
        brand="NewBrand", model_name="SuperDriver", model_year=2026, club_type="driver",
        launch_bias="low", spin_bias="low", forgiveness_rating=8, workability_rating=7,
        swing_speed_min=90.0, swing_speed_max=120.0,
    )
    db.add(new_club)
    db.commit()

    alerts = compute_new_club_alerts(db, new_club.id)
    db.close()

    # Should alert the Pro user, not the free user
    assert len(alerts) >= 1
    user_ids = [a["user_id"] for a in alerts]
    assert 1 in user_ids  # pro user
    assert 2 not in user_ids  # free user


def test_alerts_include_score():
    db = TestSession()
    # Get the new club we added
    new_club = db.query(ClubSpec).filter(ClubSpec.model_name == "SuperDriver").first()
    alerts = compute_new_club_alerts(db, new_club.id)
    db.close()

    for alert in alerts:
        assert "score" in alert
        assert "club_name" in alert
        assert alert["score"] > 0


def test_no_alerts_for_irrelevant_club():
    db = TestSession()

    # Add an iron — no users have iron shots
    iron = ClubSpec(
        brand="IronCo", model_name="IronX", model_year=2026, club_type="iron",
        launch_bias="mid", spin_bias="mid", forgiveness_rating=6, workability_rating=6,
        swing_speed_min=70.0, swing_speed_max=100.0,
    )
    db.add(iron)
    db.commit()

    alerts = compute_new_club_alerts(db, iron.id)
    db.close()

    assert len(alerts) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_alerts.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `backend/app/services/alerts.py`:

```python
from sqlalchemy.orm import Session

from backend.app.models.club_spec import ClubSpec
from backend.app.models.user import User
from backend.app.services.swing_profile import compute_swing_profile
from backend.app.services.fitting_engine import score_club, rank_recommendations


def compute_new_club_alerts(db: Session, new_club_id: int) -> list[dict]:
    """Check if a new club would score in the top 3 for any Pro user.

    Returns list of alert dicts: [{"user_id", "email", "club_name", "score", "club_type"}]
    """
    new_club = db.query(ClubSpec).filter(ClubSpec.id == new_club_id).first()
    if not new_club:
        return []

    club_type = new_club.club_type
    new_club_dict = {
        "id": new_club.id,
        "brand": new_club.brand,
        "model_name": new_club.model_name,
        "model_year": new_club.model_year,
        "club_type": new_club.club_type,
        "loft": new_club.loft,
        "launch_bias": new_club.launch_bias,
        "spin_bias": new_club.spin_bias,
        "forgiveness_rating": new_club.forgiveness_rating,
        "workability_rating": new_club.workability_rating,
        "swing_speed_min": new_club.swing_speed_min,
        "swing_speed_max": new_club.swing_speed_max,
        "msrp": new_club.msrp,
        "avg_used_price": new_club.avg_used_price,
        "still_in_production": new_club.still_in_production,
    }

    # Get all Pro users
    pro_users = db.query(User).filter(User.subscription_tier == "pro").all()

    alerts = []
    for user in pro_users:
        profile = compute_swing_profile(db, user.id, club_type)
        if profile is None:
            continue

        # Score the new club
        new_score = score_club(profile, new_club_dict)

        # Get all existing clubs of this type and score them
        existing = db.query(ClubSpec).filter(
            ClubSpec.club_type == club_type,
            ClubSpec.id != new_club.id,
        ).all()

        existing_dicts = []
        for c in existing:
            existing_dicts.append({
                "id": c.id, "brand": c.brand, "model_name": c.model_name,
                "model_year": c.model_year, "club_type": c.club_type,
                "launch_bias": c.launch_bias, "spin_bias": c.spin_bias,
                "forgiveness_rating": c.forgiveness_rating,
                "workability_rating": c.workability_rating,
                "swing_speed_min": c.swing_speed_min,
                "swing_speed_max": c.swing_speed_max,
                "msrp": c.msrp, "avg_used_price": c.avg_used_price,
                "still_in_production": c.still_in_production,
            })

        # Check if new club would be in top 3
        all_clubs = existing_dicts + [new_club_dict]
        ranked = rank_recommendations(profile, all_clubs, top_n=3)
        top_3_ids = [r["club"]["id"] for r in ranked]

        if new_club.id in top_3_ids:
            alerts.append({
                "user_id": user.id,
                "email": user.email,
                "club_name": f"{new_club.brand} {new_club.model_name}",
                "club_type": club_type,
                "score": new_score,
            })

    return alerts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_alerts.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/alerts.py backend/tests/test_alerts.py
git commit -m "feat: add new club alert service for Pro users"
```

---

### Task 7: Full Test Suite & Integration Verification

**Files:** None new — verification only.

- [ ] **Step 1: Run all tests**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
source .venv/Scripts/activate
python -m pytest backend/tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: E2E integration test**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
rm -f swingfit.db
python -c "
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import User, ClubSpec, SwingSession, Shot
from backend.app.services.auth import hash_password
from scripts.seed_clubs import seed_clubs_from_csv

Base.metadata.create_all(engine)
client = TestClient(app)

# Register
r = client.post('/auth/register', json={'email': 'danny@swingfit.com', 'username': 'danny', 'password': 'golf123'})
print(f'Register: {r.status_code} | id={r.json()[\"id\"]}')

# Login
r = client.post('/auth/login', json={'email': 'danny@swingfit.com', 'password': 'golf123'})
token = r.json()['token']
print(f'Login: {r.status_code} | token={token[:20]}...')

# Auth check
r = client.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
print(f'Me: {r.json()[\"email\"]} | tier will be free')

# Subscription status
r = client.get('/billing/status', headers={'Authorization': f'Bearer {token}'})
print(f'Billing: tier={r.json()[\"tier\"]}')

# Seed clubs + shots
db = SessionLocal()
seed_clubs_from_csv(db, 'data/club_specs/initial_seed.csv')
session = SwingSession(user_id=1, launch_monitor_type='trackman_4', data_source='file_upload')
db.add(session)
db.commit()
for i in range(10):
    db.add(Shot(session_id=session.id, club_used='driver', ball_speed=149+i, launch_angle=14.0,
        spin_rate=3100.0, carry_distance=248+i, club_speed=105.0, smash_factor=1.42,
        offline_distance=8.0+i, shot_number=i+1))
db.commit()
# Make user Pro for alert test
user = db.query(User).filter(User.id == 1).first()
user.subscription_tier = 'pro'
db.commit()
db.close()

# Recommendations still work
r = client.post('/fitting/recommend', json={'user_id': 1, 'club_type': 'driver'})
print(f'Recs: {len(r.json()[\"recommendations\"])} clubs')

# New club alerts
from backend.app.services.alerts import compute_new_club_alerts
db = SessionLocal()
new_club = ClubSpec(brand='Future', model_name='Driver X', model_year=2027, club_type='driver',
    launch_bias='low', spin_bias='low', forgiveness_rating=9, workability_rating=8,
    swing_speed_min=90.0, swing_speed_max=120.0, msrp=649.99)
db.add(new_club)
db.commit()
alerts = compute_new_club_alerts(db, new_club.id)
print(f'Alerts: {len(alerts)} Pro users notified')
for a in alerts:
    print(f'  user={a[\"email\"]} | {a[\"club_name\"]} scored {a[\"score\"]}/100')
db.close()

print('\\nPhase 5 integration checks passed!')
"
```

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "chore: Phase 5 complete — auth, subscriptions, and new club alerts"
```
