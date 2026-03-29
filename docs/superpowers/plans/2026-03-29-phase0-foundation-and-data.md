# Phase 0: Foundation & Data — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the SwingFit backend (FastAPI + SQLite), define all core data models, seed the club spec database, and expose CRUD + query endpoints for clubs, sessions, shots, and user swing profiles.

**Architecture:** FastAPI app with SQLAlchemy ORM over SQLite (migrating to PostgreSQL later). Alembic for schema migrations. Pydantic schemas for request/response validation. The club spec database is the core data asset — seeded from CSV with realistic golf equipment data.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, uvicorn, pytest, SQLite (local dev)

---

### Task 1: Git Init & Project Scaffolding

**Files:**
- Create: `.gitignore`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/parsers/__init__.py`
- Create: `backend/app/services/parsers/trackman/__init__.py`
- Create: `backend/app/utils/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/requirements.txt`
- Create: `data/club_specs/.gitkeep`
- Create: `data/sample_sessions/.gitkeep`
- Create: `scripts/.gitkeep`
- Create: `frontend/.gitkeep`

- [ ] **Step 1: Initialize git repo**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
git init
```

- [ ] **Step 2: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
venv/
env/

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Database
*.db
*.sqlite3

# Node (frontend)
node_modules/
frontend/dist/

# Test / coverage
.pytest_cache/
htmlcov/
.coverage
```

- [ ] **Step 3: Create backend/requirements.txt**

```
fastapi==0.115.12
uvicorn[standard]==0.34.2
sqlalchemy==2.0.40
alembic==1.15.2
pydantic==2.11.3
pydantic-settings==2.9.1
python-dotenv==1.1.0
python-multipart==0.0.20
httpx==0.28.1
pytest==8.4.0
pytest-asyncio==0.26.0
numpy==2.2.6
```

- [ ] **Step 4: Create backend/app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SwingFit"
    database_url: str = "sqlite:///./swingfit.db"
    debug: bool = True

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 5: Create backend/app/main.py with health check**

```python
from fastapi import FastAPI

from backend.app.config import settings

app = FastAPI(title=settings.app_name)


@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.app_name}
```

- [ ] **Step 6: Create all __init__.py files and directory structure**

Create empty `__init__.py` files in:
- `backend/app/__init__.py`
- `backend/app/models/__init__.py`
- `backend/app/routers/__init__.py`
- `backend/app/services/__init__.py`
- `backend/app/services/parsers/__init__.py`
- `backend/app/services/parsers/trackman/__init__.py`
- `backend/app/utils/__init__.py`
- `backend/tests/__init__.py`

Create `.gitkeep` in:
- `data/club_specs/.gitkeep`
- `data/sample_sessions/.gitkeep`
- `scripts/.gitkeep`
- `frontend/.gitkeep`

- [ ] **Step 7: Create .env file**

```
DATABASE_URL=sqlite:///./swingfit.db
DEBUG=true
```

- [ ] **Step 8: Install dependencies and verify health check**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
python -m venv .venv
source .venv/Scripts/activate  # Windows Git Bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
sleep 2
curl http://localhost:8000/
# Expected: {"status":"ok","app":"SwingFit"}
kill %1
```

- [ ] **Step 9: Commit**

```bash
git add .gitignore backend/ data/ scripts/ frontend/.gitkeep .env
git commit -m "feat: scaffold SwingFit project structure with FastAPI"
```

---

### Task 2: Database Setup & Base Model

**Files:**
- Create: `backend/app/database.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Write test for database connection**

Create `backend/tests/test_database.py`:

```python
from sqlalchemy import text

from backend.app.database import engine


def test_database_connection():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
source .venv/Scripts/activate
python -m pytest backend/tests/test_database.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.database'`

- [ ] **Step 3: Create backend/app/database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite only
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest backend/tests/test_database.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/database.py backend/tests/test_database.py
git commit -m "feat: add database engine and session factory"
```

---

### Task 3: User Model

**Files:**
- Create: `backend/app/models/user.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_models_user.py`

- [ ] **Step 1: Write test for User model**

Create `backend/tests/test_models_user.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest backend/tests/test_models_user.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.app.models.user'`

- [ ] **Step 3: Create backend/app/models/user.py**

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
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    sessions = relationship("SwingSession", back_populates="user")
```

- [ ] **Step 4: Update models __init__.py**

Update `backend/app/models/__init__.py`:

```python
from backend.app.models.user import User

__all__ = ["User"]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest backend/tests/test_models_user.py -v
```

Expected: Both tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/user.py backend/app/models/__init__.py backend/tests/test_models_user.py
git commit -m "feat: add User model with email uniqueness"
```

---

### Task 4: ClubSpec Model

**Files:**
- Create: `backend/app/models/club_spec.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_models_club_spec.py`

- [ ] **Step 1: Write test for ClubSpec model**

Create `backend/tests/test_models_club_spec.py`:

```python
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.club_spec import ClubSpec


engine = create_engine("sqlite:///:memory:")
TestSession = sessionmaker(bind=engine)


def setup_module():
    Base.metadata.create_all(engine)


def teardown_module():
    Base.metadata.drop_all(engine)


def test_create_driver_spec():
    session = TestSession()
    club = ClubSpec(
        brand="TaylorMade",
        model_name="Qi10 Max",
        model_year=2025,
        club_type="driver",
        loft=10.5,
        lie_angle=56.0,
        shaft_options=json.dumps(["Fujikura Speeder NX", "Project X HZRDUS"]),
        head_weight=200.0,
        adjustable=True,
        loft_range_min=8.5,
        loft_range_max=12.5,
        launch_bias="mid",
        spin_bias="low",
        forgiveness_rating=9,
        workability_rating=4,
        swing_speed_min=85.0,
        swing_speed_max=115.0,
        msrp=599.99,
        avg_used_price=420.0,
        still_in_production=True,
    )
    session.add(club)
    session.commit()
    session.refresh(club)

    assert club.id is not None
    assert club.brand == "TaylorMade"
    assert club.club_type == "driver"
    assert club.adjustable is True
    assert club.swing_speed_min == 85.0
    session.close()


def test_create_iron_spec():
    session = TestSession()
    club = ClubSpec(
        brand="Titleist",
        model_name="T150",
        model_year=2024,
        club_type="iron",
        loft=33.0,
        lie_angle=62.5,
        shaft_options=json.dumps(["True Temper AMT Black"]),
        head_weight=265.0,
        adjustable=False,
        launch_bias="mid",
        spin_bias="mid",
        forgiveness_rating=5,
        workability_rating=8,
        swing_speed_min=80.0,
        swing_speed_max=110.0,
        msrp=1399.99,
        still_in_production=True,
    )
    session.add(club)
    session.commit()
    session.refresh(club)

    assert club.id is not None
    assert club.club_type == "iron"
    assert club.adjustable is False
    assert club.loft_range_min is None
    session.close()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest backend/tests/test_models_club_spec.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create backend/app/models/club_spec.py**

```python
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class ClubSpec(Base):
    __tablename__ = "club_specs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identity
    brand: Mapped[str] = mapped_column(String, nullable=False)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_year: Mapped[int] = mapped_column(Integer, nullable=False)
    club_type: Mapped[str] = mapped_column(String, nullable=False)  # driver, iron, hybrid, fairway, wedge, putter

    # Specifications
    loft: Mapped[float | None] = mapped_column(Float, nullable=True)
    lie_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    shaft_options: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    head_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    adjustable: Mapped[bool] = mapped_column(Boolean, default=False)
    loft_range_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    loft_range_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Performance profile
    launch_bias: Mapped[str | None] = mapped_column(String, nullable=True)  # low, mid, high
    spin_bias: Mapped[str | None] = mapped_column(String, nullable=True)  # low, mid, high
    forgiveness_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-10
    workability_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-10

    # Swing speed suitability
    swing_speed_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    swing_speed_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Market data
    msrp: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_used_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    affiliate_url_template: Mapped[str | None] = mapped_column(String, nullable=True)

    # Metadata
    still_in_production: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 4: Update models __init__.py**

Update `backend/app/models/__init__.py`:

```python
from backend.app.models.user import User
from backend.app.models.club_spec import ClubSpec

__all__ = ["User", "ClubSpec"]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest backend/tests/test_models_club_spec.py -v
```

Expected: Both tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/club_spec.py backend/app/models/__init__.py backend/tests/test_models_club_spec.py
git commit -m "feat: add ClubSpec model for club specification database"
```

---

### Task 5: SwingSession & Shot Models

**Files:**
- Create: `backend/app/models/session.py`
- Create: `backend/app/models/shot.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/test_models_session_shot.py`

- [ ] **Step 1: Write test for SwingSession and Shot models**

Create `backend/tests/test_models_session_shot.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.user import User
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot


engine = create_engine("sqlite:///:memory:")
TestSession = sessionmaker(bind=engine)


def setup_module():
    Base.metadata.create_all(engine)


def teardown_module():
    Base.metadata.drop_all(engine)


def test_create_session_with_shots():
    db = TestSession()

    user = User(email="test@example.com", username="tester", hashed_password="h")
    db.add(user)
    db.commit()
    db.refresh(user)

    swing_session = SwingSession(
        user_id=user.id,
        session_date=datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc),
        launch_monitor_type="trackman_4",
        location="indoor",
        data_source="file_upload",
        source_file_name="session_export.csv",
    )
    db.add(swing_session)
    db.commit()
    db.refresh(swing_session)

    assert swing_session.id is not None
    assert swing_session.user_id == user.id

    shot = Shot(
        session_id=swing_session.id,
        club_used="driver",
        ball_speed=149.8,
        launch_angle=12.3,
        spin_rate=2845.0,
        carry_distance=248.0,
        total_distance=271.0,
        club_speed=105.2,
        smash_factor=1.42,
        attack_angle=-1.2,
        club_path=2.1,
        face_angle=0.8,
        face_to_path=-1.3,
        spin_axis=3.2,
        offline_distance=8.0,
        apex_height=98.0,
        landing_angle=38.5,
        shot_number=1,
    )
    db.add(shot)
    db.commit()
    db.refresh(shot)

    assert shot.id is not None
    assert shot.session_id == swing_session.id
    assert shot.ball_speed == 149.8
    assert shot.is_valid is True
    db.close()


def test_session_shots_relationship():
    db = TestSession()

    user = User(email="rel@example.com", username="rel", hashed_password="h")
    db.add(user)
    db.commit()

    swing_session = SwingSession(
        user_id=user.id,
        session_date=datetime(2025, 6, 15, tzinfo=timezone.utc),
        launch_monitor_type="garmin_r10",
        data_source="file_upload",
    )
    db.add(swing_session)
    db.commit()

    for i in range(3):
        shot = Shot(
            session_id=swing_session.id,
            club_used="7-iron",
            ball_speed=120.0 + i,
            launch_angle=18.0,
            spin_rate=6400.0,
            carry_distance=165.0 + i,
            shot_number=i + 1,
        )
        db.add(shot)
    db.commit()

    db.refresh(swing_session)
    assert len(swing_session.shots) == 3
    assert swing_session.shots[0].club_used == "7-iron"
    db.close()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest backend/tests/test_models_session_shot.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create backend/app/models/session.py**

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class SwingSession(Base):
    __tablename__ = "swing_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Session metadata
    session_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    launch_monitor_type: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)

    # Trackman-specific metadata
    trackman_session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    trackman_facility_name: Mapped[str | None] = mapped_column(String, nullable=True)
    trackman_bay_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # Data quality
    data_source: Mapped[str] = mapped_column(String, nullable=False)

    # File reference
    source_file_name: Mapped[str | None] = mapped_column(String, nullable=True)
    source_file_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="sessions")
    shots = relationship("Shot", back_populates="session", order_by="Shot.shot_number")
```

- [ ] **Step 4: Create backend/app/models/shot.py**

```python
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("swing_sessions.id"), nullable=False)

    # Club used
    club_used: Mapped[str] = mapped_column(String, nullable=False)
    club_brand: Mapped[str | None] = mapped_column(String, nullable=True)
    club_model: Mapped[str | None] = mapped_column(String, nullable=True)

    # Ball data
    ball_speed: Mapped[float] = mapped_column(Float, nullable=False)
    launch_angle: Mapped[float] = mapped_column(Float, nullable=False)
    spin_rate: Mapped[float] = mapped_column(Float, nullable=False)
    spin_axis: Mapped[float | None] = mapped_column(Float, nullable=True)
    carry_distance: Mapped[float] = mapped_column(Float, nullable=False)
    total_distance: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Club data
    club_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    smash_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    attack_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    club_path: Mapped[float | None] = mapped_column(Float, nullable=True)
    face_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    face_to_path: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Dispersion
    offline_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    apex_height: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Trackman-specific extended data
    landing_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    dynamic_loft: Mapped[float | None] = mapped_column(Float, nullable=True)
    spin_loft: Mapped[float | None] = mapped_column(Float, nullable=True)
    hang_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_data_distance: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Quality
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    shot_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    session = relationship("SwingSession", back_populates="shots")
```

- [ ] **Step 5: Update models __init__.py**

Update `backend/app/models/__init__.py`:

```python
from backend.app.models.user import User
from backend.app.models.club_spec import ClubSpec
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot

__all__ = ["User", "ClubSpec", "SwingSession", "Shot"]
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
python -m pytest backend/tests/test_models_session_shot.py -v
```

Expected: Both tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/session.py backend/app/models/shot.py backend/app/models/__init__.py backend/tests/test_models_session_shot.py
git commit -m "feat: add SwingSession and Shot models with relationships"
```

---

### Task 6: Alembic Setup & Initial Migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/` (auto-generated migration)

- [ ] **Step 1: Initialize Alembic**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
source .venv/Scripts/activate
cd backend
alembic init alembic
```

- [ ] **Step 2: Configure alembic.ini**

Edit `backend/alembic.ini` — set the `sqlalchemy.url` line:

```ini
sqlalchemy.url = sqlite:///./swingfit.db
```

- [ ] **Step 3: Configure alembic/env.py to import models**

Replace the contents of `backend/alembic/env.py`:

```python
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.database import Base
from backend.app.models import User, ClubSpec, SwingSession, Shot  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Generate initial migration**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit/backend"
alembic revision --autogenerate -m "initial schema: users, club_specs, swing_sessions, shots"
```

Expected: A new file in `backend/alembic/versions/` with the migration

- [ ] **Step 5: Run the migration**

```bash
alembic upgrade head
```

Expected: Tables created in `backend/swingfit.db`

- [ ] **Step 6: Verify tables exist**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
python -c "
from sqlalchemy import inspect
from backend.app.database import engine
inspector = inspect(engine)
tables = inspector.get_table_names()
print('Tables:', tables)
assert 'users' in tables
assert 'club_specs' in tables
assert 'swing_sessions' in tables
assert 'shots' in tables
print('All tables created successfully')
"
```

- [ ] **Step 7: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: set up Alembic with initial migration for all models"
```

---

### Task 7: Pydantic Schemas for API

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/club_spec.py`
- Create: `backend/app/schemas/session.py`
- Create: `backend/app/schemas/shot.py`
- Create: `backend/tests/test_schemas.py`

- [ ] **Step 1: Write test for schemas**

Create `backend/tests/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from backend.app.schemas.club_spec import ClubSpecCreate, ClubSpecRead, ClubSpecSearch
from backend.app.schemas.session import SwingSessionCreate, SwingSessionRead
from backend.app.schemas.shot import ShotCreate, ShotRead


def test_club_spec_create_valid():
    data = ClubSpecCreate(
        brand="TaylorMade",
        model_name="Qi10",
        model_year=2025,
        club_type="driver",
        loft=10.5,
        swing_speed_min=85.0,
        swing_speed_max=115.0,
        launch_bias="mid",
        spin_bias="low",
        forgiveness_rating=8,
        workability_rating=5,
        msrp=599.99,
        still_in_production=True,
    )
    assert data.brand == "TaylorMade"
    assert data.club_type == "driver"


def test_club_spec_create_invalid_club_type():
    with pytest.raises(ValidationError):
        ClubSpecCreate(
            brand="TaylorMade",
            model_name="Qi10",
            model_year=2025,
            club_type="bat",  # invalid
        )


def test_club_spec_search():
    search = ClubSpecSearch(brand="Titleist", club_type="driver")
    assert search.brand == "Titleist"
    assert search.swing_speed is None


def test_shot_create_valid():
    shot = ShotCreate(
        club_used="driver",
        ball_speed=149.8,
        launch_angle=12.3,
        spin_rate=2845.0,
        carry_distance=248.0,
        shot_number=1,
    )
    assert shot.ball_speed == 149.8
    assert shot.is_valid is True


def test_session_create_valid():
    session = SwingSessionCreate(
        launch_monitor_type="trackman_4",
        data_source="file_upload",
        session_date="2025-06-15T10:00:00Z",
    )
    assert session.launch_monitor_type == "trackman_4"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest backend/tests/test_schemas.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create backend/app/schemas/club_spec.py**

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CLUB_TYPES = Literal["driver", "iron", "hybrid", "fairway", "wedge", "putter"]
BIAS_OPTIONS = Literal["low", "mid", "high"]


class ClubSpecCreate(BaseModel):
    brand: str
    model_name: str
    model_year: int
    club_type: CLUB_TYPES
    loft: float | None = None
    lie_angle: float | None = None
    shaft_options: str | None = None
    head_weight: float | None = None
    adjustable: bool = False
    loft_range_min: float | None = None
    loft_range_max: float | None = None
    launch_bias: BIAS_OPTIONS | None = None
    spin_bias: BIAS_OPTIONS | None = None
    forgiveness_rating: int | None = Field(None, ge=1, le=10)
    workability_rating: int | None = Field(None, ge=1, le=10)
    swing_speed_min: float | None = None
    swing_speed_max: float | None = None
    msrp: float | None = None
    avg_used_price: float | None = None
    affiliate_url_template: str | None = None
    still_in_production: bool = True


class ClubSpecRead(ClubSpecCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClubSpecSearch(BaseModel):
    brand: str | None = None
    club_type: CLUB_TYPES | None = None
    model_year: int | None = None
    swing_speed: float | None = None
    launch_bias: BIAS_OPTIONS | None = None
    spin_bias: BIAS_OPTIONS | None = None
```

- [ ] **Step 4: Create backend/app/schemas/session.py**

```python
from datetime import datetime

from pydantic import BaseModel


class SwingSessionCreate(BaseModel):
    session_date: datetime | None = None
    launch_monitor_type: str
    location: str | None = None
    trackman_session_id: str | None = None
    trackman_facility_name: str | None = None
    trackman_bay_id: str | None = None
    data_source: str
    source_file_name: str | None = None
    source_file_hash: str | None = None


class SwingSessionRead(SwingSessionCreate):
    id: int
    user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Create backend/app/schemas/shot.py**

```python
from pydantic import BaseModel


class ShotCreate(BaseModel):
    club_used: str
    club_brand: str | None = None
    club_model: str | None = None
    ball_speed: float
    launch_angle: float
    spin_rate: float
    spin_axis: float | None = None
    carry_distance: float
    total_distance: float | None = None
    club_speed: float | None = None
    smash_factor: float | None = None
    attack_angle: float | None = None
    club_path: float | None = None
    face_angle: float | None = None
    face_to_path: float | None = None
    offline_distance: float | None = None
    apex_height: float | None = None
    landing_angle: float | None = None
    dynamic_loft: float | None = None
    spin_loft: float | None = None
    hang_time: float | None = None
    last_data_distance: float | None = None
    is_valid: bool = True
    shot_number: int


class ShotRead(ShotCreate):
    id: int
    session_id: int

    model_config = {"from_attributes": True}
```

- [ ] **Step 6: Create backend/app/schemas/__init__.py**

```python
from backend.app.schemas.club_spec import ClubSpecCreate, ClubSpecRead, ClubSpecSearch
from backend.app.schemas.session import SwingSessionCreate, SwingSessionRead
from backend.app.schemas.shot import ShotCreate, ShotRead

__all__ = [
    "ClubSpecCreate", "ClubSpecRead", "ClubSpecSearch",
    "SwingSessionCreate", "SwingSessionRead",
    "ShotCreate", "ShotRead",
]
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
python -m pytest backend/tests/test_schemas.py -v
```

Expected: All 5 tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/ backend/tests/test_schemas.py
git commit -m "feat: add Pydantic schemas for ClubSpec, SwingSession, and Shot"
```

---

### Task 8: Club CRUD Endpoints

**Files:**
- Create: `backend/app/routers/clubs.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_routers_clubs.py`

- [ ] **Step 1: Write tests for club endpoints**

Create `backend/tests/test_routers_clubs.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app

engine = create_engine("sqlite:///:memory:")
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_module():
    Base.metadata.create_all(engine)


def teardown_module():
    Base.metadata.drop_all(engine)


DRIVER_DATA = {
    "brand": "TaylorMade",
    "model_name": "Qi10 Max",
    "model_year": 2025,
    "club_type": "driver",
    "loft": 10.5,
    "launch_bias": "mid",
    "spin_bias": "low",
    "forgiveness_rating": 9,
    "workability_rating": 4,
    "swing_speed_min": 85.0,
    "swing_speed_max": 115.0,
    "msrp": 599.99,
    "still_in_production": True,
}


def test_create_club():
    response = client.post("/clubs", json=DRIVER_DATA)
    assert response.status_code == 201
    data = response.json()
    assert data["brand"] == "TaylorMade"
    assert data["id"] is not None


def test_get_club_by_id():
    # Create first
    create_resp = client.post("/clubs", json={
        **DRIVER_DATA,
        "model_name": "Stealth 2",
        "model_year": 2023,
    })
    club_id = create_resp.json()["id"]

    response = client.get(f"/clubs/{club_id}")
    assert response.status_code == 200
    assert response.json()["model_name"] == "Stealth 2"


def test_get_club_not_found():
    response = client.get("/clubs/9999")
    assert response.status_code == 404


def test_list_clubs():
    response = client.get("/clubs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_search_clubs_by_brand():
    response = client.get("/clubs/search", params={"brand": "TaylorMade"})
    assert response.status_code == 200
    data = response.json()
    assert all(c["brand"] == "TaylorMade" for c in data)


def test_search_clubs_by_type():
    response = client.get("/clubs/search", params={"club_type": "driver"})
    assert response.status_code == 200
    data = response.json()
    assert all(c["club_type"] == "driver" for c in data)


def test_search_clubs_by_swing_speed():
    response = client.get("/clubs/search", params={"swing_speed": 100.0})
    assert response.status_code == 200
    data = response.json()
    for club in data:
        if club["swing_speed_min"] and club["swing_speed_max"]:
            assert club["swing_speed_min"] <= 100.0 <= club["swing_speed_max"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest backend/tests/test_routers_clubs.py -v
```

Expected: FAIL — router not registered, 404s

- [ ] **Step 3: Create backend/app/routers/clubs.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.club_spec import ClubSpec
from backend.app.schemas.club_spec import ClubSpecCreate, ClubSpecRead, ClubSpecSearch

router = APIRouter(prefix="/clubs", tags=["clubs"])


@router.post("", response_model=ClubSpecRead, status_code=201)
def create_club(club: ClubSpecCreate, db: Session = Depends(get_db)):
    db_club = ClubSpec(**club.model_dump())
    db.add(db_club)
    db.commit()
    db.refresh(db_club)
    return db_club


@router.get("", response_model=list[ClubSpecRead])
def list_clubs(db: Session = Depends(get_db)):
    return db.query(ClubSpec).all()


@router.get("/search", response_model=list[ClubSpecRead])
def search_clubs(
    brand: str | None = None,
    club_type: str | None = None,
    model_year: int | None = None,
    swing_speed: float | None = None,
    launch_bias: str | None = None,
    spin_bias: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(ClubSpec)
    if brand:
        query = query.filter(ClubSpec.brand == brand)
    if club_type:
        query = query.filter(ClubSpec.club_type == club_type)
    if model_year:
        query = query.filter(ClubSpec.model_year == model_year)
    if swing_speed is not None:
        query = query.filter(
            ClubSpec.swing_speed_min <= swing_speed,
            ClubSpec.swing_speed_max >= swing_speed,
        )
    if launch_bias:
        query = query.filter(ClubSpec.launch_bias == launch_bias)
    if spin_bias:
        query = query.filter(ClubSpec.spin_bias == spin_bias)
    return query.all()


@router.get("/{club_id}", response_model=ClubSpecRead)
def get_club(club_id: int, db: Session = Depends(get_db)):
    club = db.query(ClubSpec).filter(ClubSpec.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return club
```

- [ ] **Step 4: Register router in main.py**

Replace `backend/app/main.py`:

```python
from fastapi import FastAPI

from backend.app.config import settings
from backend.app.routers.clubs import router as clubs_router

app = FastAPI(title=settings.app_name)
app.include_router(clubs_router)


@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.app_name}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest backend/tests/test_routers_clubs.py -v
```

Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/clubs.py backend/app/main.py backend/tests/test_routers_clubs.py
git commit -m "feat: add club CRUD and search endpoints"
```

---

### Task 9: Session & Shot Endpoints

**Files:**
- Create: `backend/app/routers/sessions.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_routers_sessions.py`

- [ ] **Step 1: Write tests for session and shot endpoints**

Create `backend/tests/test_routers_sessions.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User

engine = create_engine("sqlite:///:memory:")
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

USER_ID = None


def setup_module():
    Base.metadata.create_all(engine)
    # Create a test user
    db = TestSession()
    user = User(email="session_test@example.com", username="st", hashed_password="h")
    db.add(user)
    db.commit()
    db.refresh(user)
    global USER_ID
    USER_ID = user.id
    db.close()


def teardown_module():
    Base.metadata.drop_all(engine)


def test_create_session():
    response = client.post(f"/users/{USER_ID}/sessions", json={
        "launch_monitor_type": "trackman_4",
        "data_source": "file_upload",
        "session_date": "2025-06-15T10:00:00Z",
        "location": "indoor",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == USER_ID
    assert data["launch_monitor_type"] == "trackman_4"


def test_add_shots_to_session():
    # Create session first
    session_resp = client.post(f"/users/{USER_ID}/sessions", json={
        "launch_monitor_type": "garmin_r10",
        "data_source": "file_upload",
    })
    session_id = session_resp.json()["id"]

    shots = [
        {
            "club_used": "driver",
            "ball_speed": 149.8,
            "launch_angle": 12.3,
            "spin_rate": 2845.0,
            "carry_distance": 248.0,
            "total_distance": 271.0,
            "club_speed": 105.2,
            "shot_number": 1,
        },
        {
            "club_used": "driver",
            "ball_speed": 151.0,
            "launch_angle": 11.8,
            "spin_rate": 2650.0,
            "carry_distance": 255.0,
            "total_distance": 278.0,
            "club_speed": 107.1,
            "shot_number": 2,
        },
    ]
    response = client.post(f"/sessions/{session_id}/shots", json=shots)
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2
    assert data[0]["ball_speed"] == 149.8


def test_get_session_summary():
    # Create session with shots
    session_resp = client.post(f"/users/{USER_ID}/sessions", json={
        "launch_monitor_type": "trackman_4",
        "data_source": "file_upload",
    })
    session_id = session_resp.json()["id"]

    shots = [
        {"club_used": "driver", "ball_speed": 150.0, "launch_angle": 12.0, "spin_rate": 2800.0, "carry_distance": 250.0, "club_speed": 105.0, "shot_number": 1},
        {"club_used": "driver", "ball_speed": 148.0, "launch_angle": 13.0, "spin_rate": 2900.0, "carry_distance": 245.0, "club_speed": 103.0, "shot_number": 2},
        {"club_used": "7-iron", "ball_speed": 120.0, "launch_angle": 18.0, "spin_rate": 6400.0, "carry_distance": 165.0, "club_speed": 82.0, "shot_number": 3},
    ]
    client.post(f"/sessions/{session_id}/shots", json=shots)

    response = client.get(f"/sessions/{session_id}/summary")
    assert response.status_code == 200
    data = response.json()

    # Should have summaries grouped by club
    assert "driver" in data
    assert "7-iron" in data
    assert data["driver"]["avg_ball_speed"] == 149.0
    assert data["driver"]["avg_carry"] == 247.5
    assert data["driver"]["shot_count"] == 2
    assert data["7-iron"]["shot_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest backend/tests/test_routers_sessions.py -v
```

Expected: FAIL — routes don't exist

- [ ] **Step 3: Create backend/app/routers/sessions.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.models.user import User
from backend.app.schemas.session import SwingSessionCreate, SwingSessionRead
from backend.app.schemas.shot import ShotCreate, ShotRead

router = APIRouter(tags=["sessions"])


@router.post("/users/{user_id}/sessions", response_model=SwingSessionRead, status_code=201)
def create_session(user_id: int, session_data: SwingSessionCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    swing_session = SwingSession(user_id=user_id, **session_data.model_dump())
    db.add(swing_session)
    db.commit()
    db.refresh(swing_session)
    return swing_session


@router.post("/sessions/{session_id}/shots", response_model=list[ShotRead], status_code=201)
def add_shots(session_id: int, shots: list[ShotCreate], db: Session = Depends(get_db)):
    swing_session = db.query(SwingSession).filter(SwingSession.id == session_id).first()
    if not swing_session:
        raise HTTPException(status_code=404, detail="Session not found")
    db_shots = []
    for shot_data in shots:
        shot = Shot(session_id=session_id, **shot_data.model_dump())
        db.add(shot)
        db_shots.append(shot)
    db.commit()
    for shot in db_shots:
        db.refresh(shot)
    return db_shots


@router.get("/sessions/{session_id}/summary")
def get_session_summary(session_id: int, db: Session = Depends(get_db)):
    swing_session = db.query(SwingSession).filter(SwingSession.id == session_id).first()
    if not swing_session:
        raise HTTPException(status_code=404, detail="Session not found")

    shots = db.query(Shot).filter(
        Shot.session_id == session_id,
        Shot.is_valid == True,
    ).all()

    if not shots:
        return {}

    # Group by club
    clubs: dict[str, list[Shot]] = {}
    for shot in shots:
        clubs.setdefault(shot.club_used, []).append(shot)

    summary = {}
    for club_name, club_shots in clubs.items():
        n = len(club_shots)

        def avg(attr: str) -> float | None:
            vals = [getattr(s, attr) for s in club_shots if getattr(s, attr) is not None]
            return round(sum(vals) / len(vals), 1) if vals else None

        summary[club_name] = {
            "shot_count": n,
            "avg_ball_speed": avg("ball_speed"),
            "avg_launch_angle": avg("launch_angle"),
            "avg_spin_rate": avg("spin_rate"),
            "avg_carry": avg("carry_distance"),
            "avg_total": avg("total_distance"),
            "avg_club_speed": avg("club_speed"),
            "avg_smash_factor": avg("smash_factor"),
            "avg_attack_angle": avg("attack_angle"),
            "avg_club_path": avg("club_path"),
            "avg_face_angle": avg("face_angle"),
            "avg_offline": avg("offline_distance"),
        }

    return summary
```

- [ ] **Step 4: Register sessions router in main.py**

Replace `backend/app/main.py`:

```python
from fastapi import FastAPI

from backend.app.config import settings
from backend.app.routers.clubs import router as clubs_router
from backend.app.routers.sessions import router as sessions_router

app = FastAPI(title=settings.app_name)
app.include_router(clubs_router)
app.include_router(sessions_router)


@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.app_name}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest backend/tests/test_routers_sessions.py -v
```

Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/sessions.py backend/app/main.py backend/tests/test_routers_sessions.py
git commit -m "feat: add session creation, shot ingestion, and session summary endpoints"
```

---

### Task 10: Club Spec Seed Data

**Files:**
- Create: `data/club_specs/initial_seed.csv`
- Create: `scripts/seed_clubs.py`
- Create: `backend/tests/test_seed_clubs.py`

- [ ] **Step 1: Create data/club_specs/initial_seed.csv**

This CSV contains 20 realistic club specs: 10 drivers, 5 iron sets, 5 wedges.

```csv
brand,model_name,model_year,club_type,loft,lie_angle,shaft_options,head_weight,adjustable,loft_range_min,loft_range_max,launch_bias,spin_bias,forgiveness_rating,workability_rating,swing_speed_min,swing_speed_max,msrp,avg_used_price,still_in_production
TaylorMade,Qi10 Max,2025,driver,10.5,56.0,"[""Fujikura Speeder NX"",""Project X HZRDUS""]",200,True,8.0,12.5,high,low,9,3,80,115,599.99,450.00,True
TaylorMade,Qi10,2025,driver,10.5,56.0,"[""Fujikura Speeder NX""]",198,True,8.0,12.5,mid,low,7,6,85,120,599.99,440.00,True
Callaway,Paradym Ai Smoke Max,2024,driver,10.5,56.0,"[""Project X HZRDUS Smoke""]",200,True,8.0,12.5,high,mid,9,3,75,115,599.99,380.00,True
Callaway,Paradym Ai Smoke,2024,driver,9.0,56.0,"[""Project X HZRDUS Smoke""]",198,True,7.0,11.0,mid,low,6,7,90,125,599.99,370.00,True
Titleist,TSR3,2023,driver,9.0,58.5,"[""KURO KAGE Black"",""Tensei AV Blue""]",200,True,8.0,11.0,low,low,5,9,90,125,599.99,320.00,False
Titleist,TSR2,2023,driver,10.0,58.5,"[""KURO KAGE Black""]",200,True,8.0,12.0,mid,mid,8,5,80,118,599.99,310.00,False
Ping,G430 Max,2023,driver,10.5,57.0,"[""Alta CB Black"",""Ping Tour 2.0""]",203,True,8.0,12.5,mid,mid,9,4,75,115,549.99,300.00,True
Ping,G430 LST,2023,driver,9.0,57.0,"[""Ping Tour 2.0""]",198,True,7.5,10.5,low,low,5,8,95,130,549.99,310.00,True
Cobra,Darkspeed Max,2024,driver,10.5,56.5,"[""Arccos Caddie Smart Grip""]",200,True,9.0,12.0,high,mid,9,3,75,110,499.99,340.00,True
Cobra,Darkspeed X,2024,driver,9.0,56.5,"[""MCA Kai'li White""]",196,True,7.5,10.5,low,low,5,8,95,130,499.99,330.00,True
TaylorMade,P790,2024,iron,33.0,62.5,"[""True Temper Dynamic Gold""]",265,False,,,,mid,mid,6,7,80,115,1399.99,900.00,True
Callaway,Apex Pro 24,2024,iron,30.5,62.0,"[""True Temper Elevate""]",263,False,,,,mid,mid,5,8,85,120,1499.99,950.00,True
Titleist,T150,2023,iron,33.0,62.5,"[""True Temper AMT Black""]",265,False,,,,mid,mid,5,8,80,115,1399.99,850.00,True
Ping,i230,2023,iron,33.0,62.5,"[""Nippon Modus3 Tour""]",265,False,,,,mid,mid,6,7,80,115,1349.99,820.00,True
Cobra,King Forged Tec,2024,iron,30.0,62.0,"[""KBS $-Taper""]",260,False,,,,high,mid,7,5,75,110,1199.99,750.00,True
Titleist,Vokey SM10,2024,wedge,56.0,64.0,"[""True Temper Dynamic Gold""]",300,False,,,,mid,high,4,10,70,130,179.99,130.00,True
Callaway,Jaws Raw,2023,wedge,56.0,64.0,"[""True Temper Dynamic Gold""]",300,False,,,,mid,high,5,9,70,130,179.99,120.00,True
TaylorMade,Hi-Toe 3,2024,wedge,58.0,64.0,"[""KBS Hi-Rev 2.0""]",298,False,,,,high,high,6,8,70,125,179.99,125.00,True
Cleveland,RTX6 ZipCore,2024,wedge,56.0,64.0,"[""True Temper Dynamic Gold""]",300,False,,,,mid,high,5,9,70,130,159.99,110.00,True
Ping,Glide 4.0,2023,wedge,56.0,64.0,"[""Nippon Modus3 Tour""]",298,False,,,,mid,mid,6,8,70,125,179.99,115.00,True
```

- [ ] **Step 2: Write test for seed script**

Create `backend/tests/test_seed_clubs.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.club_spec import ClubSpec
from scripts.seed_clubs import seed_clubs_from_csv

engine = create_engine("sqlite:///:memory:")
TestSession = sessionmaker(bind=engine)


def setup_module():
    Base.metadata.create_all(engine)


def teardown_module():
    Base.metadata.drop_all(engine)


def test_seed_clubs_from_csv():
    db = TestSession()
    count = seed_clubs_from_csv(db, "data/club_specs/initial_seed.csv")
    assert count == 20
    db.close()


def test_seed_clubs_correct_data():
    db = TestSession()
    qi10 = db.query(ClubSpec).filter(
        ClubSpec.brand == "TaylorMade",
        ClubSpec.model_name == "Qi10 Max",
    ).first()
    assert qi10 is not None
    assert qi10.club_type == "driver"
    assert qi10.loft == 10.5
    assert qi10.adjustable is True
    assert qi10.swing_speed_min == 80.0

    drivers = db.query(ClubSpec).filter(ClubSpec.club_type == "driver").all()
    assert len(drivers) == 10

    irons = db.query(ClubSpec).filter(ClubSpec.club_type == "iron").all()
    assert len(irons) == 5

    wedges = db.query(ClubSpec).filter(ClubSpec.club_type == "wedge").all()
    assert len(wedges) == 5
    db.close()


def test_seed_clubs_idempotent():
    db = TestSession()
    count1 = seed_clubs_from_csv(db, "data/club_specs/initial_seed.csv")
    count2 = seed_clubs_from_csv(db, "data/club_specs/initial_seed.csv")
    # Second run should skip duplicates
    assert count2 == 0
    total = db.query(ClubSpec).count()
    assert total == 20
    db.close()
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
python -m pytest backend/tests/test_seed_clubs.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.seed_clubs'`

- [ ] **Step 4: Create scripts/seed_clubs.py**

```python
import csv
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.models.club_spec import ClubSpec


def seed_clubs_from_csv(db: Session, csv_path: str) -> int:
    """Load club specs from CSV into database. Returns count of new records."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {csv_path}")

    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Check for duplicate
            existing = db.query(ClubSpec).filter(
                ClubSpec.brand == row["brand"],
                ClubSpec.model_name == row["model_name"],
                ClubSpec.model_year == int(row["model_year"]),
                ClubSpec.club_type == row["club_type"],
            ).first()
            if existing:
                continue

            club = ClubSpec(
                brand=row["brand"],
                model_name=row["model_name"],
                model_year=int(row["model_year"]),
                club_type=row["club_type"],
                loft=_float_or_none(row.get("loft")),
                lie_angle=_float_or_none(row.get("lie_angle")),
                shaft_options=row.get("shaft_options") or None,
                head_weight=_float_or_none(row.get("head_weight")),
                adjustable=row.get("adjustable", "").strip().lower() == "true",
                loft_range_min=_float_or_none(row.get("loft_range_min")),
                loft_range_max=_float_or_none(row.get("loft_range_max")),
                launch_bias=row.get("launch_bias") or None,
                spin_bias=row.get("spin_bias") or None,
                forgiveness_rating=_int_or_none(row.get("forgiveness_rating")),
                workability_rating=_int_or_none(row.get("workability_rating")),
                swing_speed_min=_float_or_none(row.get("swing_speed_min")),
                swing_speed_max=_float_or_none(row.get("swing_speed_max")),
                msrp=_float_or_none(row.get("msrp")),
                avg_used_price=_float_or_none(row.get("avg_used_price")),
                still_in_production=row.get("still_in_production", "").strip().lower() == "true",
            )
            db.add(club)
            count += 1
    db.commit()
    return count


def _float_or_none(val: str | None) -> float | None:
    if not val or val.strip() == "":
        return None
    return float(val)


def _int_or_none(val: str | None) -> int | None:
    if not val or val.strip() == "":
        return None
    return int(val)


if __name__ == "__main__":
    from backend.app.database import SessionLocal, engine, Base
    from backend.app.models import ClubSpec  # noqa: F811

    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        count = seed_clubs_from_csv(db, "data/club_specs/initial_seed.csv")
        print(f"Seeded {count} club specs")
    finally:
        db.close()
```

Also create `scripts/__init__.py` (empty file).

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest backend/tests/test_seed_clubs.py -v
```

Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add data/club_specs/initial_seed.csv scripts/seed_clubs.py scripts/__init__.py backend/tests/test_seed_clubs.py
git commit -m "feat: add club spec seed data (20 clubs) and seed script"
```

---

### Task 11: Run Full Test Suite & Verify Everything Works Together

**Files:** None new — integration verification.

- [ ] **Step 1: Run all tests**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
source .venv/Scripts/activate
python -m pytest backend/tests/ -v
```

Expected: All tests pass (across all test files).

- [ ] **Step 2: Boot the server and test manually**

```bash
# Seed the database
python -m scripts.seed_clubs

# Start the server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
sleep 2

# Health check
curl http://localhost:8000/

# List clubs
curl http://localhost:8000/clubs

# Search drivers
curl "http://localhost:8000/clubs/search?club_type=driver&swing_speed=105"

# Get a specific club
curl http://localhost:8000/clubs/1

kill %1
```

Expected:
- Health check returns `{"status":"ok","app":"SwingFit"}`
- `/clubs` returns 20 clubs
- Search returns filtered results
- `/clubs/1` returns the first club

- [ ] **Step 3: Commit any fixes if needed, then tag**

```bash
git add -A
git commit -m "chore: Phase 0 complete — foundation and data layer"
```
