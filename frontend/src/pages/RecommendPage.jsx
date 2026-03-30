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
        <div>Launch: <b>{profile.avg_launch_angle?.toFixed(1)}&deg;{indicator(profile.avg_launch_angle, optL[0], optL[1])}</b></div>
        <div>Spin: <b>{profile.avg_spin_rate?.toFixed(0)} rpm{indicator(profile.avg_spin_rate, optS[0], optS[1])}</b></div>
        <div>Carry: <b>{profile.avg_carry?.toFixed(0)} yd</b></div>
        <div>Dispersion: <b>&plusmn;{profile.std_carry?.toFixed(0)} yd</b></div>
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
          #{rank} MATCH &mdash; {rec.score}/100
        </span>
      </div>
      <h3 className="font-bold text-lg">{club.brand} {club.model_name}</h3>
      <p className="text-sm text-gray-500">
        {club.model_year} | {club.loft && `${club.loft}\u00B0`} | MSRP ${club.msrp}
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
          Buy &mdash; ${bestLink.estimated_price} ({bestLink.condition})
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
