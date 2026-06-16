import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import { Layout } from './components/Layout'
import { Setup } from './pages/Setup'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Upload } from './pages/Upload'
import { Collections } from './pages/Collections'
import { CollectionDetail } from './pages/CollectionDetail'
import { Gallery } from './pages/Gallery'
import { Settings } from './pages/Settings'
import { Jobs } from './pages/Jobs'
import { HistoryPage } from './pages/History'
import axios from 'axios'

function App() {
  const { token, setupCompleted, setSetupCompleted } = useAuthStore()

  useEffect(() => {
    axios.get('/api/setup-status')
      .then((res) => setSetupCompleted(res.data.setup_completed))
      .catch(() => setSetupCompleted(false))
  }, [setSetupCompleted])

  // If setup not completed, force setup page
  if (!setupCompleted) {
    return (
      <Routes>
        <Route path="/setup" element={<Setup />} />
        <Route path="*" element={<Navigate to="/setup" replace />} />
      </Routes>
    )
  }

  // If not logged in, force login
  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/collections" element={<Collections />} />
        <Route path="/collections/:id" element={<CollectionDetail />} />
        <Route path="/gallery" element={<Gallery />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default App
