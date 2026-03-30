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
      {field('launch_angle', 'Launch Angle (deg)')}
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
