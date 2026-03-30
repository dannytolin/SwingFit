# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

```bash
# Activate venv (Windows Git Bash)
source .venv/Scripts/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# Run all tests
python -m pytest backend/tests/ -v

# Run a single test file
python -m pytest backend/tests/test_trackman_csv_parser.py -v

# Run a single test
python -m pytest backend/tests/test_trackman_csv_parser.py::test_parse_trackman_csv_returns_shots -v

# Seed the club database
python -m scripts.seed_clubs

# Run Alembic migrations (from backend/ directory)
cd backend && alembic upgrade head

# Generate a new migration after model changes (from backend/ directory)
cd backend && alembic revision --autogenerate -m "description"
```

Always use `python -m pytest` (not bare `pytest`) — the project uses package-relative imports that require the module path.

## Architecture

**SwingFit** is a golf equipment fitting engine: ingests swing data from launch monitors, computes swing profiles, recommends clubs, and explains why each club fits.

### Backend (FastAPI + SQLAlchemy + SQLite)

Four routers registered in `backend/app/main.py`: clubs, sessions, ingest, fitting.

**Data flow — Ingest:** File upload → format auto-detection → parser → `list[ShotCreate]` → DB persistence → data quality tagging

**Data flow — Fitting:** Compute `SwingProfile` from shots → hard filter clubs (speed range, type, budget) → score each club (launch/spin/forgiveness/speed/recency) → rank → generate explanation per recommendation

**Models** (`backend/app/models/`): User → SwingSession → Shot (one-to-many chain). ClubSpec is independent (the club equipment database).

**Parsers** (`backend/app/services/parsers/`): Each parser takes raw input and returns `list[ShotCreate]`. The upload endpoint tries parsers in order: Garmin R10 → Trackman CSV → Generic CSV. Garmin must be checked before Trackman because their header base-names overlap.

**Fitting engine** (`backend/app/services/`): Three services work together:
- `swing_profile.py` — `compute_swing_profile(db, user_id, club_type)` returns a `SwingProfile` dataclass with averages, dispersion, shot shape, data quality tier
- `fitting_engine.py` — `score_club(profile, club_dict)` scores 0-100 across 5 factors; `rank_recommendations()` sorts and returns top N
- `explanation.py` — `generate_explanation(profile, club_dict)` produces plain-English reasoning referencing the user's specific numbers

**Scoring breakdown** (100 points total): launch optimization (20), spin optimization (20), forgiveness vs workability fit (30), swing speed range fit (20), model recency (10). Optimal launch/spin constants per club type are in `OPTIMAL_LAUNCH` and `OPTIMAL_SPIN` dicts.

### Key Conventions

- All internal units are imperial (mph, yards, feet, degrees, rpm). Metric inputs are converted on ingest via `backend/app/utils/unit_converter.py`.
- Club names are normalized via `backend/app/utils/club_normalizer.py` (e.g., "7 Iron" → "7-iron", "PW" → "PW", "3 Wood" → "3-wood").
- SQLAlchemy model import order matters in `backend/app/models/__init__.py` — ClubSpec and User must be imported before SwingSession and Shot due to relationship resolution.
- Router tests use `StaticPool` with in-memory SQLite and manage `app.dependency_overrides[get_db]` in `setup_module`/`teardown_module` to avoid cross-file interference.
- The Trackman Vision parser (`report_vision.py`) calls the Anthropic API — tests mock `TrackmanReportParser` at the import site (`backend.app.routers.ingest.TrackmanReportParser`).
- The fitting router passes ClubSpec ORM objects as dicts to the scoring/explanation services (not ORM instances directly).

### What's Built vs Planned

- **Phase 0 (complete):** Project scaffold, all models, club CRUD, session/shot endpoints, seed data (20 clubs)
- **Phase 1 (complete):** Ingest pipeline — Trackman CSV, Garmin R10, generic CSV, Claude Vision OCR, manual entry, data quality tiering
- **Phase 2 (complete):** Fitting engine — swing profile computation, 5-factor recommendation scoring, plain-English explanations, club comparison
- **Phase 3 (not started):** Affiliate links, purchase routing
- **Phase 4 (not started):** Frontend (React/Vite), mobile-first SPA
- **Phase 5+:** Subscriptions (Stripe), new club alerts, B2B licensing

See `SwingFit_ProcessMap.md` for the full product spec and `docs/superpowers/plans/` for implementation plans.
