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
