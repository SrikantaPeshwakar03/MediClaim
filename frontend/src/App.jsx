import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import UploadPage from './pages/UploadPage'
import StatusPage from './pages/StatusPage'
import DecisionPage from './pages/DecisionPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/status/:claimId" element={<StatusPage />} />
        <Route path="/decision/:claimId" element={<DecisionPage />} />
      </Routes>
    </Layout>
  )
}

export default App
