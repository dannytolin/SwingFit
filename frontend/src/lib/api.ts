import { supabase } from '@/integrations/supabase/client';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function authHeaders(): Promise<HeadersInit> {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) return {};
  return { Authorization: `Bearer ${session.access_token}` };
}

async function authFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const headers = { ...init.headers, ...(await authHeaders()) };
  return fetch(url, { ...init, headers });
}

// --- Ingest endpoints ---

export async function uploadTrackmanReport(file: File) {
  const form = new FormData();
  form.append('file', file);
  const res = await authFetch(`${API_URL}/ingest/trackman-report`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to upload report');
  }
  return res.json();
}

export async function uploadSessionFile(file: File) {
  const form = new FormData();
  form.append('file', file);
  const res = await authFetch(`${API_URL}/ingest/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to upload file');
  }
  return res.json();
}

export async function manualEntry(data: {
  club_type: string;
  ball_speed: number;
  launch_angle: number;
  spin_rate: number;
  carry_distance: number;
  club_speed?: number;
}) {
  const params = new URLSearchParams({
    club_type: data.club_type,
    ball_speed: String(data.ball_speed),
    launch_angle: String(data.launch_angle),
    spin_rate: String(data.spin_rate),
    carry_distance: String(data.carry_distance),
  });
  if (data.club_speed) params.set('club_speed', String(data.club_speed));

  const res = await authFetch(`${API_URL}/ingest/manual?${params}`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to save manual entry');
  }
  return res.json();
}

// --- Fitting endpoints ---

export async function getSwingProfile(clubType: string) {
  const res = await authFetch(
    `${API_URL}/users/me/swing-profile?club_type=${encodeURIComponent(clubType)}`
  );
  if (!res.ok) {
    if (res.status === 404) return null;
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to fetch swing profile');
  }
  return res.json();
}

export async function getCachedRecommendations(clubType: string) {
  const res = await authFetch(
    `${API_URL}/fitting/recommendations?club_type=${encodeURIComponent(clubType)}`
  );
  if (!res.ok) {
    if (res.status === 404) return null;
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to fetch cached recommendations');
  }
  return res.json();
}

export async function generateRecommendations(opts: {
  club_type: string;
  budget_max?: number;
  include_used?: boolean;
  top_n?: number;
}) {
  const res = await authFetch(`${API_URL}/fitting/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      club_type: opts.club_type,
      budget_max: opts.budget_max,
      include_used: opts.include_used ?? false,
      top_n: opts.top_n ?? 5,
    }),
  });
  if (!res.ok) {
    if (res.status === 404) return null;
    if (res.status === 503) throw new Error('Recommendation engine temporarily unavailable');
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to generate recommendations');
  }
  return res.json();
}

export async function compareClubs(opts: {
  club_type: string;
  current_club_id: number;
  recommended_club_id: number;
}) {
  const res = await authFetch(`${API_URL}/fitting/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(opts),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to compare clubs');
  }
  return res.json();
}
