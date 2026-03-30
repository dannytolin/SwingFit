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
        <StatRow label="Launch Angle" value={stats.avg_launch_angle} unit="deg" />
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
