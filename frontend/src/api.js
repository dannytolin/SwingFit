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
