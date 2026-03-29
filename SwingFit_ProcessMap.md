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

From TPS, users can go to Analyze → Table View → Export. This produces a CSV with all measured parameters. The columns include Trackman's full data set:

```
Club,Club Speed (mph),Attack Angle (deg),Club Path (deg),Face Angle (deg),Face to Path (deg),Ball Speed (mph),Smash Factor,Launch Angle (deg),Launch Direction (deg),Spin Rate (rpm),Spin Axis (deg),Carry (yd),Carry Side (yd),Total (yd),Total Side (yd),Apex Height (ft),Landing Angle (deg)
Driver,105.2,-1.2,2.1,0.8,-1.3,149.8,1.42,12.3,-0.5,2845,3.2,248,8,271,12,98,38.5
Driver,107.1,-0.8,1.5,0.3,-1.2,151.0,1.41,11.8,-0.2,2650,2.1,255,4,278,6,95,37.2
```

**Trackman provides significantly richer data than consumer monitors:**
- Full club delivery data (attack angle, club path, face angle, face to path, dynamic loft)
- Spin axis (not just total spin — tells you draw/fade spin)
- Landing angle (helps assess trajectory optimization)
- Carry side distance (precise dispersion, not estimated)

**Claude Code instructions:**
1. Create `services/parsers/trackman/csv_export.py`
2. Map all Trackman column headers to the `Shot` schema. Key mappings:
   - "Club Speed (mph)" → `club_speed`
   - "Attack Angle (deg)" → `attack_angle`
   - "Club Path (deg)" → `club_path`
   - "Face Angle (deg)" → `face_angle`
   - "Face to Path (deg)" → `face_to_path`
   - "Spin Axis (deg)" → `spin_axis`
   - "Carry Side (yd)" → `offline_distance`
   - "Apex Height (ft)" → `apex_height`
   - "Landing Angle (deg)" → store in new Shot field `landing_angle`
3. Handle unit variations: Trackman can export in metric (mps, meters) or imperial (mph, yards). Detect from headers and convert to imperial internally.
4. Handle "N/A" or blank cells — Trackman leaves fields empty when it can't measure (e.g., sometimes misses spin on a topped shot)
5. Auto-detect club type from the "Club" column — Trackman uses: "Driver", "3 Wood", "5 Wood", "4 Hybrid", "5 Iron" through "PW", "GW", "SW", "LW"
6. Set `launch_monitor_type = "trackman_4"` and `data_source = "file_upload"`

#### 1.1b — Trackman Stroke File (.tsf) Parser

Users can also export from TPS as a "TrackMan Stroke File" (.tsf) — this is Trackman's proprietary format, typically saved to USB. The .tsf file is an XML-based format.

**Claude Code instructions:**
1. Create `services/parsers/trackman/stroke_file.py`
2. Parse the XML structure — each stroke contains the same data fields as the CSV but in XML nodes
3. Map to the `Shot` schema using the same field mapping as the CSV parser
4. Extract session metadata from the file header (date, location, player name if present)
5. Set `launch_monitor_type = "trackman_4"` and `data_source = "file_upload"`

#### 1.1c — SwingSync CSV Import (Intermediary for Trackman Users)

SwingSync (swingsync.com) positions itself as a "Strava for golf sims" and can import Trackman session data and export it as CSV. For users who already use SwingSync, this is the easiest path.

**Claude Code instructions:**
1. Create `services/parsers/trackman/swingsync.py`
2. Parse SwingSync's CSV export format (different column headers than TPS)
3. Map to the `Shot` schema
4. Set `launch_monitor_type = "trackman_4"` (original source) and `data_source = "file_upload"`

### 1.2 — Trackman Report OCR (Priority 2 — Biggest User Base Unlock)

**Why this is Priority 2, right after file parsers:** Most golfers who use Trackman don't have access to TPS export. They take a GOLFTEC lesson, the coach controls the computer, and the golfer walks away with either a PDF report emailed to them or their session data visible in the Trackman Golf app (which has no export). This is the largest segment of Trackman users by far — casual-to-serious golfers who pay for lessons and fittings but don't own a Trackman. If they can just screenshot their app or forward their PDF report, you've unlocked 10x the addressable market compared to file export alone.

**What users actually have in hand after a Trackman session:**

1. **Trackman Golf App screenshots** — The app shows session data in a clean card-style layout with stats per club. Users screenshot this all the time to share on social media or text to friends. Standard format, consistent layout.

2. **Emailed PDF reports** — Coaches and fitting studios email summary reports. These are formatted PDFs with tables showing averages and sometimes per-shot data. Trackman has standard report templates.

3. **Trackman Combine reports** — Popular standardized test that outputs a scorecard-style PDF with distances per club.

4. **Photos of the TPS screen** — Some users just snap a photo of the monitor with their phone before walking away.

**Common Trackman report/app data layout:**

```
┌─────────────────────────────────────────────────────┐
│  DRIVER — Session Summary                            │
│                                                     │
│  Club Speed    105.2 mph    Attack Angle   -1.2°    │
│  Ball Speed    149.8 mph    Club Path       2.1°    │
│  Smash Factor    1.42       Face Angle      0.8°    │
│  Launch Angle   12.3°       Face to Path   -1.3°    │
│  Spin Rate     2845 rpm     Spin Axis       3.2°    │
│  Carry          248 yd      Carry Side      8 yd    │
│  Total          271 yd      Landing Angle  38.5°    │
│  Apex Height     98 ft                              │
└─────────────────────────────────────────────────────┘
```

**Technical approach — use Claude's Vision API, not traditional OCR:**

Traditional OCR (pytesseract) works for clean PDFs but struggles with phone photos of screens (glare, angles, varying lighting). Claude's vision API is a much better fit here — it can interpret the layout, understand what the numbers mean in context, and handle messy real-world images.

```python
# services/parsers/trackman/report_vision.py

import anthropic

class TrackmanReportParser:
    """
    Uses Claude's vision API to extract swing data from Trackman 
    reports, screenshots, and photos.
    """
    
    EXTRACTION_PROMPT = """
    Analyze this Trackman golf report/screenshot and extract all swing data.
    
    Return a JSON object with this exact structure:
    {
        "clubs": [
            {
                "club_type": "driver",
                "shots": 24,
                "averages": {
                    "club_speed": 105.2,
                    "ball_speed": 149.8,
                    "launch_angle": 12.3,
                    "spin_rate": 2845,
                    "carry_distance": 248,
                    "total_distance": 271,
                    "attack_angle": -1.2,
                    "club_path": 2.1,
                    "face_angle": 0.8,
                    "face_to_path": -1.3,
                    "spin_axis": 3.2,
                    "apex_height": 98,
                    "landing_angle": 38.5,
                    "offline_distance": 8,
                    "smash_factor": 1.42
                }
            }
        ],
        "data_type": "session_summary" | "combine_report" | "per_shot_table",
        "source": "trackman_app_screenshot" | "pdf_report" | "tps_photo",
        "confidence": 0.95
    }
    
    Rules:
    - All speeds in mph, distances in yards, heights in feet, angles in degrees, spin in rpm
    - If units are metric (m/s, meters), convert to imperial
    - If a value is not visible or unreadable, set to null
    - If you can see per-shot data (not just averages), include each shot separately
    - Set confidence to how sure you are the extraction is accurate (0.0 to 1.0)
    - Only return valid JSON, no other text
    """
    
    def __init__(self):
        self.client = anthropic.Anthropic()
    
    async def extract_from_image(self, image_bytes: bytes, media_type: str) -> dict:
        """Extract swing data from a Trackman screenshot or photo."""
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64.b64encode(image_bytes).decode()
                        }
                    },
                    {
                        "type": "text",
                        "text": self.EXTRACTION_PROMPT
                    }
                ]
            }]
        )
        
        # Parse the JSON response
        result = json.loads(response.content[0].text)
        return result
    
    async def extract_from_pdf(self, pdf_bytes: bytes) -> dict:
        """Extract swing data from a Trackman PDF report."""
        # Convert PDF pages to images, then run vision extraction on each page
        pass
```

**Claude Code instructions:**
1. Create `services/parsers/trackman/report_vision.py` with the Claude Vision API integration
2. Create `POST /ingest/trackman-report` endpoint that accepts:
   - Image uploads (PNG, JPG) — screenshots and photos
   - PDF uploads — emailed reports
3. Run the vision extraction, return the parsed data to the frontend
4. **Critical UX step:** Show the extracted data to the user in an editable form BEFORE saving:
   ```
   We extracted this from your Trackman report:
   
   DRIVER (24 shots)
   Club Speed: [105.2] mph     ← editable field
   Ball Speed: [149.8] mph     ← editable field  
   Launch:     [12.3]  °       ← editable field
   Spin:       [2845]  rpm     ← editable field
   Carry:      [248]   yd      ← editable field
   ...
   
   [Looks right — Save]  [Let me fix something]
   ```
5. Once confirmed, create the `SwingSession` + `Shot` records with `data_source = "ocr_vision"` and `launch_monitor_type = "trackman_4"`
6. Store the original image/PDF as a reference (S3 or local storage) so you can re-process later if the extraction pipeline improves
7. If extraction confidence < 0.7, show a warning: "We're not fully confident in some of these numbers — please double-check"

**Cost consideration:** Claude Vision API calls cost money. At ~$0.01-0.03 per image, this is negligible at MVP scale. At 10K+ reports/month, consider caching common report templates or building a specialized fine-tuned model.

### 1.3 — Trackman Range API Integration (Priority 3 — Real-Time at Facilities, Post-MVP)

The Trackman Range API (docs.trackmanrange.com) is the path to real-time data capture at Trackman Range facilities. This is the highest-value integration because it creates a seamless experience: user walks up to a Trackman Range bay, opens SwingFit on their phone, hits balls, and recommendations update live.

**How the Trackman Range API works:**

```
┌──────────────┐    WebSocket     ┌──────────────┐    REST API    ┌──────────────┐
│  Trackman    │ ──────────────── │  SwingFit    │ ──────────────│  Trackman    │
│  Range Unit  │  (real-time     │  Backend     │  (session     │  Range       │
│  (at bay)    │   shot data)    │              │   mgmt)       │  Cloud       │
└──────────────┘                 └──────────────┘               └──────────────┘
```

**The API provides three message types per shot:**
1. **Launch Data** — Sent at impact: ball speed, launch angle, launch direction
2. **Live Measurement** — Sent during flight: trajectory position updates (x,y,z at time t)
3. **Final Measurement** — Sent after ball stops: carry, total, max height, carry side, all final values

**Data fields available from the Range API:**
- BallSpeed (in m/s — must convert to mph)
- LaunchAngle, LaunchDirection
- Carry, CarryActual, CarrySide, CarrySideActual
- MaxHeight
- TargetDistance
- Full trajectory as polynomial coefficients (expandable to position arrays)
- BayId (which bay the shot came from)

**Important limitation:** The Trackman Range API provides ball flight data but does NOT include club delivery data (club speed, attack angle, face angle, club path). This is because Range units are overhead-mounted and optimized for ball tracking, not club measurement. For fitting purposes, this means Range API data is good for ball flight optimization but not as rich as Trackman 4 data for club delivery analysis.

**Claude Code instructions:**
1. Create `services/trackman_range_client.py` — a WebSocket + REST client:
   ```python
   class TrackmanRangeClient:
       """
       Manages connection to Trackman Range API.
       
       Flow:
       1. Authenticate with facility credentials
       2. Start a player session on a specific bay
       3. Open WebSocket connection for real-time shot data
       4. Receive Launch → Live → Final measurement messages
       5. Normalize Final measurements into Shot records
       6. Close session when user is done
       """
       
       def __init__(self, facility_host: str, auth_token: str):
           self.base_url = f"https://{facility_host}"
           self.ws_url = f"wss://{facility_host}/ws"
           self.auth_token = auth_token
       
       async def start_session(self, bay_id: str, user_id: int) -> str:
           """Start a player session on a bay. Returns session_id."""
           pass
       
       async def connect_websocket(self, session_id: str):
           """Open WebSocket and start receiving shot data."""
           pass
       
       async def on_final_measurement(self, measurement: dict) -> Shot:
           """
           Called when a Final Measurement arrives.
           Convert Trackman Range units to our Shot schema:
           - BallSpeed: m/s → mph (multiply by 2.237)
           - Carry: meters → yards (multiply by 1.094)
           - MaxHeight: meters → feet (multiply by 3.281)
           - CarrySide: meters → yards (multiply by 1.094)
           """
           pass
       
       async def end_session(self, session_id: str):
           """Close the player session."""
           pass
   ```
2. Create `services/parsers/trackman/range_api.py` — the normalizer that converts Range API measurements into `Shot` objects
3. Create `POST /trackman/start-session` endpoint — user provides facility code + bay number, backend establishes connection
4. Create `WebSocket /trackman/live` endpoint — frontend connects here to show real-time shot data as the user hits
5. Create `POST /trackman/end-session` endpoint — closes connection, triggers fitting engine on the collected session data
6. **Unit conversion is critical:** Range API uses metric (m/s, meters). All internal storage is imperial (mph, yards, feet). Build a `trackman_unit_converter.py` utility.

**Partnership requirement:** To access the Range API, you need to register as a Trackman Range integration partner. This requires outreach to Trackman. For MVP, build the client code against their documented API and test with simulated data. Apply for partnership credentials once you have a working product to demo.

### 1.4 — Trackman 4 Direct Bridge (Priority 4 — Power Users with Own Units, Phase 5+)

Trackman 4 hardware exposes a TCP/IP socket API on the local network. This provides the richest data (full club + ball) in real-time, but requires a companion bridge app running on the same network as the Trackman unit.

**How it works:**
```
┌──────────────┐  TCP/IP Socket  ┌──────────────┐    HTTPS     ┌──────────────┐
│  Trackman 4  │ ──────────────  │  SwingFit    │ ──────────── │  SwingFit    │
│  (local      │  (club + ball   │  Bridge App  │  (forwards   │  Cloud       │
│   network)   │   data per shot)│  (Desktop)   │   shot data) │  Backend     │
└──────────────┘                 └──────────────┘              └──────────────┘
```

The bridge app is a lightweight desktop application (Electron or Python + tkinter) that:
1. Discovers the Trackman 4 on the local network
2. Connects via TCP/IP socket
3. Arms the Trackman to start tracking
4. Receives shot data (club speed, attack angle, face angle, club path, face to path, dynamic loft, ball speed, launch angle, spin rate, spin axis, carry, etc.)
5. Forwards each shot to the SwingFit cloud API via HTTPS

**Claude Code instructions:**
1. Create `services/parsers/trackman/tm4_bridge.py` — the TCP/IP client
2. This will be packaged as a standalone desktop app later (Phase 5+)
3. For MVP, build the bridge as a Python CLI script that:
   - Accepts the Trackman's local IP as an argument
   - Connects via socket
   - Receives JSON shot data
   - POSTs to `POST /ingest/trackman-bridge` on the SwingFit API
4. Document the Trackman 4 socket protocol (based on community documentation):
   - Connection: TCP socket to Trackman IP, port TBD (typically discovered via mDNS/Bonjour)
   - Commands: ARM, DISARM, SET_CLUB, GET_STATUS
   - Data: JSON payloads with full club + ball parameters per shot
5. **This is a Phase 5+ build.** For MVP, point Trackman 4 owners to file export (Path 1). The bridge is the long-term premium experience.

### 1.5 — Garmin R10 Parser (Secondary — Largest Consumer Install Base)

Garmin R10 data is exported from the Garmin Golf app as CSV. The format looks roughly like:

```
Club,Ball Speed (mph),Launch Angle (°),Spin Rate (rpm),Carry (yd),Total (yd),Club Speed (mph),Smash Factor,Attack Angle (°),Club Path (°),Face Angle (°)
Driver,148.2,12.3,2845,245,268,105.2,1.41,-1.2,2.1,0.8
Driver,151.0,11.8,2650,252,275,107.1,1.41,-0.8,1.5,0.3
7 Iron,120.5,18.4,6420,165,172,82.3,1.46,-3.2,0.5,-0.2
```

**Claude Code instructions:**
1. Create `services/parsers/garmin_r10.py`
2. Parse the CSV, map column headers to `Shot` fields
3. Handle edge cases: missing columns, different column orderings, units
4. Auto-detect club type from the "Club" column (map "Driver" → "driver", "7 Iron" → "7-iron", "PW" → "PW", etc.)
5. Flag outlier shots as `is_valid = False` (e.g., ball speed < 50 mph for driver = likely a mishit)
6. Return a list of `Shot` Pydantic objects

### 1.6 — Generic CSV Parser (Fallback for All Other Monitors)

For launch monitors we don't have specific parsers for yet (Rapsodo, Full Swing KIT, SkyTrak, Uneekor, FlightScope), build a generic parser that:
1. Accepts a CSV file
2. Presents a column mapping UI (or uses fuzzy matching on column headers)
3. Maps columns to `Shot` fields using common synonyms:
   - "Ball Speed", "BallSpeed", "Ball Spd" → `ball_speed`
   - "Carry", "Carry Distance", "Carry Dist", "Carry (yd)" → `carry_distance`
   - "Total Spin", "Spin Rate", "Spin", "Spin (rpm)" → `spin_rate`
4. Stores the successful mapping so future uploads from the same monitor auto-map

**Claude Code instructions:**
1. Create `services/parsers/generic_csv.py`
2. Build a header fuzzy matcher using a synonym dictionary
3. Create `POST /ingest/upload` endpoint that:
   - Accepts a CSV file upload
   - Auto-detects the launch monitor format (try Trackman CSV first, then Garmin, then Rapsodo, then generic)
   - Parses and creates the `SwingSession` + `Shot` records
   - Returns the session summary
4. Add file hash deduplication — reject duplicate uploads

### 1.7 — Manual Entry

Not everyone will have a CSV export. Build a simple manual entry form where users can type in their averages per club:

```
Club Type: Driver
Avg Club Speed: 105 mph
Avg Ball Speed: 150 mph
Avg Launch Angle: 12.5°
Avg Spin Rate: 2700 rpm
Avg Carry: 250 yd
```

**Claude Code instructions:**
1. Create `POST /ingest/manual` endpoint that accepts aggregated stats (not individual shots)
2. Store as a single "synthetic" shot per club with `launch_monitor_type = "manual"`
3. This is the lowest-fidelity input but captures users who hit balls at a fitting studio and only remember their averages

### 1.8 — Data Quality Tiering

Because Trackman data is significantly richer than consumer monitor data, the fitting engine should weight recommendations by data source quality:

```python
DATA_QUALITY_TIERS = {
    "trackman_4_file":      {"tier": "platinum", "weight": 1.0,  "has_club_data": True,  "has_spin_axis": True},
    "trackman_4_bridge":    {"tier": "platinum", "weight": 1.0,  "has_club_data": True,  "has_spin_axis": True},
    "trackman_range_api":   {"tier": "gold",     "weight": 0.85, "has_club_data": False, "has_spin_axis": False},
    "trackman_report_ocr":  {"tier": "silver",   "weight": 0.7,  "has_club_data": True,  "has_spin_axis": True},
    "garmin_r10":           {"tier": "silver",    "weight": 0.7,  "has_club_data": True,  "has_spin_axis": False},
    "rapsodo_mlm2":         {"tier": "silver",    "weight": 0.7,  "has_club_data": True,  "has_spin_axis": False},
    "fullswing_kit":        {"tier": "silver",    "weight": 0.7,  "has_club_data": True,  "has_spin_axis": True},
    "generic_csv":          {"tier": "bronze",    "weight": 0.5,  "has_club_data": False, "has_spin_axis": False},
    "manual_entry":         {"tier": "bronze",    "weight": 0.3,  "has_club_data": False, "has_spin_axis": False},
}
```

**Claude Code instructions:**
1. Create `services/data_quality.py` with the tiering config above
2. When computing swing profiles, weight shots by their data source tier
3. In the UI, show a data quality badge: "Your driver profile is based on 47 Trackman shots (Platinum quality)" vs "Your driver profile is based on 12 Garmin R10 shots (Silver quality)"
4. When recommending clubs, if the user only has Silver/Bronze data, show a prompt: "For more accurate recommendations, upload your Trackman session data or visit a Trackman Range facility"

### 1.9 — MVP User Journey Flows

These are the actual end-to-end experiences a user will have with SwingFit at MVP launch. Claude Code should build the frontend flows to match these exactly.

```
SCENARIO 1: GOLFTEC / Lesson Customer (Largest segment — OCR path)
──────────────────────────────────────────────────────────────────
Golfer takes a GOLFTEC lesson or fitting on Trackman
    → Coach emails them a PDF summary report, OR
    → Session data appears in their Trackman Golf app
    → Golfer screenshots the app or saves the PDF
    
    → Opens SwingFit → "Upload Trackman Report"
    → Drops in screenshot or PDF
    → Claude Vision extracts all swing data automatically
    → SwingFit shows extracted data in editable form:
      "We found your driver data: 105 mph club speed, 
       149 ball speed, 12.3° launch, 2845 rpm spin..."
    → User confirms or tweaks any misread values → Save
    → Sees swing profile + top 3 driver recommendations
    
    Total extra effort: ~90 seconds
    Data quality: Silver (OCR-extracted averages)

SCENARIO 2: Sim Bay / Fitting Studio Customer (CSV export path)
──────────────────────────────────────────────────────────────────
Golfer hits balls at an indoor sim bay or fitting studio
    → Session ends, TPS has all the shot data
    → Golfer (or staff) exports CSV from TPS:
      Analyze → Table View → Export → Save as CSV
    → Golfer emails it to themselves or saves to phone
    
    → Opens SwingFit → "Upload Session File"
    → Drags-and-drops the CSV
    → Parser auto-detects Trackman format, ingests all shots
    → Sees full swing profile with per-shot data
    → Gets top 3 driver recommendations with explanations
    
    Total extra effort: ~60 seconds
    Data quality: Platinum (raw per-shot Trackman data)

SCENARIO 3: Garmin R10 / Consumer Launch Monitor Owner
──────────────────────────────────────────────────────────────────
Golfer owns a Garmin R10, hits balls at the range
    → Exports session from Garmin Golf app as CSV
    
    → Opens SwingFit → "Upload Session File"
    → Drags-and-drops the CSV
    → Parser auto-detects Garmin format, ingests all shots
    → Sees swing profile + recommendations
    
    Total extra effort: ~60 seconds
    Data quality: Silver (consumer monitor data)

SCENARIO 4: "I Just Know My Numbers" (Manual entry fallback)
──────────────────────────────────────────────────────────────────
Golfer remembers their averages from a fitting or lesson
    
    → Opens SwingFit → "Enter My Numbers"
    → Types in: club speed, ball speed, launch angle, 
      spin rate, carry distance
    → Sees swing profile + recommendations (lower confidence)
    → Prompt: "Upload your Trackman report for better results"
    
    Total extra effort: ~3 minutes
    Data quality: Bronze (self-reported averages)
```

**Claude Code instructions for the Upload flow UI:**
1. Build a single "Add Session" page with three clear options presented as cards:
   - "Upload Trackman Report" (accepts images + PDFs) — with subtitle "Screenshot your Trackman app or forward your emailed report"
   - "Upload Session File" (accepts CSV, TSF) — with subtitle "Export from Trackman TPS, Garmin Golf, or any launch monitor"
   - "Enter My Numbers" (manual form) — with subtitle "Type in your averages if you don't have a file"
2. For the OCR path, show a loading state while Claude Vision processes ("Reading your Trackman data..."), then display the editable confirmation form
3. For file upload, show instant results — parsing is fast
4. After any successful ingest, immediately redirect to the Swing Profile page showing their data + recommendations

---

## Phase 2: Fitting Engine (Weeks 5–8)

This is the core IP. The engine takes a user's swing profile and recommends optimal equipment.

### 2.1 — User Swing Profile

Before recommending clubs, compute the user's swing profile from their shot data:

```python
# services/fitting_engine.py

class SwingProfile:
    """Computed from a user's shot history for a given club type."""
    
    club_type: str               # "driver", "7-iron", etc.
    
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
    std_carry: float             # standard deviation of carry distance
    std_offline: float | None    # standard deviation of offline distance
    shot_shape_tendency: str     # "draw", "fade", "straight", "variable"
    miss_direction: str          # "left", "right", "both"
    
    # Derived
    smash_factor: float
    spin_loft_estimate: float    # launch angle + attack angle (approximation)
    
    # Confidence
    sample_size: int             # number of valid shots
    data_quality: str            # "high" (50+ shots), "medium" (20-49), "low" (<20)
```

**Claude Code instructions:**
1. Create a function `compute_swing_profile(user_id, club_type) -> SwingProfile`
2. Pull all valid shots for this user and club type
3. Compute all the fields above using numpy (mean, std)
4. Determine `shot_shape_tendency` from face_to_path averages:
   - face_to_path < -2° → "draw"
   - face_to_path > 2° → "fade"
   - else → "straight"
   - std of face_to_path > 4° → "variable"
5. Set `data_quality` based on `sample_size`
6. Create endpoint `GET /users/{id}/swing-profile?club_type=driver`

### 2.2 — Recommendation Algorithm

The fitting engine matches a `SwingProfile` against the `ClubSpec` database. The algorithm works in stages:

**Stage 1: Hard Filters** — Eliminate clubs that are clearly wrong
- Filter out clubs outside the user's swing speed range (`swing_speed_min` / `swing_speed_max`)
- Filter out clubs that don't match the club type
- Filter out clubs outside the user's budget (if set)

**Stage 2: Scoring** — Score remaining clubs on how well they complement the user's swing

```python
def score_club(profile: SwingProfile, club: ClubSpec) -> float:
    """
    Score a club's fit for a given swing profile.
    Higher = better fit. Scale 0-100.
    """
    score = 0.0
    
    # --- Launch optimization (40% weight) ---
    # Optimal driver launch: ~15° launch, ~2200 rpm spin for max distance
    # If user launches too HIGH → recommend LOW launch/spin club (and vice versa)
    
    if profile.avg_launch_angle > OPTIMAL_LAUNCH[profile.club_type]:
        # User launches high — reward low-launch clubs
        if club.launch_bias == "low":
            score += 20
        elif club.launch_bias == "mid":
            score += 10
    elif profile.avg_launch_angle < OPTIMAL_LAUNCH[profile.club_type]:
        # User launches low — reward high-launch clubs
        if club.launch_bias == "high":
            score += 20
        elif club.launch_bias == "mid":
            score += 10
    else:
        # User is in the sweet spot — reward mid
        if club.launch_bias == "mid":
            score += 20
    
    # Same logic for spin
    # (spin optimization adds another 20 points)
    
    # --- Forgiveness vs Workability (30% weight) ---
    # High handicap / high dispersion → prioritize forgiveness
    # Low handicap / tight dispersion → prioritize workability
    
    dispersion_score = profile.std_offline or profile.std_carry
    if dispersion_score > HIGH_DISPERSION_THRESHOLD:
        score += club.forgiveness_rating * 3  # max 30
    else:
        score += club.workability_rating * 3  # max 30
    
    # --- Swing speed fit (20% weight) ---
    # How centered is the user in the club's ideal speed range?
    speed_center = (club.swing_speed_min + club.swing_speed_max) / 2
    speed_range = club.swing_speed_max - club.swing_speed_min
    speed_fit = 1 - abs(profile.avg_club_speed - speed_center) / (speed_range / 2)
    score += max(0, speed_fit * 20)
    
    # --- Recency bonus (10% weight) ---
    # Newer models get a small bonus (better tech, easier to find)
    years_old = CURRENT_YEAR - club.model_year
    recency_score = max(0, 10 - years_old * 2)  # 10 for current year, 0 for 5+ years old
    score += recency_score
    
    return score
```

**Stage 3: Ranking & Explanation**
- Sort by score descending
- Return top 5 recommendations
- For each, generate a plain-English explanation of WHY this club fits:
  - "Your avg launch angle is 14.2° with 3100 rpm spin — that's higher spin than optimal. The Titleist TSR3 is a low-spin head that should bring your spin down ~300-400 rpm and add 8-12 yards of carry."

**Claude Code instructions:**
1. Create `services/fitting_engine.py` with the `score_club` function
2. Define optimal launch/spin constants per club type (these are well-documented in fitting literature):
   - Driver: optimal launch ~12-15°, optimal spin ~2000-2500 rpm (varies by speed)
   - 7-iron: optimal launch ~16-20°, optimal spin ~6000-7000 rpm
3. Create `POST /fitting/recommend` endpoint:
   - Input: `user_id`, `club_type`, optional `budget_max`, optional `include_used`
   - Process: compute swing profile → hard filter → score → rank
   - Output: top 5 clubs with scores, explanations, and buy links
4. Create the explanation generator — use f-strings with the swing data and club specs to build readable explanations
5. Write unit tests with sample swing profiles and verify the scoring produces sensible rankings

### 2.3 — Comparison Mode

Let users compare their current club's performance against what the recommended club would theoretically deliver:

```
YOUR CURRENT DRIVER: TaylorMade SIM2 Max (10.5°)
  Avg Carry: 248 yd | Launch: 14.2° | Spin: 3100 rpm

RECOMMENDED: Titleist TSR3 (9.0°)
  Projected Carry: 258 yd | Launch: 12.8° | Spin: 2650 rpm
  Estimated gain: +10 yards carry

WHY: Your spin rate is ~600 rpm above optimal for your 
club speed (105 mph). The TSR3's lower-spin profile 
should reduce spin without sacrificing launch.
```

**Claude Code instructions:**
1. Create `POST /fitting/compare` endpoint
2. Input: `user_id`, `club_type`, `current_club_id` (or specs), `recommended_club_id`
3. Use the swing profile + club spec deltas to estimate projected performance changes
4. Keep projections conservative — use ranges not exact numbers ("8-12 yards" not "10 yards")

---

## Phase 3: Affiliate & Purchase Layer (Weeks 8–10)

### 3.1 — Affiliate Link Router

When a user clicks "Buy This Club," route them to the best available retailer with your affiliate tag.

```python
# services/affiliate_router.py

AFFILIATE_CONFIGS = {
    "global_golf": {
        "base_url": "https://www.globalgolf.com",
        "affiliate_network": "cj",
        "affiliate_id": "YOUR_CJ_ID",
        "commission_rate": 0.08,
        "cookie_days": 30,
        "supports_used": True,
    },
    "callaway_preowned": {
        "base_url": "https://www.callawaygolfpreowned.com",
        "affiliate_network": "partnerize",
        "affiliate_id": "YOUR_PARTNERIZE_ID",
        "commission_rate": 0.06,
        "cookie_days": 45,
        "supports_used": True,
        "brands": ["Callaway", "Odyssey"],  # brand-restricted
    },
    "taylormade": {
        "base_url": "https://www.taylormadegolf.com",
        "affiliate_network": "sovrn",
        "affiliate_id": "YOUR_SOVRN_ID",
        "commission_rate": 0.05,
        "cookie_days": 30,
        "supports_used": False,
        "brands": ["TaylorMade"],
    },
    # ... more retailers
}

def get_buy_links(club: ClubSpec, include_used: bool = True) -> list[dict]:
    """
    Returns ranked list of purchase options with affiliate links.
    Prioritizes: best price → highest commission → cookie duration.
    """
    links = []
    for retailer_key, config in AFFILIATE_CONFIGS.items():
        # Check brand restrictions
        if config.get("brands") and club.brand not in config["brands"]:
            continue
        # Check used support
        if not config["supports_used"] and not club.still_in_production:
            continue
        
        link = build_affiliate_url(config, club)
        links.append({
            "retailer": retailer_key,
            "url": link,
            "estimated_price": get_cached_price(retailer_key, club),
            "condition": "new" if club.still_in_production else "used",
            "commission_rate": config["commission_rate"],
        })
    
    # Sort by price ascending
    links.sort(key=lambda x: x["estimated_price"] or float("inf"))
    return links
```

**Claude Code instructions:**
1. Create `services/affiliate_router.py` with the retailer config structure
2. Create `GET /clubs/{id}/buy-links` endpoint
3. For MVP, start with just 3 retailers: GlobalGolf (CJ Affiliate), Callaway Pre-Owned (Partnerize), and Amazon (Associates)
4. Build the URL construction logic per affiliate network
5. Add click tracking: `POST /affiliate/click` — log every outbound click with user_id, club_id, retailer, timestamp
6. This click log is your revenue attribution data

### 3.2 — Price Caching

Don't hit retailer sites on every request. Cache prices and refresh on a schedule.

**Claude Code instructions:**
1. Create a `PriceCache` model: club_spec_id, retailer, price, condition, last_checked, url
2. Create a background job (`scripts/refresh_prices.py`) that:
   - Iterates through all club specs
   - Checks GlobalGolf / Amazon for current pricing
   - Updates the cache
3. Run daily via cron or a simple scheduler
4. For MVP, prices can be manually entered — automated scraping is Phase 4+

---

## Phase 4: Frontend (Weeks 8–12, parallel with Phase 3)

### 4.1 — Pages & User Flow

```
Landing Page
    │
    ▼
Sign Up / Login
    │
    ▼
Dashboard
    ├── Upload Session (drag-drop CSV or manual entry)
    │       │
    │       ▼
    │   Session Summary (stats table, shot dispersion chart)
    │
    ├── My Bag (current clubs + performance data per club)
    │
    ├── Get Fitted (select club type → see recommendations)
    │       │
    │       ▼
    │   Recommendation Cards
    │       ├── Club name, image, score, explanation
    │       ├── "Compare to my current" toggle
    │       └── "Buy" button → affiliate link
    │
    └── Settings (profile, budget preferences, units)
```

**Claude Code instructions:**
1. Set up React project with Vite, Tailwind CSS, React Router
2. Build pages in this order:
   a. **Upload page** — drag-drop CSV zone + manual entry form
   b. **Session summary** — table of shot stats + basic charts (use Recharts)
   c. **Recommendation page** — card layout showing top 5 clubs with scores
   d. **Dashboard** — overview of sessions, swing trends over time
3. Use mobile-first responsive design — most golfers will use this at the range on their phone
4. Keep it clean and simple — no unnecessary UI complexity

### 4.2 — Key UI Components

**Recommendation Card:**
```
┌────────────────────────────────────┐
│  🏆 #1 MATCH — 94/100             │
│                                    │
│  Titleist TSR3 Driver (9.0°)       │
│  2023 | MSRP $599 | Used ~$380     │
│                                    │
│  WHY IT FITS:                      │
│  Your spin is 600 rpm above        │
│  optimal. This low-spin head       │
│  should add 8-12 yards carry.      │
│                                    │
│  [Compare to Mine]  [Buy — $380]   │
└────────────────────────────────────┘
```

**Swing Profile Summary:**
```
┌────────────────────────────────────┐
│  YOUR DRIVER PROFILE               │
│  Based on 47 shots (High Quality)  │
│                                    │
│  Club Speed:   105.2 mph           │
│  Ball Speed:   149.8 mph           │
│  Launch:       14.2° (▲ high)      │
│  Spin:         3,100 rpm (▲ high)  │
│  Carry:        248 yd              │
│  Dispersion:   ±18 yd             │
│  Shot Shape:   Fade tendency       │
│                                    │
│  ⚠️ Opportunity: Spin reduction    │
│  could add 8-15 yards              │
└────────────────────────────────────┘
```

---

## Phase 5: Polish & Launch (Weeks 12–16)

### 5.1 — Additional Parsers & Trackman Expansion
- Rapsodo MLM2 Pro (CSV export)
- Full Swing KIT (CSV/JSON export from Full Swing app)
- SkyTrak / Uneekor (sim users)
- FlightScope Mevo+ (CSV export)
- **Trackman 4 Desktop Bridge app** (Electron or Python GUI) — Package the tm4_bridge.py CLI into a proper desktop app with:
  - Auto-discovery of Trackman on local network
  - One-click connect + arm
  - Real-time shot display in a local UI
  - Background sync to SwingFit cloud
- **Trackman Range partnership** — With working code and user traction, approach Trackman for official Range API credentials

### 5.2 — Subscription & Paywall
- **Free tier:** Upload 1 session, get 1 club recommendation (driver only)
- **Pro tier ($7.99/mo or $59.99/yr):**
  - Unlimited sessions & history
  - Full bag recommendations (driver + irons + wedges + putter)
  - New club alerts ("A new driver just released that's a 96% match for your swing")
  - Trend tracking over time
  - Comparison mode

**Claude Code instructions:**
1. Integrate Stripe for subscription management
2. Create middleware that checks subscription tier before allowing access to Pro endpoints
3. Use Stripe webhooks for subscription lifecycle events

### 5.3 — New Club Alerts (Retention Feature)
When a new club model is added to the database:
1. Run it through the fitting engine against all Pro users' swing profiles
2. If it scores in their top 3 for any club type, send a push notification / email:
   "New release: The 2026 Callaway Paradym Ai Smoke driver scores 96/100 for your swing — 4 points higher than your current top pick."

### 5.4 — SEO / Content
- Auto-generate landing pages for each club in the database:
  `/clubs/taylormade-qi10-driver` with specs, pricing, and "see if it fits your swing" CTA
- These pages drive organic traffic from golfers searching for club reviews

---

## Phase 6: B2B Licensing (Months 6+)

Once the consumer product is validated, white-label the fitting engine for:
- **Independent club fitters** — $49-99/mo to use the engine during in-person fittings
- **Pro shops** — embed recommendations on their e-commerce sites
- **Launch monitor companies** — license the engine as a built-in feature of their apps (Garmin, Rapsodo, etc.)

This is the long-term high-margin play and doesn't need to be built until the core consumer product works.

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend language | Python/FastAPI | Danny's existing expertise, fast iteration, numpy for stats |
| Database | PostgreSQL | Relational data, good for analytics queries on shot data |
| Frontend | React (Vite) | Modern, fast, huge ecosystem, easy Capacitor wrap later |
| Hosting (MVP) | Railway or Render | Fast deploy, free tier, no infra management |
| Auth | Supabase Auth or JWT | Simple, cheap, handles social login |
| Payments | Stripe | Industry standard, good subscription management |
| Affiliate tracking | Custom + network SDKs | CJ, Partnerize, Amazon Associates APIs |
| Charts | Recharts | React-native, lightweight, handles all needed chart types |

---

## MVP Definition (What to ship first)

The absolute minimum to get in front of users and validate demand:

1. ✅ Upload a Trackman report via screenshot or PDF (Claude Vision OCR extraction — this is the primary onboarding path)
2. ✅ Upload a Trackman CSV/TSF export (for users with TPS access)
3. ✅ Upload a Garmin R10 CSV (secondary path for consumer monitor owners)
4. ✅ Manual entry fallback for users without files
5. ✅ Editable confirmation step for OCR-extracted data (user verifies before saving)
6. ✅ See your swing profile summary for driver (with data quality tier badge)
7. ✅ Get top 3 driver recommendations with explanations
8. ✅ Click through to buy (affiliate link to GlobalGolf)
9. ✅ User accounts with session history

**What's NOT in MVP:**
- ❌ Trackman Range API real-time integration (needs partnership credentials)
- ❌ Trackman 4 desktop bridge app (complex, niche)
- ❌ Iron/wedge/putter recommendations (just driver)
- ❌ Subscription paywall (everything free at first)
- ❌ Price scraping (manual price entry)
- ❌ Mobile app (responsive web only)
- ❌ B2B features

Ship the MVP, get 50-100 golfers using it (target Trackman users first — they're the most data-savvy and equipment-obsessed segment), watch what they do, then iterate.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Club spec data is hard to source at scale | High | High | Start with top 50 models manually; quality > quantity |
| Recommendation accuracy questioned | Medium | High | Always show confidence level; be transparent about data quality thresholds |
| Trackman Range API access denied or delayed | High | High | MVP works entirely on file uploads (no API needed). Build the client code, demo it, then approach Trackman. File upload alone captures most Trackman users. |
| Trackman changes export formats or locks down data further | Medium | High | Support multiple ingest paths so no single pathway is a single point of failure. SwingSync intermediary is a hedge. |
| Trackman 4 TCP/IP protocol undocumented / changes | High | Medium | The bridge app is Phase 5+, not MVP. File export is the reliable path. Community has already reverse-engineered the protocol for sim software. |
| MyTrackman.com never opens a consumer API | High | Medium | Not a blocker — file export + Range API + bridge cover all use cases. If they do open an API, it's upside. |
| Launch monitor APIs don't exist / change | High | Medium | Build on CSV export (universal) not APIs; API integration is a bonus |
| Affiliate programs reject application | Medium | Medium | Apply early; start with Amazon (easy approval) and add others |
| Low conversion on affiliate links | Medium | Medium | Stack with subscription revenue; affiliate is gravy not the whole meal |
| Existing player (UFIT, TRUEGolfFit) copies the real-time approach | Medium | Low | Speed to market + data flywheel = moat compounds over time |
| Trackman users don't know how to export their data | Medium | Medium | Build step-by-step export guides with screenshots for each pathway (TPS CSV, TPS stroke file, SwingSync). Make it dead simple. |
