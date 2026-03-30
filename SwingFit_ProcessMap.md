# SwingFit — Golf Equipment Fitting Engine
## Claude Code Process Map & Build Guide

---

## Product Vision

An app that ingests swing data — primarily from Trackman (the industry standard at fitting studios, lessons, and indoor sim facilities) plus consumer launch monitors like Garmin R10 — and delivers real-time club fitting recommendations matched against a database of new and used clubs with live pricing. Think "automated club fitting without the $200 in-person session."

**Core value prop:** You hit balls on a Trackman (or any launch monitor) → the app tells you exactly what clubs to buy, where to buy them, and why — instantly.

**Why Trackman-first:** Trackman is the gold standard. It's the device golfers encounter at GOLFTEC sessions, PGA coach lessons, Trackman Range facilities, and indoor sim bays. Even golfers who don't own a personal launch monitor have Trackman data sitting in their MyTrackman account from fitting sessions and lessons. Building around Trackman data captures the highest-fidelity swing profiles and the largest addressable user base of serious golfers who care about equipment optimization.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│            React (Vite) — Mobile-first SPA                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐   │
│  │  Upload  │ │  My Bag  │ │  Recs    │ │  Buy Links    │   │
│  │  Session │ │  Profile │ │  Engine  │ │  (Affiliate)  │   │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────────┐
│                     BACKEND (FastAPI / Python)               │
│  ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌───────────┐   │
│  │  Auth    │ │  Ingest      │ │  Fitting │ │ Affiliate │   │
│  │  Module  │ │  Pipeline    │ │  Engine  │ │ Router    │   │
│  └──────────┘ └──────┬───────┘ └──────────┘ └───────────┘   │
│                      │                                       │
│         ┌────────────┼────────────────┐                      │
│         ▼            ▼                ▼                      │
│  ┌─────────────┐ ┌──────────┐ ┌────────────┐               │
│  │  Trackman   │ │  CSV     │ │  Manual    │               │
│  │  Integration│ │  Parsers │ │  Entry     │               │
│  │  Layer      │ │  (Garmin,│ │            │               │
│  │             │ │  Rapsodo,│ │            │               │
│  │  • Range API│ │  KIT,    │ │            │               │
│  │  • TM4 TCP │ │  Generic)│ │            │               │
│  │  • File    │ │          │ │            │               │
│  │    Import  │ │          │ │            │               │
│  │  • Swing-  │ │          │ │            │               │
│  │    Sync    │ │          │ │            │               │
│  └─────────────┘ └──────────┘ └────────────┘               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     DATA LAYER                               │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐  │
│  │  PostgreSQL  │ │  Club Spec   │ │  Pricing Cache      │  │
│  │  (Users,     │ │  Database    │ │  (Redis or          │  │
│  │   Sessions,  │ │  (SQLite or  │ │   scheduled         │  │
│  │   Swing Data)│ │   Postgres)  │ │   scrape/API)       │  │
│  └──────────────┘ └──────────────┘ └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Stack:**
- Backend: Python / FastAPI (consistent with Danny's existing stack)
- Frontend: React (Vite) — mobile-first, could wrap in Capacitor later for native
- Database: PostgreSQL (users, sessions, swing data) + SQLite or Postgres table for club specs
- Hosting: Start on Railway or Render for speed; migrate to Databricks Apps later if needed
- Auth: Supabase Auth or simple JWT to start

---

## Phase 0: Foundation & Data (Weeks 1–3)

This phase is about building the data asset that makes everything else possible. Without a club spec database, there's no fitting engine.

### 0.1 — Project Scaffolding

```
swingfit/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Settings / env vars
│   │   ├── models/              # SQLAlchemy / Pydantic models
│   │   │   ├── user.py
│   │   │   ├── session.py       # A "session" = one range visit
│   │   │   ├── shot.py          # Individual shot data
│   │   │   ├── club_spec.py     # Club specifications database
│   │   │   └── recommendation.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── ingest.py        # Upload / parse swing data
│   │   │   ├── fitting.py       # Recommendation engine
│   │   │   ├── clubs.py         # Club database CRUD
│   │   │   └── affiliate.py     # Purchase link routing
│   │   ├── services/
│   │   │   ├── parsers/         # One parser per launch monitor format
│   │   │   │   ├── trackman/    # Trackman-specific (priority integration)
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── stroke_file.py    # .tsf file parser (TPS export)
│   │   │   │   │   ├── csv_export.py     # TPS table view CSV export
│   │   │   │   │   ├── range_api.py      # Trackman Range API client (WebSocket + REST)
│   │   │   │   │   ├── tm4_bridge.py     # Trackman 4 TCP/IP local bridge
│   │   │   │   │   ├── swingsync.py      # SwingSync intermediary CSV import
│   │   │   │   │   └── pdf_report.py     # OCR parser for Trackman PDF reports
│   │   │   │   ├── garmin_r10.py
│   │   │   │   ├── rapsodo.py
│   │   │   │   ├── fullswing_kit.py
│   │   │   │   └── generic_csv.py
│   │   │   ├── trackman_range_client.py  # Trackman Range API session manager
│   │   │   ├── fitting_engine.py
│   │   │   ├── club_lookup.py
│   │   │   └── affiliate_router.py
│   │   └── utils/
│   ├── tests/
│   ├── alembic/                 # DB migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── api/
│   └── package.json
├── data/
│   ├── club_specs/              # Raw club spec data (CSV/JSON)
│   └── sample_sessions/        # Test swing data files
├── scripts/
│   ├── scrape_club_specs.py     # Build the club database
│   └── seed_db.py
├── .env
├── docker-compose.yml
└── README.md
```

**Claude Code instructions:**
1. Initialize the FastAPI project with the directory structure above
2. Set up `docker-compose.yml` with PostgreSQL and the FastAPI app
3. Create the SQLAlchemy models (see 0.2 and 0.3 below for schemas)
4. Set up Alembic for migrations
5. Create a basic health check endpoint at `GET /`
6. Use `python-dotenv` for config management

### 0.2 — Club Specification Database

This is the core data asset. Each club model needs these fields:

```python
# models/club_spec.py

class ClubSpec(Base):
    __tablename__ = "club_specs"

    id = Column(Integer, primary_key=True)

    # Identity
    brand = Column(String)              # "TaylorMade", "Callaway", "Titleist", etc.
    model_name = Column(String)         # "Stealth 2 Plus"
    model_year = Column(Integer)        # 2023
    club_type = Column(String)          # "driver", "iron", "hybrid", "fairway", "wedge", "putter"

    # Specifications
    loft = Column(Float)                # degrees — e.g., 9.0, 10.5 for drivers
    lie_angle = Column(Float)           # degrees
    shaft_options = Column(JSON)        # list of compatible stock shafts
    head_weight = Column(Float)         # grams
    adjustable = Column(Boolean)        # hosel adjustability
    loft_range_min = Column(Float)      # if adjustable, min loft
    loft_range_max = Column(Float)      # if adjustable, max loft

    # Performance profile (from OEM data / fitting databases)
    launch_bias = Column(String)        # "low", "mid", "high"
    spin_bias = Column(String)          # "low", "mid", "high"
    forgiveness_rating = Column(Integer) # 1-10 scale
    workability_rating = Column(Integer) # 1-10 scale

    # Swing speed suitability ranges
    swing_speed_min = Column(Float)     # mph — lower bound of ideal range
    swing_speed_max = Column(Float)     # mph — upper bound of ideal range

    # Market data
    msrp = Column(Float)
    avg_used_price = Column(Float)      # updated periodically
    affiliate_url_template = Column(String)  # parameterized URL

    # Metadata
    still_in_production = Column(Boolean)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

**Data sourcing strategy (in priority order):**
1. **Manual seed first** — Start with the top 50 most popular club models across drivers, irons, and wedges from the last 3 years (TaylorMade, Callaway, Titleist, Ping, Cobra). This is ~150 SKUs. Enter specs from OEM websites. This is enough to build and test the engine.
2. **Scrape OEM spec pages** — Write scrapers for each major brand's product pages. Specs are publicly available. Store raw HTML + parsed data.
3. **Used pricing** — Scrape GlobalGolf, 2nd Swing, Callaway Pre-Owned for average used prices. Run weekly.
4. **Long-term** — Build relationships with OEMs for spec data feeds. Consider purchasing data from golf industry data providers.

**Claude Code instructions:**
1. Create the `ClubSpec` model and run migration
2. Create a `scripts/seed_clubs.py` that reads from a CSV file (`data/club_specs/initial_seed.csv`) and populates the database
3. Create the initial seed CSV with at least 10 drivers, 5 iron sets, and 5 wedge models with realistic spec data
4. Create CRUD endpoints: `GET /clubs`, `GET /clubs/{id}`, `GET /clubs/search?brand=&type=&year=`
5. Add filtering by club_type, brand, swing_speed range, launch_bias, spin_bias

### 0.3 — Swing Data Models

```python
# models/session.py

class SwingSession(Base):
    __tablename__ = "swing_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Session metadata
    session_date = Column(DateTime)
    launch_monitor_type = Column(String)   # "trackman_4", "trackman_range", "garmin_r10", "rapsodo_mlm2", "fullswing_kit", "manual"
    location = Column(String, nullable=True)  # "range", "course", "indoor", "trackman_range_facility"

    # Trackman-specific metadata
    trackman_session_id = Column(String, nullable=True)    # ID from Trackman Range API or MyTrackman
    trackman_facility_name = Column(String, nullable=True) # e.g., "GOLFTEC Chicago", "Trackman Range - Scottsdale"
    trackman_bay_id = Column(String, nullable=True)        # Bay ID for Trackman Range sessions

    # Data quality indicator
    data_source = Column(String)           # "api_realtime", "api_post_session", "file_upload", "manual_entry"

    # File reference
    source_file_name = Column(String, nullable=True)
    source_file_hash = Column(String, nullable=True)  # dedupe uploads

    created_at = Column(DateTime)


# models/shot.py

class Shot(Base):
    __tablename__ = "shots"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("swing_sessions.id"))

    # What club was used for this shot
    club_used = Column(String)             # "driver", "7-iron", "PW", etc.
    club_brand = Column(String, nullable=True)
    club_model = Column(String, nullable=True)

    # Ball data
    ball_speed = Column(Float)             # mph
    launch_angle = Column(Float)           # degrees
    spin_rate = Column(Float)              # rpm (total spin)
    spin_axis = Column(Float, nullable=True) # degrees — tilt
    carry_distance = Column(Float)         # yards
    total_distance = Column(Float, nullable=True)

    # Club data (not all monitors provide all of these)
    club_speed = Column(Float, nullable=True)     # mph
    smash_factor = Column(Float, nullable=True)
    attack_angle = Column(Float, nullable=True)   # degrees
    club_path = Column(Float, nullable=True)       # degrees
    face_angle = Column(Float, nullable=True)      # degrees
    face_to_path = Column(Float, nullable=True)    # degrees

    # Dispersion
    offline_distance = Column(Float, nullable=True)  # yards left(-) / right(+)
    apex_height = Column(Float, nullable=True)        # feet

    # Trackman-specific extended data (not available from all monitors)
    landing_angle = Column(Float, nullable=True)       # degrees — from Trackman
    dynamic_loft = Column(Float, nullable=True)        # degrees — from Trackman
    spin_loft = Column(Float, nullable=True)           # degrees — from Trackman (launch_angle + attack_angle)
    hang_time = Column(Float, nullable=True)           # seconds — from Trackman Range API
    last_data_distance = Column(Float, nullable=True)  # yards — how far Trackman tracked the ball

    # Quality flag
    is_valid = Column(Boolean, default=True)  # can be flagged as mishit

    shot_number = Column(Integer)  # order within session
```

**Claude Code instructions:**
1. Create the `SwingSession` and `Shot` models, run migrations
2. Create `POST /sessions` endpoint that accepts session metadata
3. Create `POST /sessions/{id}/shots` for adding individual shots
4. Create `GET /sessions/{id}/summary` that returns aggregated stats per club (avg ball speed, avg carry, avg spin, avg launch angle, dispersion metrics)
5. Create `GET /users/{id}/profile` that returns career averages across all sessions, grouped by club type

---

## Phase 1: Ingest Pipeline — Trackman First (Weeks 3–7)

Trackman is the primary integration. Every other launch monitor is a secondary ingest path. The pipeline needs to handle multiple Trackman data pathways since Trackman doesn't offer a single clean consumer API — you have to meet the data where it lives.

### Trackman Data Landscape

There are four distinct ways to get data out of Trackman, each with different access models, data richness, and integration complexity:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TRACKMAN DATA PATHWAYS                            │
│                                                                     │
│  PATH 1: Trackman Range API (Commercial Facilities)                 │
│  ├── Access: REST + WebSocket, documented at docs.trackmanrange.com │
│  ├── Data: Real-time ball flight, launch data, trajectory polys     │
│  ├── Auth: Facility-level credentials                               │
│  ├── Richness: ★★★★★ (real-time, full trajectory)                  │
│  └── Effort: Medium (need Trackman Range partnership)               │
│                                                                     │
│  PATH 2: Trackman 4 Direct TCP/IP (Private Owners / Sim Bays)      │
│  ├── Access: Local network socket API                               │
│  ├── Data: Full club + ball data per shot                           │
│  ├── Auth: Local network only — needs companion app/bridge          │
│  ├── Richness: ★★★★★ (richest data including full club delivery)   │
│  └── Effort: High (desktop bridge app, local network discovery)     │
│                                                                     │
│  PATH 3: File Export (TPS → CSV/TSF, SwingSync intermediary)        │
│  ├── Access: User exports from Trackman Performance Studio          │
│  ├── Data: All measured parameters per shot                         │
│  ├── Auth: None — user just uploads the file                        │
│  ├── Richness: ★★★★ (full data, but post-session only)             │
│  └── Effort: Low (just build parsers)                               │
│                                                                     │
│  PATH 4: Trackman PDF/Screenshot Reports (Universal Fallback)       │
│  ├── Access: User takes screenshot or saves PDF from TPS/app        │
│  ├── Data: Aggregated averages, sometimes per-shot tables           │
│  ├── Auth: None                                                     │
│  ├── Richness: ★★★ (summarized, not raw shot data)                 │
│  └── Effort: Medium (OCR / structured extraction)                   │
│                                                                     │
│  PATH 5: MyTrackman.com / Trackman Golf App (Consumer Cloud)        │
│  ├── Access: No official API — data is locked in the app            │
│  ├── Data: Session history, shot data viewable but not exportable   │
│  ├── Auth: N/A — no programmatic access                             │
│  ├── Richness: ★★★★ (full data exists, just can't get to it)       │
│  └── Effort: N/A until Trackman opens an API or partnership         │
│                                                                     │
│  BUILD PRIORITY:  Path 3 → Path 4 → Path 1 → Path 2 → Path 5      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.1 — Trackman File Parsers (Priority 1 — Fastest Path to Trackman Data)

**Why first:** Every Trackman user can export data this way today with zero partnership or API access needed. This is the MVP Trackman integration.

#### 1.1a — Trackman Performance Studio (TPS) CSV Export

From TPS, users can go to Analyze → Table View → Export. This produces a CSV with all measured parameters.

**Claude Code instructions:**
1. Create `services/parsers/trackman/csv_export.py`
2. Map all Trackman column headers to the `Shot` schema
3. Handle unit variations: Trackman can export in metric or imperial. Detect from headers and convert to imperial internally.
4. Handle "N/A" or blank cells
5. Auto-detect club type from the "Club" column
6. Set `launch_monitor_type = "trackman_4"` and `data_source = "file_upload"`

#### 1.1b — Trackman Stroke File (.tsf) Parser

Users can also export from TPS as a "TrackMan Stroke File" (.tsf) — this is Trackman's proprietary XML-based format.

**Claude Code instructions:**
1. Create `services/parsers/trackman/stroke_file.py`
2. Parse the XML structure
3. Map to the `Shot` schema using the same field mapping as the CSV parser

#### 1.1c — SwingSync CSV Import

SwingSync (swingsync.com) positions itself as a "Strava for golf sims" and can import Trackman session data and export it as CSV.

**Claude Code instructions:**
1. Create `services/parsers/trackman/swingsync.py`
2. Parse SwingSync's CSV export format (different column headers than TPS)

### 1.2 — Trackman Report OCR (Priority 2 — Biggest User Base Unlock)

**Why this is Priority 2:** Most golfers who use Trackman don't have access to TPS export. They take a GOLFTEC lesson and walk away with a PDF report or screenshot. This is the largest segment of Trackman users by far.

**Technical approach — use Claude's Vision API:**

```python
# services/parsers/trackman/report_vision.py

class TrackmanReportParser:
    """Uses Claude's vision API to extract swing data from Trackman reports."""

    def extract_from_image(self, image_bytes: bytes, media_type: str) -> dict:
        """Extract swing data from a Trackman screenshot or photo."""
        pass

    def extract_from_pdf(self, pdf_bytes: bytes) -> dict:
        """Extract swing data from a Trackman PDF report."""
        pass
```

**Claude Code instructions:**
1. Create `services/parsers/trackman/report_vision.py` with the Claude Vision API integration
2. Create `POST /ingest/trackman-report` endpoint
3. Show extracted data in an editable form BEFORE saving
4. Store the original image/PDF as a reference
5. If extraction confidence < 0.7, show a warning

### 1.3 — Trackman Range API Integration (Priority 3 — Post-MVP)

The Trackman Range API (docs.trackmanrange.com) enables real-time data capture at facilities.

**Claude Code instructions:**
1. Create `services/trackman_range_client.py` — WebSocket + REST client
2. Build unit conversion utility (Range API uses metric)
3. **Partnership required** — build against documented API, test with simulated data

### 1.4 — Trackman 4 Direct Bridge (Priority 4 — Phase 5+)

Trackman 4 TCP/IP socket API on local network. Requires a companion bridge app.

### 1.5 — Garmin R10 Parser

Garmin R10 data exported from the Garmin Golf app as CSV.

**Claude Code instructions:**
1. Create `services/parsers/garmin_r10.py`
2. Parse CSV, map column headers to `Shot` fields
3. Flag outlier shots as `is_valid = False`

### 1.6 — Generic CSV Parser

Fallback for all other launch monitors (Rapsodo, Full Swing KIT, SkyTrak, Uneekor, FlightScope).

**Claude Code instructions:**
1. Create `services/parsers/generic_csv.py`
2. Build a header fuzzy matcher using a synonym dictionary
3. Create `POST /ingest/upload` endpoint with auto-detection

### 1.7 — Manual Entry

Simple manual entry form for users who only remember their averages.

### 1.8 — Data Quality Tiering

```python
DATA_QUALITY_TIERS = {
    "trackman_4_file":      {"tier": "platinum", "weight": 1.0},
    "trackman_4_bridge":    {"tier": "platinum", "weight": 1.0},
    "trackman_range_api":   {"tier": "gold",     "weight": 0.85},
    "trackman_report_ocr":  {"tier": "silver",   "weight": 0.7},
    "garmin_r10":           {"tier": "silver",    "weight": 0.7},
    "generic_csv":          {"tier": "bronze",    "weight": 0.5},
    "manual_entry":         {"tier": "bronze",    "weight": 0.3},
}
```

### 1.9 — MVP User Journey Flows

```
SCENARIO 1: GOLFTEC / Lesson Customer (OCR path) — ~90 seconds
SCENARIO 2: Sim Bay / Fitting Studio (CSV export) — ~60 seconds
SCENARIO 3: Garmin R10 Owner (CSV export) — ~60 seconds
SCENARIO 4: "I Know My Numbers" (Manual entry) — ~3 minutes
```

---

## Phase 2: Fitting Engine (Weeks 5–8)

This is the core IP. The engine takes a user's swing profile and recommends optimal equipment.

### 2.1 — User Swing Profile

Compute the user's swing profile from their shot data using `compute_swing_profile()`.

### 2.2 — Playwright Data Scrapers (Automated Club Database Population)

Instead of manually entering club specs, use Playwright to scrape OEM sites, retailers, and review sites on a schedule. This keeps the club database comprehensive and current without manual work.

**Architecture:**
```
PLAYWRIGHT SCRAPERS (scheduled — daily for prices, weekly for specs)
    │
    ├── OEM Scrapers → club specs, lofts, shaft options, MSRP
    │   ├── taylormadegolf.com        (drivers, irons, wedges, fairways, hybrids)
    │   ├── callawaygolf.com          (drivers, irons, wedges, fairways, hybrids)
    │   ├── titleist.com              (drivers, irons, wedges, fairways, hybrids)
    │   ├── ping.com                  (drivers, irons, wedges, fairways, hybrids)
    │   ├── cobragolf.com             (drivers, irons, wedges, fairways, hybrids)
    │   ├── mizunogolf.com            (primarily irons + wedges)
    │   ├── clevelandgolf.com         (wedges + putters primarily)
    │   ├── srixon.com                (drivers, irons — same parent as Cleveland)
    │   ├── pxg.com                   (full line, premium DTC)
    │   ├── honmagolf.com             (Japanese luxury, growing U.S. presence)
    │   └── touredge.com              (value/game-improvement, popular with seniors)
    │
    ├── Retailer Scrapers → current pricing, availability, used prices
    │   ├── globalgolf.com
    │   ├── 2ndswing.com
    │   ├── callawaygolfpreowned.com
    │   └── amazon.com (golf clubs category)
    │
    ├── Review Scrapers → performance characteristics, editorial descriptions
    │   ├── mygolfspy.com (most data-driven reviews)
    │   ├── golfdigest.com/hot-list
    │   └── golfwrx.com/reviews
    │
    ▼
CLUB DATABASE (Supabase — always fresh, hundreds of clubs)
    │
    ▼
CLAUDE API (called per-user when they upload swing data)
    │
    ├── Input: user's swing profile + relevant clubs from database
    ├── Output: top 5 recommendations with match scores + explanations
    ▼
RECOMMENDATIONS (cached in Supabase, displayed on Shop page)
```

**Phased rollout:**

- **Phase 1 (built):** Top 5 brands — TaylorMade, Callaway, Titleist, Ping, Cobra — drivers only. GlobalGolf + 2nd Swing pricing. MyGolfSpy reviews.
- **Phase 2 (next sprint):** Add Mizuno, Cleveland/Srixon, PXG, Honma, Tour Edge. Expand all brands to full club categories (irons, wedges, fairways, hybrids, putters).
- **Phase 3:** Additional review sources (Golf Digest, GolfWRX). Additional retailer pricing (Callaway Pre-Owned, Amazon).

**Claude Code instructions:**
1. Install Playwright: `pip install playwright && playwright install chromium`
2. Create `scripts/scrapers/` directory with one scraper per OEM/retailer/review site
3. Each OEM scraper extracts at minimum: brand, model_name, model_year, club_type, loft, msrp, shaft_options, adjustable, key technology
4. Create `scripts/scrapers/run_all.py` orchestrator with error handling per scraper
5. Add rate limiting (2-3s delays), User-Agent rotation, scrape logging

### 2.3 — Claude API Recommendation Engine (Replaces Static Scoring)

Instead of a hand-coded scoring formula, the recommendation engine sends the user's swing profile + the club database to Claude's API and gets back intelligent, contextual recommendations.

**Why this is better than a static scoring algorithm:**
- Claude understands fitting nuances impossible to capture in a formula
- Editorial-quality explanations come naturally
- As Claude improves, recommendations automatically get better
- Can recommend full builds (head + shaft + specs) like Club Champion

**The recommendation flow:**

```
User uploads Trackman data
    → compute SwingProfile (math — stays as-is)
    → hard-filter clubs by type, speed range, budget
    → send profile + candidates to Claude API (claude-sonnet-4-20250514)
    → Claude returns top 5 with scores, explanations, projected changes
    → cache in recommendations table
    → frontend reads from cache (fast, no API call)
```

**Caching:** Only re-generate when user uploads new data, changes preferences, or club database refreshes.

**Cost tracking:** Log each Claude API call to `api_usage` table.

**Endpoints:**
- `POST /fitting/recommend` — triggers Claude API recommendation generation
- `GET /fitting/recommendations` — reads cached recommendations (fast)
- `POST /fitting/compare` — Claude side-by-side comparison of two clubs

### 2.4 — Comparison Mode

Send two clubs + user profile to Claude for side-by-side analysis with projected performance changes.

---

## Phase 3: Affiliate & Purchase Layer (Weeks 8–10)

### 3.1 — Affiliate Link Router

Route users to retailers with affiliate tags. Current configs: GlobalGolf (CJ, 8%), 2nd Swing (ShareASale, 7%), Callaway Pre-Owned (Partnerize, 6%), TaylorMade (Sovrn, 5%), Amazon (Associates, 4%).

### 3.2 — Price Caching (Powered by Playwright Scrapers)

Prices scraped by Playwright and cached. Frontend reads from cache, never hits retailer sites directly. Staleness check for prices older than 48 hours.

---

## Phase 4: Frontend (Weeks 8–12, parallel with Phase 3)

### 4.1 — Pages & User Flow

```
Landing Page → Sign Up / Login → Dashboard
    ├── Upload Session (OCR / CSV / Manual)
    ├── My Bag (current clubs + performance)
    ├── Get Fitted (recommendations with Claude explanations)
    └── Settings (profile, budget, units)
```

### 4.2 — Key UI Components

Recommendation cards with match scores, editorial explanations, buy links, and comparison toggles. Swing profile summary with data quality badges.

---

## Phase 5: Polish & Launch (Weeks 12–16)

### 5.1 — Additional Parsers & Trackman Expansion
### 5.2 — Subscription & Paywall (Free tier + Pro at $7.99/mo)
### 5.3 — New Club Alerts (Retention Feature)
### 5.4 — SEO / Content (Auto-generated club landing pages)

---

## Phase 6: B2B Licensing (Months 6+)

White-label the fitting engine for independent club fitters, pro shops, and launch monitor companies.

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend language | Python/FastAPI | Danny's existing expertise, fast iteration, numpy for stats |
| Database | PostgreSQL | Relational data, good for analytics queries on shot data |
| Frontend | React (Vite) | Modern, fast, huge ecosystem, easy Capacitor wrap later |
| Auth | Supabase Auth | Simple, handles social login |
| Payments | Stripe | Industry standard subscription management |
| Recommendations | Claude API (Sonnet) | Better than static scoring, editorial explanations |
| Club data | Playwright scrapers | Automated, always fresh, 11 brands planned |
| Affiliate tracking | Custom + network SDKs | CJ, ShareASale, Partnerize, Amazon Associates |

---

## MVP Definition

1. ✅ Upload Trackman report via screenshot/PDF (Claude Vision OCR)
2. ✅ Upload Trackman/Garmin CSV
3. ✅ Manual entry fallback
4. ✅ Editable confirmation step for OCR data
5. ✅ Swing profile summary with data quality tier
6. ✅ Top 5 driver recommendations with Claude explanations
7. ✅ Buy links (affiliate links to GlobalGolf, 2nd Swing)
8. ✅ User accounts with session history

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Club spec data hard to source at scale | High | High | Start with top 50 manually; Playwright scrapers for scale |
| Trackman Range API access denied | High | High | MVP works on file uploads alone |
| Launch monitor APIs don't exist / change | High | Medium | Build on CSV export (universal) |
| Low conversion on affiliate links | Medium | Medium | Stack with subscription revenue |
| Existing competitors copy approach | Medium | Low | Speed to market + data flywheel |
