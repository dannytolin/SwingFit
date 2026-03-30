import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import DashboardPage from './pages/DashboardPage'
import UploadPage from './pages/UploadPage'
import SessionPage from './pages/SessionPage'
import RecommendPage from './pages/RecommendPage'

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
