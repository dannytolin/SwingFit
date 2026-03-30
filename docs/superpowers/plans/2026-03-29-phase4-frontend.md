# Phase 4: Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a mobile-first React SPA that lets golfers upload swing data (CSV, screenshot, or manual), view their swing profile, get club recommendations with buy links, and see session history.

**Architecture:** Vite + React + Tailwind CSS + React Router. An API client module wraps all backend calls. Pages: Upload (3 ingest paths), Session Summary (post-upload stats), Recommendations (profile + scored cards + buy links), Dashboard (session list). No auth for MVP — uses a demo user created on first load.

**Tech Stack:** React 18, Vite, Tailwind CSS, React Router v6, Recharts (charts)

---

### Task 1: CORS Middleware on Backend

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_cors.py`

The frontend (port 5173) needs to call the backend (port 8000). Without CORS, browsers block the requests.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_cors.py`:

```python
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_cors_preflight():
    response = client.options(
        "/",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_cors_header_on_get():
    response = client.get(
        "/",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.headers.get("access-control-allow-origin") == "*"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_cors.py -v`
Expected: FAIL — no CORS headers

- [ ] **Step 3: Add CORS middleware to main.py**

Edit `backend/app/main.py` — add the CORS middleware after creating the app:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.routers.affiliate import router as affiliate_router
from backend.app.routers.clubs import router as clubs_router
from backend.app.routers.fitting import router as fitting_router
from backend.app.routers.ingest import router as ingest_router
from backend.app.routers.sessions import router as sessions_router

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clubs_router)
app.include_router(sessions_router)
app.include_router(ingest_router)
app.include_router(fitting_router)
app.include_router(affiliate_router)


@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.app_name}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_cors.py -v`
Expected: Both tests PASS

- [ ] **Step 5: Run full backend test suite**

Run: `python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/test_cors.py
git commit -m "feat: add CORS middleware for frontend dev server"
```

---

### Task 2: Vite + React + Tailwind Scaffold

**Files:**
- Create: `frontend/` project via Vite
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/App.jsx`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Create Vite React project**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
rm frontend/.gitkeep
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit/frontend"
npm create vite@latest . -- --template react
npm install
npm install -D tailwindcss @tailwindcss/vite
npm install react-router-dom recharts
```

- [ ] **Step 2: Configure Tailwind**

Replace `frontend/src/index.css`:

```css
@import "tailwindcss";
```

Add the Tailwind Vite plugin to `frontend/vite.config.js`:

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

- [ ] **Step 3: Set up React Router in App.jsx**

Replace `frontend/src/App.jsx`:

```jsx
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import SessionPage from './pages/SessionPage'
import RecommendPage from './pages/RecommendPage'
import DashboardPage from './pages/DashboardPage'

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-green-700">SwingFit</Link>
          <div className="flex gap-4 text-sm">
            <Link to="/" className="text-gray-600 hover:text-green-700">Dashboard</Link>
            <Link to="/upload" className="text-gray-600 hover:text-green-700">Upload</Link>
            <Link to="/recommend" className="text-gray-600 hover:text-green-700">Get Fitted</Link>
          </div>
        </div>
      </nav>
      <main className="max-w-5xl mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/session/:sessionId" element={<SessionPage />} />
          <Route path="/recommend" element={<RecommendPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
```

- [ ] **Step 4: Create placeholder page components**

Create `frontend/src/pages/DashboardPage.jsx`:

```jsx
export default function DashboardPage() {
  return <div><h1 className="text-2xl font-bold">Dashboard</h1><p className="text-gray-500 mt-2">Coming soon</p></div>
}
```

Create `frontend/src/pages/UploadPage.jsx`:

```jsx
export default function UploadPage() {
  return <div><h1 className="text-2xl font-bold">Upload Session</h1><p className="text-gray-500 mt-2">Coming soon</p></div>
}
```

Create `frontend/src/pages/SessionPage.jsx`:

```jsx
export default function SessionPage() {
  return <div><h1 className="text-2xl font-bold">Session Summary</h1><p className="text-gray-500 mt-2">Coming soon</p></div>
}
```

Create `frontend/src/pages/RecommendPage.jsx`:

```jsx
export default function RecommendPage() {
  return <div><h1 className="text-2xl font-bold">Get Fitted</h1><p className="text-gray-500 mt-2">Coming soon</p></div>
}
```

- [ ] **Step 5: Update main.jsx**

Replace `frontend/src/main.jsx`:

```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 6: Verify the dev server starts**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit/frontend"
npm run dev &
sleep 3
curl -s http://localhost:5173 | head -5
kill %1
```

Expected: HTML with `<div id="root">` returned

- [ ] **Step 7: Commit**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
git add frontend/
git commit -m "feat: scaffold React frontend with Vite, Tailwind, React Router"
```

---

### Task 3: API Client Module

**Files:**
- Create: `frontend/src/api.js`

This module wraps all backend API calls. The Vite proxy rewrites `/api/*` to `http://localhost:8000/*`.

- [ ] **Step 1: Create the API client**

Create `frontend/src/api.js`:

```js
const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// Ingest
export async function uploadCSV(userId, file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/ingest/upload?user_id=${userId}`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function uploadReport(userId, file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/ingest/trackman-report?user_id=${userId}`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function manualEntry(userId, data) {
  const params = new URLSearchParams({
    user_id: userId,
    club_type: data.club_type,
    ball_speed: data.ball_speed,
    launch_angle: data.launch_angle,
    spin_rate: data.spin_rate,
    carry_distance: data.carry_distance,
    ...(data.club_speed && { club_speed: data.club_speed }),
    ...(data.total_distance && { total_distance: data.total_distance }),
  })
  return request(`/ingest/manual?${params}`, { method: 'POST' })
}

// Sessions
export async function getSessionSummary(sessionId) {
  return request(`/sessions/${sessionId}/summary`)
}

// Swing Profile
export async function getSwingProfile(userId, clubType) {
  return request(`/users/${userId}/swing-profile?club_type=${clubType}`)
}

// Fitting
export async function getRecommendations(userId, clubType, options = {}) {
  return request('/fitting/recommend', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      club_type: clubType,
      budget_max: options.budgetMax || null,
      include_used: options.includeUsed || false,
      top_n: options.topN || 5,
    }),
  })
}

export async function compareClubs(userId, clubType, currentClubId, recommendedClubId) {
  return request('/fitting/compare', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      club_type: clubType,
      current_club_id: currentClubId,
      recommended_club_id: recommendedClubId,
    }),
  })
}

// Affiliate
export async function trackClick(userId, clubSpecId, retailer, url) {
  return request('/affiliate/click', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      club_spec_id: clubSpecId,
      retailer,
      url,
    }),
  })
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api.js
git commit -m "feat: add API client module for all backend endpoints"
```

---

### Task 4: Upload Page

**Files:**
- Modify: `frontend/src/pages/UploadPage.jsx`

The upload page has 3 cards: Upload Trackman Report (images/PDFs), Upload Session File (CSVs), Enter My Numbers (manual form). For MVP, use a hardcoded `userId = 1`.

- [ ] **Step 1: Build the upload page**

Replace `frontend/src/pages/UploadPage.jsx`:

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadCSV, uploadReport, manualEntry } from '../api'

const USER_ID = 1

function FileDropZone({ label, subtitle, accept, onUpload }) {
  const [dragging, setDragging] = useState(false)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)

  async function handleFile(file) {
    setStatus('uploading')
    setError(null)
    try {
      const result = await onUpload(file)
      setStatus('done')
      return result
    } catch (e) {
      setError(e.message)
      setStatus(null)
      return null
    }
  }

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
        dragging ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-green-400'
      }`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0])
      }}
      onClick={() => {
        const input = document.createElement('input')
        input.type = 'file'
        input.accept = accept
        input.onchange = (e) => { if (e.target.files[0]) handleFile(e.target.files[0]) }
        input.click()
      }}
    >
      <p className="font-semibold text-gray-800">{label}</p>
      <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
      {status === 'uploading' && <p className="text-sm text-blue-600 mt-2">Processing...</p>}
      {status === 'done' && <p className="text-sm text-green-600 mt-2">Upload complete!</p>}
      {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
    </div>
  )
}

function ManualEntryForm() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    club_type: 'Driver', ball_speed: '', launch_angle: '',
    spin_rate: '', carry_distance: '', club_speed: '', total_distance: '',
  })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const result = await manualEntry(USER_ID, form)
      navigate(`/session/${result.session.id}`)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function field(name, label, required = true) {
    return (
      <div>
        <label className="block text-sm font-medium text-gray-700">{label}{required && ' *'}</label>
        <input
          type="number"
          step="0.1"
          required={required}
          className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          value={form[name]}
          onChange={(e) => setForm({ ...form, [name]: e.target.value })}
        />
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-gray-700">Club Type *</label>
        <select
          className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          value={form.club_type}
          onChange={(e) => setForm({ ...form, club_type: e.target.value })}
        >
          <option>Driver</option>
          <option>3 Wood</option>
          <option>5 Wood</option>
          <option>7 Iron</option>
          <option>PW</option>
        </select>
      </div>
      {field('ball_speed', 'Ball Speed (mph)')}
      {field('launch_angle', 'Launch Angle (°)')}
      {field('spin_rate', 'Spin Rate (rpm)')}
      {field('carry_distance', 'Carry Distance (yd)')}
      {field('club_speed', 'Club Speed (mph)', false)}
      {field('total_distance', 'Total Distance (yd)', false)}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-green-600 text-white rounded py-2 font-medium hover:bg-green-700 disabled:opacity-50"
      >
        {loading ? 'Saving...' : 'Save & Get Recommendations'}
      </button>
    </form>
  )
}

export default function UploadPage() {
  const navigate = useNavigate()

  async function handleCSV(file) {
    const result = await uploadCSV(USER_ID, file)
    navigate(`/session/${result.session.id}`)
    return result
  }

  async function handleReport(file) {
    const result = await uploadReport(USER_ID, file)
    navigate(`/session/${result.session.id}`)
    return result
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Add Session</h1>

      <div className="grid gap-4 md:grid-cols-2">
        <FileDropZone
          label="Upload Trackman Report"
          subtitle="Screenshot your Trackman app or forward your emailed report"
          accept="image/*,.pdf"
          onUpload={handleReport}
        />
        <FileDropZone
          label="Upload Session File"
          subtitle="Export from Trackman TPS, Garmin Golf, or any launch monitor"
          accept=".csv,.tsf"
          onUpload={handleCSV}
        />
      </div>

      <div className="border rounded-lg p-6 bg-white">
        <h2 className="font-semibold text-gray-800 mb-1">Enter My Numbers</h2>
        <p className="text-sm text-gray-500 mb-4">Type in your averages if you don't have a file</p>
        <ManualEntryForm />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify the page renders**

Start the dev server and visit `http://localhost:5173/upload` — should see 2 drop zones and a manual form.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/UploadPage.jsx
git commit -m "feat: add upload page with CSV, report, and manual entry"
```

---

### Task 5: Session Summary Page

**Files:**
- Modify: `frontend/src/pages/SessionPage.jsx`

Shows per-club stats after an upload completes. Uses the `/sessions/{id}/summary` endpoint.

- [ ] **Step 1: Build the session summary page**

Replace `frontend/src/pages/SessionPage.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getSessionSummary } from '../api'

function StatRow({ label, value, unit }) {
  if (value == null) return null
  return (
    <div className="flex justify-between py-1 border-b border-gray-100">
      <span className="text-gray-600 text-sm">{label}</span>
      <span className="font-medium text-sm">{typeof value === 'number' ? value.toFixed(1) : value} {unit}</span>
    </div>
  )
}

function ClubSummaryCard({ clubName, stats }) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="font-bold text-lg mb-2 capitalize">{clubName}</h3>
      <p className="text-xs text-gray-500 mb-3">{stats.shot_count} shots</p>
      <div className="space-y-0">
        <StatRow label="Ball Speed" value={stats.avg_ball_speed} unit="mph" />
        <StatRow label="Club Speed" value={stats.avg_club_speed} unit="mph" />
        <StatRow label="Launch Angle" value={stats.avg_launch_angle} unit="°" />
        <StatRow label="Spin Rate" value={stats.avg_spin_rate} unit="rpm" />
        <StatRow label="Carry" value={stats.avg_carry} unit="yd" />
        <StatRow label="Total" value={stats.avg_total} unit="yd" />
        <StatRow label="Smash Factor" value={stats.avg_smash_factor} unit="" />
      </div>
    </div>
  )
}

export default function SessionPage() {
  const { sessionId } = useParams()
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getSessionSummary(sessionId)
      .then(setSummary)
      .catch((e) => setError(e.message))
  }, [sessionId])

  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!summary) return <p className="text-gray-500">Loading session...</p>

  const clubs = Object.entries(summary)

  if (clubs.length === 0) {
    return <p className="text-gray-500">No shot data in this session.</p>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Session #{sessionId}</h1>
        <Link to="/recommend" className="bg-green-600 text-white text-sm px-4 py-2 rounded hover:bg-green-700">
          Get Recommendations
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {clubs.map(([clubName, stats]) => (
          <ClubSummaryCard key={clubName} clubName={clubName} stats={stats} />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/SessionPage.jsx
git commit -m "feat: add session summary page with per-club stats"
```

---

### Task 6: Recommendation Page with Swing Profile & Cards

**Files:**
- Modify: `frontend/src/pages/RecommendPage.jsx`

The main "Get Fitted" page: shows swing profile summary + recommendation cards with scores, explanations, and buy links.

- [ ] **Step 1: Build the recommendation page**

Replace `frontend/src/pages/RecommendPage.jsx`:

```jsx
import { useState } from 'react'
import { getRecommendations, trackClick } from '../api'

const USER_ID = 1

function ProfileCard({ profile }) {
  if (!profile) return null

  const launchOpt = { driver: [12, 15], '7-iron': [16, 20] }
  const spinOpt = { driver: [2000, 2500], '7-iron': [6000, 7000] }
  const optL = launchOpt[profile.club_type] || [12, 15]
  const optS = spinOpt[profile.club_type] || [2000, 2500]

  function indicator(val, low, high) {
    if (val > high) return ' (high)'
    if (val < low) return ' (low)'
    return ''
  }

  return (
    <div className="bg-white rounded-lg border p-5">
      <h2 className="font-bold text-lg mb-1">Your {profile.club_type} Profile</h2>
      <p className="text-xs text-gray-500 mb-3">
        Based on {profile.sample_size} shots ({profile.data_quality} quality)
      </p>
      <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
        <div>Club Speed: <b>{profile.avg_club_speed?.toFixed(1)} mph</b></div>
        <div>Ball Speed: <b>{profile.avg_ball_speed?.toFixed(1)} mph</b></div>
        <div>Launch: <b>{profile.avg_launch_angle?.toFixed(1)}°{indicator(profile.avg_launch_angle, optL[0], optL[1])}</b></div>
        <div>Spin: <b>{profile.avg_spin_rate?.toFixed(0)} rpm{indicator(profile.avg_spin_rate, optS[0], optS[1])}</b></div>
        <div>Carry: <b>{profile.avg_carry?.toFixed(0)} yd</b></div>
        <div>Dispersion: <b>±{profile.std_carry?.toFixed(0)} yd</b></div>
        <div>Shot Shape: <b className="capitalize">{profile.shot_shape_tendency}</b></div>
        <div>Smash: <b>{profile.smash_factor?.toFixed(2)}</b></div>
      </div>
    </div>
  )
}

function RecCard({ rec, rank }) {
  const club = rec.club
  const bestLink = rec.buy_links?.[0]

  async function handleBuyClick(link) {
    try {
      await trackClick(USER_ID, club.id, link.retailer, link.url)
    } catch (e) { /* tracking failure shouldn't block navigation */ }
    window.open(link.url, '_blank')
  }

  return (
    <div className="bg-white rounded-lg border p-5">
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs font-bold text-green-700 bg-green-50 px-2 py-1 rounded">
          #{rank} MATCH — {rec.score}/100
        </span>
      </div>
      <h3 className="font-bold text-lg">{club.brand} {club.model_name}</h3>
      <p className="text-sm text-gray-500">
        {club.model_year} | {club.loft && `${club.loft}°`} | MSRP ${club.msrp}
        {club.avg_used_price && ` | Used ~$${club.avg_used_price}`}
      </p>
      <div className="mt-3 text-sm text-gray-700">
        <p className="font-medium mb-1">Why it fits:</p>
        <p>{rec.explanation}</p>
      </div>
      {bestLink && (
        <button
          onClick={() => handleBuyClick(bestLink)}
          className="mt-4 w-full bg-green-600 text-white rounded py-2 text-sm font-medium hover:bg-green-700"
        >
          Buy — ${bestLink.estimated_price} ({bestLink.condition})
        </button>
      )}
      {rec.buy_links?.length > 1 && (
        <div className="mt-2 text-xs text-gray-500">
          Also at: {rec.buy_links.slice(1).map(l => l.retailer.replace('_', ' ')).join(', ')}
        </div>
      )}
    </div>
  )
}

export default function RecommendPage() {
  const [clubType, setClubType] = useState('driver')
  const [budget, setBudget] = useState('')
  const [includeUsed, setIncludeUsed] = useState(true)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleFit() {
    setLoading(true)
    setError(null)
    try {
      const data = await getRecommendations(USER_ID, clubType, {
        budgetMax: budget ? parseFloat(budget) : null,
        includeUsed,
      })
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Get Fitted</h1>

      <div className="bg-white rounded-lg border p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm font-medium text-gray-700">Club Type</label>
          <select
            className="mt-1 rounded border border-gray-300 px-3 py-2 text-sm"
            value={clubType}
            onChange={(e) => setClubType(e.target.value)}
          >
            <option value="driver">Driver</option>
            <option value="iron">Iron</option>
            <option value="wedge">Wedge</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Max Budget ($)</label>
          <input
            type="number"
            className="mt-1 rounded border border-gray-300 px-3 py-2 text-sm w-28"
            placeholder="Any"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
          />
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeUsed}
            onChange={(e) => setIncludeUsed(e.target.checked)}
          />
          Include used
        </label>
        <button
          onClick={handleFit}
          disabled={loading}
          className="bg-green-600 text-white px-6 py-2 rounded text-sm font-medium hover:bg-green-700 disabled:opacity-50"
        >
          {loading ? 'Analyzing...' : 'Find My Clubs'}
        </button>
      </div>

      {error && <p className="text-red-600">{error}</p>}

      {result && (
        <>
          <ProfileCard profile={result.profile} />
          <div className="grid gap-4 md:grid-cols-2">
            {result.recommendations.map((rec, i) => (
              <RecCard key={rec.club.id} rec={rec} rank={i + 1} />
            ))}
          </div>
          {result.recommendations.length === 0 && (
            <p className="text-gray-500">No matching clubs found. Try adjusting your filters.</p>
          )}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/RecommendPage.jsx
git commit -m "feat: add recommendation page with profile, scored cards, and buy links"
```

---

### Task 7: Dashboard Page

**Files:**
- Modify: `frontend/src/pages/DashboardPage.jsx`

Overview page with a link to upload and a link to get fitted. For MVP, this is a simple landing page.

- [ ] **Step 1: Build the dashboard**

Replace `frontend/src/pages/DashboardPage.jsx`:

```jsx
import { Link } from 'react-router-dom'

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Welcome to SwingFit</h1>
        <p className="text-gray-600 mt-2">
          Upload your swing data and get personalized club recommendations instantly.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Link
          to="/upload"
          className="block bg-white rounded-lg border p-6 hover:border-green-500 hover:shadow-md transition"
        >
          <h2 className="font-bold text-lg text-gray-900">Upload Session</h2>
          <p className="text-sm text-gray-500 mt-1">
            Drop a Trackman CSV, screenshot a report, or enter your numbers manually.
          </p>
          <span className="inline-block mt-3 text-green-600 text-sm font-medium">Get started &rarr;</span>
        </Link>

        <Link
          to="/recommend"
          className="block bg-white rounded-lg border p-6 hover:border-green-500 hover:shadow-md transition"
        >
          <h2 className="font-bold text-lg text-gray-900">Get Fitted</h2>
          <p className="text-sm text-gray-500 mt-1">
            See which clubs match your swing profile with scores and explanations.
          </p>
          <span className="inline-block mt-3 text-green-600 text-sm font-medium">Find my clubs &rarr;</span>
        </Link>
      </div>

      <div className="text-xs text-gray-400">
        SwingFit analyzes your launch monitor data and recommends equipment from a database of 20+ clubs
        across TaylorMade, Callaway, Titleist, Ping, and Cobra.
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/DashboardPage.jsx
git commit -m "feat: add dashboard landing page"
```

---

### Task 8: Demo User Seeding & Full Integration Test

**Files:**
- Create: `scripts/seed_demo.py`

For MVP, create a demo user with pre-loaded shot data so the app works immediately. Also verify the full frontend-backend integration.

- [ ] **Step 1: Create demo seed script**

Create `scripts/seed_demo.py`:

```python
"""Seed a demo user with driver shots for testing the frontend."""
from backend.app.database import SessionLocal, engine, Base
from backend.app.models import User, ClubSpec, SwingSession, Shot
from scripts.seed_clubs import seed_clubs_from_csv


def seed_demo():
    Base.metadata.create_all(engine)
    db = SessionLocal()

    # Check if demo user already exists
    existing = db.query(User).filter(User.email == "demo@swingfit.com").first()
    if existing:
        print(f"Demo user already exists (id={existing.id})")
        db.close()
        return

    # Create demo user
    user = User(email="demo@swingfit.com", username="demo", hashed_password="demo")
    db.add(user)
    db.commit()

    # Seed clubs
    count = seed_clubs_from_csv(db, "data/club_specs/initial_seed.csv")
    print(f"Seeded {count} clubs")

    # Create a session with 15 driver shots
    session = SwingSession(
        user_id=user.id,
        launch_monitor_type="trackman_4",
        data_source="file_upload",
    )
    db.add(session)
    db.commit()

    import random
    random.seed(42)
    for i in range(15):
        db.add(Shot(
            session_id=session.id,
            club_used="driver",
            ball_speed=148.0 + random.gauss(0, 2),
            launch_angle=13.5 + random.gauss(0, 0.8),
            spin_rate=3000.0 + random.gauss(0, 200),
            carry_distance=247.0 + random.gauss(0, 5),
            total_distance=270.0 + random.gauss(0, 6),
            club_speed=104.5 + random.gauss(0, 1.5),
            attack_angle=-1.0 + random.gauss(0, 0.5),
            face_to_path=-1.2 + random.gauss(0, 0.8),
            offline_distance=5.0 + random.gauss(0, 6),
            smash_factor=1.41 + random.gauss(0, 0.01),
            shot_number=i + 1,
        ))

    db.commit()
    print(f"Created demo user (id={user.id}) with 15 driver shots")
    db.close()


if __name__ == "__main__":
    seed_demo()
```

- [ ] **Step 2: Run the seed script**

```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
source .venv/Scripts/activate
rm -f swingfit.db
python -m scripts.seed_demo
```

Expected: `Seeded 20 clubs` and `Created demo user (id=1) with 15 driver shots`

- [ ] **Step 3: Integration test — start both servers and verify**

Terminal 1 (backend):
```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit"
source .venv/Scripts/activate
uvicorn backend.app.main:app --port 8000
```

Terminal 2 (frontend):
```bash
cd "C:/Users/DannyTolin/OneDrive - ARTE/Desktop/Swingfit/frontend"
npm run dev
```

Then open `http://localhost:5173` in a browser and verify:
1. Dashboard loads with two cards
2. Click "Get Fitted" → select Driver → click "Find My Clubs"
3. Swing profile card appears with stats
4. 5 recommendation cards appear with scores and explanations
5. Buy buttons show prices and open retailer URLs
6. Upload page shows 3 ingest options

- [ ] **Step 4: Run backend test suite to ensure no regressions**

```bash
python -m pytest backend/tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add scripts/seed_demo.py
git commit -m "feat: add demo user seed script for frontend testing"
```

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: Phase 4 complete — React frontend with upload, recommendations, and buy links"
```
