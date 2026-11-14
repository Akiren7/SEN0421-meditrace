import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { RequirePermission } from './components/RequirePermission'
import { homePath } from './lib/permissions'
import { AdminPage, LogsPage } from './pages/AdminLogsPages'
import { AlarmsPage } from './pages/AlarmsPage'
import { LoginPage } from './pages/LoginPage'
import { PatientDetailPage } from './pages/PatientDetailPage'
import { PatientListPage } from './pages/PatientListPage'
import { useSession } from './state/contexts'

function Home() {
  const { user } = useSession()
  return <Navigate to={user ? homePath(user.role) : '/login'} replace />
}

export function App() {
  const { user } = useSession()
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={user ? <Layout /> : <Navigate to="/login" replace />}>
        <Route
          path="/patients"
          element={
            <RequirePermission action="view_patients">
              <PatientListPage />
            </RequirePermission>
          }
        />
        <Route
          path="/patients/:patientId"
          element={
            <RequirePermission action="view_patients">
              <PatientDetailPage />
            </RequirePermission>
          }
        />
        <Route
          path="/alarms"
          element={
            <RequirePermission action="view_patients">
              <AlarmsPage />
            </RequirePermission>
          }
        />
        <Route
          path="/admin"
          element={
            <RequirePermission action="manage_devices_users">
              <AdminPage />
            </RequirePermission>
          }
        />
        <Route path="/logs" element={<LogsPage />} />
      </Route>
      <Route path="*" element={<Home />} />
    </Routes>
  )
}
