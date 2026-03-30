# Phase 2: Fitting Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the fitting engine that computes a user's swing profile from their shot data, scores club recommendations against it, generates plain-English explanations, and supports current-vs-recommended comparison.

**Architecture:** A `SwingProfile` dataclass is computed from all valid shots for a user+club_type. The recommendation engine applies hard filters (speed range, club type, budget) then scores remaining clubs on launch optimization (40%), forgiveness/workability fit (30%), speed fit (20%), and recency (10%). An explanation generator produces human-readable reasoning per recommendation. A comparison endpoint estimates projected performance deltas.

**Tech Stack:** Python, FastAPI, SQLAlchemy, numpy, Pydantic dataclasses

---

### Task 1: SwingProfile Dataclass & Computation

**Files:**
- Create: `backend/app/services/swing_profile.py`
- Create: `backend/tests/test_swing_profile.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_swing_profile.py`:

```python
import numpy as np
import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models.user import User
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.services.swing_profile import compute_swing_profile, SwingProfile


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)


def setup_module():
    Base.metadata.create_all(engine)
    db = TestSession()
    user = User(email="profile@test.com", username="profiler", hashed_password="h")
    db.add(user)
    db.commit()

    session = SwingSession(
        user_id=user.id,
        launch_monitor_type="trackman_4",
        data_source="file_upload",
    )
    db.add(session)
    db.commit()

    # 5 driver shots with realistic spread
    driver_shots = [
        {"ball_speed": 149.0, "launch_angle": 12.0, "spin_rate": 2800.0, "carry_distance": 248.0,
         "club_speed": 105.0, "attack_angle": -1.2, "club_path": 2.0, "face_angle": 0.5,
         "face_to_path": -1.5, "offline_distance": 8.0, "smash_factor": 1.42},
        {"ball_speed": 151.0, "launch_angle": 11.5, "spin_rate": 2650.0, "carry_distance": 255.0,
         "club_speed": 107.0, "attack_angle": -0.8, "club_path": 1.5, "face_angle": 0.3,
         "face_to_path": -1.2, "offline_distance": 4.0, "smash_factor": 1.41},
        {"ball_speed": 148.0, "launch_angle": 13.0, "spin_rate": 2900.0, "carry_distance": 245.0,
         "club_speed": 104.0, "attack_angle": -1.5, "club_path": 2.5, "face_angle": 1.0,
         "face_to_path": -1.5, "offline_distance": -5.0, "smash_factor": 1.42},
        {"ball_speed": 150.0, "launch_angle": 12.5, "spin_rate": 2750.0, "carry_distance": 250.0,
         "club_speed": 106.0, "attack_angle": -1.0, "club_path": 1.8, "face_angle": 0.6,
         "face_to_path": -1.2, "offline_distance": 6.0, "smash_factor": 1.42},
        {"ball_speed": 152.0, "launch_angle": 11.8, "spin_rate": 2700.0, "carry_distance": 258.0,
         "club_speed": 108.0, "attack_angle": -0.5, "club_path": 1.2, "face_angle": 0.2,
         "face_to_path": -1.0, "offline_distance": 3.0, "smash_factor": 1.41},
    ]
    for i, data in enumerate(driver_shots):
        shot = Shot(
            session_id=session.id,
            club_used="driver",
            shot_number=i + 1,
            **data,
        )
        db.add(shot)

    # 1 invalid shot (should be excluded)
    invalid_shot = Shot(
        session_id=session.id,
        club_used="driver",
        ball_speed=50.0, launch_angle=5.0, spin_rate=1000.0,
        carry_distance=80.0, shot_number=6, is_valid=False,
    )
    db.add(invalid_shot)

    # 2 iron shots
    for i in range(2):
        shot = Shot(
            session_id=session.id,
            club_used="7-iron",
            ball_speed=120.0 + i,
            launch_angle=18.0 + i * 0.5,
            spin_rate=6400.0 + i * 100,
            carry_distance=165.0 + i * 2,
            club_speed=82.0 + i,
            shot_number=7 + i,
        )
        db.add(shot)

    db.commit()
    db.close()


def teardown_module():
    Base.metadata.drop_all(engine)


def test_compute_swing_profile_driver():
    db = TestSession()
    profile = compute_swing_profile(db, user_id=1, club_type="driver")
    db.close()

    assert isinstance(profile, SwingProfile)
    assert profile.club_type == "driver"
    assert profile.sample_size == 5  # excludes invalid shot
    assert round(profile.avg_ball_speed, 1) == 150.0
    assert round(profile.avg_carry, 1) == 251.2
    assert round(profile.avg_club_speed, 1) == 106.0
    assert round(profile.avg_launch_angle, 1) == 12.2
    assert round(profile.avg_spin_rate, 1) == 2760.0
    assert profile.avg_attack_angle is not None
    assert profile.std_carry > 0
    assert profile.data_quality == "low"  # < 20 shots


def test_swing_profile_shot_shape():
    db = TestSession()
    profile = compute_swing_profile(db, user_id=1, club_type="driver")
    db.close()

    # avg face_to_path is around -1.3 (between -2 and 2) → straight
    assert profile.shot_shape_tendency == "straight"


def test_swing_profile_iron():
    db = TestSession()
    profile = compute_swing_profile(db, user_id=1, club_type="7-iron")
    db.close()

    assert profile.club_type == "7-iron"
    assert profile.sample_size == 2
    assert profile.data_quality == "low"


def test_swing_profile_no_shots():
    db = TestSession()
    profile = compute_swing_profile(db, user_id=1, club_type="putter")
    db.close()

    assert profile is None


def test_swing_profile_smash_factor():
    db = TestSession()
    profile = compute_swing_profile(db, user_id=1, club_type="driver")
    db.close()

    assert round(profile.smash_factor, 2) == 1.42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_swing_profile.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `backend/app/services/swing_profile.py`:

```python
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot


@dataclass
class SwingProfile:
    club_type: str

    # Central tendency
    avg_club_speed: float
    avg_ball_speed: float
    avg_launch_angle: float
    avg_spin_rate: float
    avg_carry: float
    avg_attack_angle: float | None
    avg_club_path: float | None
    avg_face_angle: float | None

    # Consistency / dispersion
    std_carry: float
    std_offline: float | None
    shot_shape_tendency: str  # "draw", "fade", "straight", "variable"
    miss_direction: str  # "left", "right", "both"

    # Derived
    smash_factor: float
    spin_loft_estimate: float | None

    # Confidence
    sample_size: int
    data_quality: str  # "high", "medium", "low"


def compute_swing_profile(
    db: Session,
    user_id: int,
    club_type: str,
) -> SwingProfile | None:
    """Compute a swing profile from all valid shots for a user and club type.

    Returns None if no valid shots exist for this club type.
    """
    session_ids = [
        s.id for s in db.query(SwingSession.id).filter(
            SwingSession.user_id == user_id
        ).all()
    ]
    if not session_ids:
        return None

    shots = db.query(Shot).filter(
        Shot.session_id.in_(session_ids),
        Shot.club_used == club_type,
        Shot.is_valid == True,
    ).all()

    if not shots:
        return None

    n = len(shots)

    def avg(attr: str) -> float | None:
        vals = [getattr(s, attr) for s in shots if getattr(s, attr) is not None]
        return float(np.mean(vals)) if vals else None

    def std(attr: str) -> float | None:
        vals = [getattr(s, attr) for s in shots if getattr(s, attr) is not None]
        return float(np.std(vals, ddof=0)) if len(vals) >= 2 else None

    avg_club_speed = avg("club_speed") or 0.0
    avg_ball_speed = avg("ball_speed") or 0.0
    avg_launch = avg("launch_angle") or 0.0
    avg_spin = avg("spin_rate") or 0.0
    avg_carry = avg("carry_distance") or 0.0
    avg_attack = avg("attack_angle")
    avg_path = avg("club_path")
    avg_face = avg("face_angle")
    avg_ftp = avg("face_to_path")
    std_ftp = std("face_to_path")

    # Shot shape from face_to_path
    if std_ftp is not None and std_ftp > 4.0:
        shot_shape = "variable"
    elif avg_ftp is not None and avg_ftp < -2.0:
        shot_shape = "draw"
    elif avg_ftp is not None and avg_ftp > 2.0:
        shot_shape = "fade"
    else:
        shot_shape = "straight"

    # Miss direction from offline_distance
    offlines = [s.offline_distance for s in shots if s.offline_distance is not None]
    if offlines:
        avg_offline = float(np.mean(offlines))
        if avg_offline > 3.0:
            miss_dir = "right"
        elif avg_offline < -3.0:
            miss_dir = "left"
        else:
            miss_dir = "both"
    else:
        miss_dir = "both"

    # Smash factor
    smash_vals = [s.smash_factor for s in shots if s.smash_factor is not None]
    smash = float(np.mean(smash_vals)) if smash_vals else (
        avg_ball_speed / avg_club_speed if avg_club_speed > 0 else 0.0
    )

    # Spin loft estimate
    spin_loft = (avg_launch + abs(avg_attack)) if avg_attack is not None else None

    # Data quality
    if n >= 50:
        quality = "high"
    elif n >= 20:
        quality = "medium"
    else:
        quality = "low"

    return SwingProfile(
        club_type=club_type,
        avg_club_speed=avg_club_speed,
        avg_ball_speed=avg_ball_speed,
        avg_launch_angle=avg_launch,
        avg_spin_rate=avg_spin,
        avg_carry=avg_carry,
        avg_attack_angle=avg_attack,
        avg_club_path=avg_path,
        avg_face_angle=avg_face,
        std_carry=std("carry_distance") or 0.0,
        std_offline=std("offline_distance"),
        shot_shape_tendency=shot_shape,
        miss_direction=miss_dir,
        smash_factor=smash,
        spin_loft_estimate=spin_loft,
        sample_size=n,
        data_quality=quality,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_swing_profile.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/swing_profile.py backend/tests/test_swing_profile.py
git commit -m "feat: add SwingProfile computation from shot history"
```

---

### Task 2: Recommendation Scoring Engine

**Files:**
- Create: `backend/app/services/fitting_engine.py`
- Create: `backend/tests/test_fitting_engine.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_fitting_engine.py`:

```python
from backend.app.services.swing_profile import SwingProfile
from backend.app.services.fitting_engine import (
    score_club,
    rank_recommendations,
    OPTIMAL_LAUNCH,
    OPTIMAL_SPIN,
)


def _make_profile(**overrides) -> SwingProfile:
    defaults = {
        "club_type": "driver",
        "avg_club_speed": 105.0,
        "avg_ball_speed": 150.0,
        "avg_launch_angle": 14.0,
        "avg_spin_rate": 3100.0,
        "avg_carry": 248.0,
        "avg_attack_angle": -1.2,
        "avg_club_path": 2.0,
        "avg_face_angle": 0.5,
        "std_carry": 8.0,
        "std_offline": 12.0,
        "shot_shape_tendency": "straight",
        "miss_direction": "right",
        "smash_factor": 1.42,
        "spin_loft_estimate": 15.2,
        "sample_size": 50,
        "data_quality": "high",
    }
    defaults.update(overrides)
    return SwingProfile(**defaults)


def _make_club(**overrides) -> dict:
    """Simulate a ClubSpec as a dict with the fields score_club needs."""
    defaults = {
        "id": 1,
        "brand": "Titleist",
        "model_name": "TSR3",
        "model_year": 2025,
        "club_type": "driver",
        "loft": 9.0,
        "launch_bias": "low",
        "spin_bias": "low",
        "forgiveness_rating": 5,
        "workability_rating": 9,
        "swing_speed_min": 90.0,
        "swing_speed_max": 120.0,
        "msrp": 599.99,
        "avg_used_price": 380.0,
        "still_in_production": True,
    }
    defaults.update(overrides)
    return defaults


def test_score_club_returns_float():
    profile = _make_profile()
    club = _make_club()
    score = score_club(profile, club)
    assert isinstance(score, float)
    assert 0 <= score <= 100


def test_high_spin_user_prefers_low_spin_club():
    profile = _make_profile(avg_spin_rate=3200.0)
    low_spin = _make_club(spin_bias="low")
    high_spin = _make_club(spin_bias="high")
    assert score_club(profile, low_spin) > score_club(profile, high_spin)


def test_high_launch_user_prefers_low_launch_club():
    profile = _make_profile(avg_launch_angle=16.0)
    low_launch = _make_club(launch_bias="low")
    high_launch = _make_club(launch_bias="high")
    assert score_club(profile, low_launch) > score_club(profile, high_launch)


def test_high_dispersion_prefers_forgiveness():
    profile = _make_profile(std_offline=20.0)
    forgiving = _make_club(forgiveness_rating=9, workability_rating=3)
    workable = _make_club(forgiveness_rating=3, workability_rating=9)
    assert score_club(profile, forgiving) > score_club(profile, workable)


def test_low_dispersion_prefers_workability():
    profile = _make_profile(std_offline=5.0)
    forgiving = _make_club(forgiveness_rating=9, workability_rating=3)
    workable = _make_club(forgiveness_rating=3, workability_rating=9)
    assert score_club(profile, workable) > score_club(profile, forgiving)


def test_speed_fit_centered_scores_higher():
    profile = _make_profile(avg_club_speed=105.0)
    centered = _make_club(swing_speed_min=90.0, swing_speed_max=120.0)  # center=105
    off_center = _make_club(swing_speed_min=110.0, swing_speed_max=140.0)  # center=125
    assert score_club(profile, centered) > score_club(profile, off_center)


def test_newer_club_scores_higher():
    profile = _make_profile()
    new_club = _make_club(model_year=2025)
    old_club = _make_club(model_year=2020)
    # Same specs otherwise, so only recency differs
    new_score = score_club(profile, new_club)
    old_score = score_club(profile, old_club)
    assert new_score > old_score


def test_rank_recommendations():
    profile = _make_profile(avg_spin_rate=3200.0, avg_launch_angle=15.0, std_offline=18.0)
    clubs = [
        _make_club(id=1, brand="Titleist", model_name="TSR3", launch_bias="low", spin_bias="low",
                   forgiveness_rating=5, workability_rating=9),
        _make_club(id=2, brand="TaylorMade", model_name="Qi10 Max", launch_bias="high", spin_bias="mid",
                   forgiveness_rating=9, workability_rating=3),
        _make_club(id=3, brand="Ping", model_name="G430 Max", launch_bias="mid", spin_bias="mid",
                   forgiveness_rating=9, workability_rating=4),
    ]
    ranked = rank_recommendations(profile, clubs, top_n=3)
    assert len(ranked) == 3
    assert all("score" in r for r in ranked)
    assert all("club" in r for r in ranked)
    # Scores should be descending
    scores = [r["score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_optimal_constants_exist():
    assert "driver" in OPTIMAL_LAUNCH
    assert "driver" in OPTIMAL_SPIN
    assert "7-iron" in OPTIMAL_LAUNCH
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_fitting_engine.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `backend/app/services/fitting_engine.py`:

```python
from datetime import datetime, timezone

from backend.app.services.swing_profile import SwingProfile


CURRENT_YEAR = datetime.now(timezone.utc).year

# Optimal launch angles per club type (degrees)
OPTIMAL_LAUNCH: dict[str, tuple[float, float]] = {
    "driver": (12.0, 15.0),
    "3-wood": (11.0, 14.0),
    "5-wood": (12.0, 15.0),
    "3-hybrid": (12.0, 15.0),
    "4-hybrid": (13.0, 16.0),
    "5-hybrid": (14.0, 17.0),
    "4-iron": (14.0, 17.0),
    "5-iron": (15.0, 18.0),
    "6-iron": (16.0, 19.0),
    "7-iron": (16.0, 20.0),
    "8-iron": (18.0, 22.0),
    "9-iron": (20.0, 25.0),
    "PW": (24.0, 28.0),
    "GW": (26.0, 30.0),
    "SW": (28.0, 34.0),
    "LW": (30.0, 36.0),
}

# Optimal spin rates per club type (rpm)
OPTIMAL_SPIN: dict[str, tuple[float, float]] = {
    "driver": (2000.0, 2500.0),
    "3-wood": (3000.0, 4000.0),
    "5-wood": (3500.0, 4500.0),
    "3-hybrid": (3500.0, 4500.0),
    "4-hybrid": (4000.0, 5000.0),
    "5-hybrid": (4500.0, 5500.0),
    "4-iron": (4500.0, 5500.0),
    "5-iron": (5000.0, 6000.0),
    "6-iron": (5500.0, 6500.0),
    "7-iron": (6000.0, 7000.0),
    "8-iron": (7000.0, 8000.0),
    "9-iron": (7500.0, 8500.0),
    "PW": (8000.0, 9500.0),
    "GW": (8500.0, 10000.0),
    "SW": (9000.0, 10500.0),
    "LW": (9500.0, 11000.0),
}

# Dispersion threshold (yards std) — above this, prioritize forgiveness
HIGH_DISPERSION_THRESHOLD = 12.0


def score_club(profile: SwingProfile, club: dict) -> float:
    """Score a club's fit for a given swing profile. Scale 0-100."""
    score = 0.0

    # --- Launch optimization (20 points) ---
    optimal_launch = OPTIMAL_LAUNCH.get(profile.club_type, (12.0, 15.0))
    launch_mid = (optimal_launch[0] + optimal_launch[1]) / 2
    if profile.avg_launch_angle > optimal_launch[1]:
        # Launches too high — reward low launch
        score += {"low": 20, "mid": 10, "high": 0}.get(club.get("launch_bias", "mid"), 5)
    elif profile.avg_launch_angle < optimal_launch[0]:
        # Launches too low — reward high launch
        score += {"high": 20, "mid": 10, "low": 0}.get(club.get("launch_bias", "mid"), 5)
    else:
        # In the zone — reward mid
        score += {"mid": 20, "low": 10, "high": 10}.get(club.get("launch_bias", "mid"), 10)

    # --- Spin optimization (20 points) ---
    optimal_spin = OPTIMAL_SPIN.get(profile.club_type, (2000.0, 2500.0))
    if profile.avg_spin_rate > optimal_spin[1]:
        score += {"low": 20, "mid": 10, "high": 0}.get(club.get("spin_bias", "mid"), 5)
    elif profile.avg_spin_rate < optimal_spin[0]:
        score += {"high": 20, "mid": 10, "low": 0}.get(club.get("spin_bias", "mid"), 5)
    else:
        score += {"mid": 20, "low": 10, "high": 10}.get(club.get("spin_bias", "mid"), 10)

    # --- Forgiveness vs Workability (30 points) ---
    dispersion = profile.std_offline if profile.std_offline is not None else profile.std_carry
    forgiveness = club.get("forgiveness_rating") or 5
    workability = club.get("workability_rating") or 5
    if dispersion > HIGH_DISPERSION_THRESHOLD:
        score += forgiveness * 3  # max 30
    else:
        score += workability * 3  # max 30

    # --- Swing speed fit (20 points) ---
    speed_min = club.get("swing_speed_min")
    speed_max = club.get("swing_speed_max")
    if speed_min is not None and speed_max is not None and speed_max > speed_min:
        speed_center = (speed_min + speed_max) / 2
        speed_range = speed_max - speed_min
        speed_fit = 1.0 - abs(profile.avg_club_speed - speed_center) / (speed_range / 2)
        score += max(0.0, speed_fit * 20)

    # --- Recency bonus (10 points) ---
    model_year = club.get("model_year", CURRENT_YEAR)
    years_old = CURRENT_YEAR - model_year
    score += max(0, 10 - years_old * 2)

    return round(score, 1)


def rank_recommendations(
    profile: SwingProfile,
    clubs: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """Score and rank clubs, returning top_n results."""
    scored = []
    for club in clubs:
        s = score_club(profile, club)
        scored.append({"club": club, "score": s})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_fitting_engine.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/fitting_engine.py backend/tests/test_fitting_engine.py
git commit -m "feat: add club recommendation scoring engine"
```

---

### Task 3: Explanation Generator

**Files:**
- Create: `backend/app/services/explanation.py`
- Create: `backend/tests/test_explanation.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_explanation.py`:

```python
from backend.app.services.swing_profile import SwingProfile
from backend.app.services.explanation import generate_explanation
from backend.app.services.fitting_engine import OPTIMAL_SPIN


def _make_profile(**overrides) -> SwingProfile:
    defaults = {
        "club_type": "driver",
        "avg_club_speed": 105.0,
        "avg_ball_speed": 150.0,
        "avg_launch_angle": 14.0,
        "avg_spin_rate": 3100.0,
        "avg_carry": 248.0,
        "avg_attack_angle": -1.2,
        "avg_club_path": 2.0,
        "avg_face_angle": 0.5,
        "std_carry": 8.0,
        "std_offline": 12.0,
        "shot_shape_tendency": "straight",
        "miss_direction": "right",
        "smash_factor": 1.42,
        "spin_loft_estimate": 15.2,
        "sample_size": 50,
        "data_quality": "high",
    }
    defaults.update(overrides)
    return SwingProfile(**defaults)


def _make_club(**overrides) -> dict:
    defaults = {
        "brand": "Titleist",
        "model_name": "TSR3",
        "model_year": 2025,
        "club_type": "driver",
        "loft": 9.0,
        "launch_bias": "low",
        "spin_bias": "low",
        "forgiveness_rating": 5,
        "workability_rating": 9,
        "swing_speed_min": 90.0,
        "swing_speed_max": 120.0,
    }
    defaults.update(overrides)
    return defaults


def test_explanation_mentions_club():
    profile = _make_profile(avg_spin_rate=3200.0)
    club = _make_club(brand="Titleist", model_name="TSR3")
    explanation = generate_explanation(profile, club)
    assert "Titleist TSR3" in explanation


def test_explanation_addresses_high_spin():
    profile = _make_profile(avg_spin_rate=3200.0)
    club = _make_club(spin_bias="low")
    explanation = generate_explanation(profile, club)
    assert "spin" in explanation.lower()


def test_explanation_addresses_high_launch():
    profile = _make_profile(avg_launch_angle=17.0)
    club = _make_club(launch_bias="low")
    explanation = generate_explanation(profile, club)
    assert "launch" in explanation.lower()


def test_explanation_addresses_forgiveness():
    profile = _make_profile(std_offline=20.0)
    club = _make_club(forgiveness_rating=9)
    explanation = generate_explanation(profile, club)
    assert "forgiv" in explanation.lower()


def test_explanation_is_nonempty():
    profile = _make_profile()
    club = _make_club()
    explanation = generate_explanation(profile, club)
    assert len(explanation) > 20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_explanation.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `backend/app/services/explanation.py`:

```python
from backend.app.services.swing_profile import SwingProfile
from backend.app.services.fitting_engine import (
    OPTIMAL_LAUNCH,
    OPTIMAL_SPIN,
    HIGH_DISPERSION_THRESHOLD,
)


def generate_explanation(profile: SwingProfile, club: dict) -> str:
    """Generate a plain-English explanation of why a club fits a swing profile."""
    brand = club.get("brand", "")
    model = club.get("model_name", "")
    club_name = f"{brand} {model}".strip()

    reasons: list[str] = []

    # Launch analysis
    optimal_launch = OPTIMAL_LAUNCH.get(profile.club_type, (12.0, 15.0))
    if profile.avg_launch_angle > optimal_launch[1]:
        diff = round(profile.avg_launch_angle - optimal_launch[1], 1)
        if club.get("launch_bias") == "low":
            reasons.append(
                f"Your launch angle ({profile.avg_launch_angle:.1f}°) is {diff}° above optimal. "
                f"The {club_name}'s low-launch design should bring that down into the {optimal_launch[0]:.0f}-{optimal_launch[1]:.0f}° window."
            )
    elif profile.avg_launch_angle < optimal_launch[0]:
        diff = round(optimal_launch[0] - profile.avg_launch_angle, 1)
        if club.get("launch_bias") == "high":
            reasons.append(
                f"Your launch angle ({profile.avg_launch_angle:.1f}°) is {diff}° below optimal. "
                f"The {club_name}'s high-launch profile should help get the ball up."
            )

    # Spin analysis
    optimal_spin = OPTIMAL_SPIN.get(profile.club_type, (2000.0, 2500.0))
    if profile.avg_spin_rate > optimal_spin[1]:
        excess = round(profile.avg_spin_rate - optimal_spin[1])
        if club.get("spin_bias") == "low":
            reasons.append(
                f"Your spin rate ({profile.avg_spin_rate:.0f} rpm) is ~{excess} rpm above optimal. "
                f"The {club_name} is a low-spin head that could reduce spin by 200-400 rpm and add 5-10 yards of carry."
            )
    elif profile.avg_spin_rate < optimal_spin[0]:
        deficit = round(optimal_spin[0] - profile.avg_spin_rate)
        if club.get("spin_bias") == "high":
            reasons.append(
                f"Your spin rate ({profile.avg_spin_rate:.0f} rpm) is ~{deficit} rpm below optimal. "
                f"The {club_name} adds spin to improve ball flight and stopping power."
            )

    # Forgiveness / dispersion
    dispersion = profile.std_offline if profile.std_offline is not None else profile.std_carry
    forgiveness = club.get("forgiveness_rating") or 5
    if dispersion > HIGH_DISPERSION_THRESHOLD and forgiveness >= 7:
        reasons.append(
            f"Your shot dispersion is {dispersion:.1f} yards — the {club_name} has a "
            f"forgiveness rating of {forgiveness}/10, which should tighten up your misses."
        )
    elif dispersion <= HIGH_DISPERSION_THRESHOLD:
        workability = club.get("workability_rating") or 5
        if workability >= 7:
            reasons.append(
                f"Your tight dispersion ({dispersion:.1f} yd) means you can benefit from "
                f"the {club_name}'s workability ({workability}/10) for shot shaping."
            )

    # Speed fit
    speed_min = club.get("swing_speed_min")
    speed_max = club.get("swing_speed_max")
    if speed_min and speed_max:
        reasons.append(
            f"Your club speed ({profile.avg_club_speed:.0f} mph) fits well in the "
            f"{club_name}'s designed range of {speed_min:.0f}-{speed_max:.0f} mph."
        )

    if not reasons:
        reasons.append(
            f"The {club_name} is a well-rounded match for your swing profile."
        )

    return " ".join(reasons)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_explanation.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/explanation.py backend/tests/test_explanation.py
git commit -m "feat: add recommendation explanation generator"
```

---

### Task 4: Fitting API Endpoints

**Files:**
- Create: `backend/app/routers/fitting.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_routers_fitting.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_routers_fitting.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.models.club_spec import ClubSpec

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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

    # Create user
    user = User(email="fit@test.com", username="fitter", hashed_password="h")
    db.add(user)
    db.commit()
    global USER_ID
    USER_ID = user.id

    # Create session with driver shots
    session = SwingSession(
        user_id=user.id,
        launch_monitor_type="trackman_4",
        data_source="file_upload",
    )
    db.add(session)
    db.commit()

    for i in range(5):
        shot = Shot(
            session_id=session.id,
            club_used="driver",
            ball_speed=149.0 + i,
            launch_angle=14.0 + i * 0.2,
            spin_rate=3100.0 + i * 50,
            carry_distance=248.0 + i,
            club_speed=105.0 + i * 0.5,
            attack_angle=-1.2,
            face_to_path=-1.3,
            offline_distance=8.0 + i,
            smash_factor=1.42,
            shot_number=i + 1,
        )
        db.add(shot)

    # Create some clubs
    clubs_data = [
        {"brand": "Titleist", "model_name": "TSR3", "model_year": 2025, "club_type": "driver",
         "loft": 9.0, "launch_bias": "low", "spin_bias": "low",
         "forgiveness_rating": 5, "workability_rating": 9,
         "swing_speed_min": 90.0, "swing_speed_max": 120.0,
         "msrp": 599.99, "avg_used_price": 380.0, "still_in_production": True},
        {"brand": "TaylorMade", "model_name": "Qi10 Max", "model_year": 2025, "club_type": "driver",
         "loft": 10.5, "launch_bias": "high", "spin_bias": "mid",
         "forgiveness_rating": 9, "workability_rating": 3,
         "swing_speed_min": 80.0, "swing_speed_max": 115.0,
         "msrp": 599.99, "avg_used_price": 450.0, "still_in_production": True},
        {"brand": "Ping", "model_name": "G430 Max", "model_year": 2023, "club_type": "driver",
         "loft": 10.5, "launch_bias": "mid", "spin_bias": "mid",
         "forgiveness_rating": 9, "workability_rating": 4,
         "swing_speed_min": 75.0, "swing_speed_max": 115.0,
         "msrp": 549.99, "avg_used_price": 300.0, "still_in_production": True},
        {"brand": "Titleist", "model_name": "T150", "model_year": 2023, "club_type": "iron",
         "loft": 33.0, "launch_bias": "mid", "spin_bias": "mid",
         "forgiveness_rating": 5, "workability_rating": 8,
         "swing_speed_min": 80.0, "swing_speed_max": 115.0,
         "msrp": 1399.99, "still_in_production": True},
    ]
    for c in clubs_data:
        db.add(ClubSpec(**c))

    db.commit()
    db.close()


def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)


client = TestClient(app)


def test_get_swing_profile():
    response = client.get(f"/users/{USER_ID}/swing-profile", params={"club_type": "driver"})
    assert response.status_code == 200
    data = response.json()
    assert data["club_type"] == "driver"
    assert data["sample_size"] == 5
    assert "avg_ball_speed" in data
    assert "shot_shape_tendency" in data
    assert "data_quality" in data


def test_get_swing_profile_no_shots():
    response = client.get(f"/users/{USER_ID}/swing-profile", params={"club_type": "putter"})
    assert response.status_code == 404


def test_recommend_clubs():
    response = client.post("/fitting/recommend", json={
        "user_id": USER_ID,
        "club_type": "driver",
    })
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert "profile" in data
    recs = data["recommendations"]
    assert len(recs) >= 1
    assert len(recs) <= 5
    # All should be drivers, not irons
    for r in recs:
        assert r["club"]["club_type"] == "driver"
    assert all("score" in r for r in recs)
    assert all("explanation" in r for r in recs)
    # Should be sorted descending by score
    scores = [r["score"] for r in recs]
    assert scores == sorted(scores, reverse=True)


def test_recommend_with_budget():
    response = client.post("/fitting/recommend", json={
        "user_id": USER_ID,
        "club_type": "driver",
        "budget_max": 400.0,
        "include_used": True,
    })
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    for r in recs:
        price = r["club"].get("avg_used_price") or r["club"].get("msrp")
        assert price is not None
        assert price <= 400.0


def test_recommend_no_profile():
    response = client.post("/fitting/recommend", json={
        "user_id": USER_ID,
        "club_type": "putter",
    })
    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_routers_fitting.py -v`
Expected: FAIL — routes don't exist

- [ ] **Step 3: Write implementation**

Create `backend/app/routers/fitting.py`:

```python
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.club_spec import ClubSpec
from backend.app.models.user import User
from backend.app.services.swing_profile import compute_swing_profile
from backend.app.services.fitting_engine import score_club, rank_recommendations
from backend.app.services.explanation import generate_explanation

router = APIRouter(tags=["fitting"])


@router.get("/users/{user_id}/swing-profile")
def get_swing_profile(user_id: int, club_type: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = compute_swing_profile(db, user_id, club_type)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No valid shots found for {club_type}")

    return asdict(profile)


class RecommendRequest(BaseModel):
    user_id: int
    club_type: str
    budget_max: float | None = None
    include_used: bool = False
    top_n: int = 5


@router.post("/fitting/recommend")
def recommend_clubs(req: RecommendRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = compute_swing_profile(db, req.user_id, req.club_type)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No valid shots found for {req.club_type}")

    # Hard filter: club type + speed range
    query = db.query(ClubSpec).filter(ClubSpec.club_type == req.club_type)
    if profile.avg_club_speed > 0:
        query = query.filter(
            ClubSpec.swing_speed_min <= profile.avg_club_speed,
            ClubSpec.swing_speed_max >= profile.avg_club_speed,
        )
    all_clubs = query.all()

    # Convert to dicts for scoring
    club_dicts = []
    for c in all_clubs:
        d = {
            "id": c.id,
            "brand": c.brand,
            "model_name": c.model_name,
            "model_year": c.model_year,
            "club_type": c.club_type,
            "loft": c.loft,
            "launch_bias": c.launch_bias,
            "spin_bias": c.spin_bias,
            "forgiveness_rating": c.forgiveness_rating,
            "workability_rating": c.workability_rating,
            "swing_speed_min": c.swing_speed_min,
            "swing_speed_max": c.swing_speed_max,
            "msrp": c.msrp,
            "avg_used_price": c.avg_used_price,
            "still_in_production": c.still_in_production,
        }

        # Budget filter
        if req.budget_max is not None:
            if req.include_used and d.get("avg_used_price"):
                if d["avg_used_price"] > req.budget_max:
                    continue
            elif d.get("msrp") and d["msrp"] > req.budget_max:
                continue

        club_dicts.append(d)

    ranked = rank_recommendations(profile, club_dicts, top_n=req.top_n)

    # Add explanations
    for rec in ranked:
        rec["explanation"] = generate_explanation(profile, rec["club"])

    return {
        "profile": asdict(profile),
        "recommendations": ranked,
    }
```

- [ ] **Step 4: Register fitting router in main.py**

Read `backend/app/main.py` first, then add the fitting router. The final state:

```python
from fastapi import FastAPI

from backend.app.config import settings
from backend.app.routers.clubs import router as clubs_router
from backend.app.routers.sessions import router as sessions_router
from backend.app.routers.ingest import router as ingest_router
from backend.app.routers.fitting import router as fitting_router

app = FastAPI(title=settings.app_name)
app.include_router(clubs_router)
app.include_router(sessions_router)
app.include_router(ingest_router)
app.include_router(fitting_router)


@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.app_name}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_routers_fitting.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/fitting.py backend/app/main.py backend/tests/test_routers_fitting.py
git commit -m "feat: add fitting API endpoints with swing profile and recommendations"
```

---

### Task 5: Comparison Endpoint

**Files:**
- Modify: `backend/app/routers/fitting.py`
- Create: `backend/tests/test_routers_comparison.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_routers_comparison.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.user import User
from backend.app.models.session import SwingSession
from backend.app.models.shot import Shot
from backend.app.models.club_spec import ClubSpec

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)

USER_ID = None
CURRENT_CLUB_ID = None
RECOMMENDED_CLUB_ID = None


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

    user = User(email="compare@test.com", username="comparer", hashed_password="h")
    db.add(user)
    db.commit()
    global USER_ID
    USER_ID = user.id

    session = SwingSession(
        user_id=user.id,
        launch_monitor_type="trackman_4",
        data_source="file_upload",
    )
    db.add(session)
    db.commit()

    for i in range(5):
        shot = Shot(
            session_id=session.id,
            club_used="driver",
            ball_speed=149.0 + i,
            launch_angle=14.0,
            spin_rate=3100.0,
            carry_distance=248.0 + i,
            club_speed=105.0,
            offline_distance=8.0,
            smash_factor=1.42,
            shot_number=i + 1,
        )
        db.add(shot)

    current = ClubSpec(
        brand="TaylorMade", model_name="SIM2 Max", model_year=2021, club_type="driver",
        loft=10.5, launch_bias="high", spin_bias="mid",
        forgiveness_rating=8, workability_rating=4,
        swing_speed_min=80.0, swing_speed_max=115.0,
        msrp=499.99, still_in_production=False,
    )
    db.add(current)
    db.commit()
    global CURRENT_CLUB_ID
    CURRENT_CLUB_ID = current.id

    recommended = ClubSpec(
        brand="Titleist", model_name="TSR3", model_year=2025, club_type="driver",
        loft=9.0, launch_bias="low", spin_bias="low",
        forgiveness_rating=5, workability_rating=9,
        swing_speed_min=90.0, swing_speed_max=120.0,
        msrp=599.99, avg_used_price=380.0, still_in_production=True,
    )
    db.add(recommended)
    db.commit()
    global RECOMMENDED_CLUB_ID
    RECOMMENDED_CLUB_ID = recommended.id

    db.close()


def teardown_module():
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(engine)


client = TestClient(app)


def test_compare_clubs():
    response = client.post("/fitting/compare", json={
        "user_id": USER_ID,
        "club_type": "driver",
        "current_club_id": CURRENT_CLUB_ID,
        "recommended_club_id": RECOMMENDED_CLUB_ID,
    })
    assert response.status_code == 200
    data = response.json()
    assert "current" in data
    assert "recommended" in data
    assert "profile" in data
    assert "explanation" in data
    assert data["current"]["brand"] == "TaylorMade"
    assert data["recommended"]["brand"] == "Titleist"
    assert "current_score" in data
    assert "recommended_score" in data
    assert data["recommended_score"] >= 0


def test_compare_club_not_found():
    response = client.post("/fitting/compare", json={
        "user_id": USER_ID,
        "club_type": "driver",
        "current_club_id": 9999,
        "recommended_club_id": RECOMMENDED_CLUB_ID,
    })
    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_routers_comparison.py -v`
Expected: FAIL — endpoint doesn't exist

- [ ] **Step 3: Add compare endpoint to fitting router**

Append to `backend/app/routers/fitting.py`:

Add this import at the top (if not already there):
```python
from backend.app.models.club_spec import ClubSpec
```

Add this Pydantic model and endpoint at the bottom:

```python
class CompareRequest(BaseModel):
    user_id: int
    club_type: str
    current_club_id: int
    recommended_club_id: int


def _club_to_dict(club: ClubSpec) -> dict:
    return {
        "id": club.id,
        "brand": club.brand,
        "model_name": club.model_name,
        "model_year": club.model_year,
        "club_type": club.club_type,
        "loft": club.loft,
        "launch_bias": club.launch_bias,
        "spin_bias": club.spin_bias,
        "forgiveness_rating": club.forgiveness_rating,
        "workability_rating": club.workability_rating,
        "swing_speed_min": club.swing_speed_min,
        "swing_speed_max": club.swing_speed_max,
        "msrp": club.msrp,
        "avg_used_price": club.avg_used_price,
        "still_in_production": club.still_in_production,
    }


@router.post("/fitting/compare")
def compare_clubs(req: CompareRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = compute_swing_profile(db, req.user_id, req.club_type)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No valid shots found for {req.club_type}")

    current_club = db.query(ClubSpec).filter(ClubSpec.id == req.current_club_id).first()
    if not current_club:
        raise HTTPException(status_code=404, detail="Current club not found")

    rec_club = db.query(ClubSpec).filter(ClubSpec.id == req.recommended_club_id).first()
    if not rec_club:
        raise HTTPException(status_code=404, detail="Recommended club not found")

    current_dict = _club_to_dict(current_club)
    rec_dict = _club_to_dict(rec_club)

    current_score = score_club(profile, current_dict)
    rec_score = score_club(profile, rec_dict)
    explanation = generate_explanation(profile, rec_dict)

    return {
        "profile": asdict(profile),
        "current": current_dict,
        "recommended": rec_dict,
        "current_score": current_score,
        "recommended_score": rec_score,
        "score_difference": round(rec_score - current_score, 1),
        "explanation": explanation,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_routers_comparison.py -v`
Expected: Both tests PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/fitting.py backend/tests/test_routers_comparison.py
git commit -m "feat: add club comparison endpoint"
```

---

### Task 6: Full Test Suite & Integration Verification

**Files:** None new — integration verification only.

- [ ] **Step 1: Run all tests**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
source .venv/Scripts/activate
python -m pytest backend/tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: End-to-end integration test**

```bash
python -c "
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import User, ClubSpec, SwingSession, Shot
from scripts.seed_clubs import seed_clubs_from_csv

# Setup
Base.metadata.create_all(engine)
db = SessionLocal()
user = User(email='e2e@test.com', username='e2e', hashed_password='h')
db.add(user)
db.commit()
uid = user.id
seed_clubs_from_csv(db, 'data/club_specs/initial_seed.csv')

# Add shots
session = SwingSession(user_id=uid, launch_monitor_type='trackman_4', data_source='file_upload')
db.add(session)
db.commit()
for i in range(10):
    db.add(Shot(session_id=session.id, club_used='driver',
        ball_speed=149+i, launch_angle=14.0, spin_rate=3100.0,
        carry_distance=248+i, club_speed=105.0, smash_factor=1.42,
        offline_distance=8.0, shot_number=i+1))
db.commit()
db.close()

client = TestClient(app)

# Swing profile
r = client.get(f'/users/{uid}/swing-profile', params={'club_type': 'driver'})
print(f'Profile: {r.status_code} | {r.json()[\"avg_ball_speed\"]:.1f} mph | {r.json()[\"data_quality\"]}')

# Recommendations
r = client.post('/fitting/recommend', json={'user_id': uid, 'club_type': 'driver'})
recs = r.json()['recommendations']
print(f'Recommendations: {len(recs)} clubs')
for rec in recs[:3]:
    print(f'  {rec[\"club\"][\"brand\"]} {rec[\"club\"][\"model_name\"]}: {rec[\"score\"]}/100')
    print(f'    {rec[\"explanation\"][:80]}...')

print('Phase 2 integration checks passed!')
"
```

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "chore: Phase 2 complete — fitting engine with recommendations and comparison"
```
