import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import DashboardLayout from './components/layout/DashboardLayout'
import Dashboard from './pages/Dashboard'
import ParkingAvailability from './pages/ParkingAvailability'
import CurrentlyParked from './pages/CurrentlyParked'
import LogsViewer from './pages/LogsViewer'
import VehicleManagement from './pages/VehicleManagement'
import Forecasting from './pages/Forecasting'
import AnomalyDetection from './pages/AnomalyDetection'
import OfflineLogImport from './pages/OfflineLogImport'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Chatbot from './pages/Chatbot'
import ParkingBooking from './pages/ParkingBooking'
import TimetableUpload from './pages/TimetableUpload'

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/chatbot" element={<Chatbot />} />

          {/* Protected Admin Routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="parking-availability" element={<ParkingAvailability />} />
            <Route path="currently-parked" element={<CurrentlyParked />} />
            <Route path="logs" element={<LogsViewer />} />
            <Route path="vehicles" element={<VehicleManagement />} />
            <Route path="forecasting" element={<Forecasting />} />
            <Route path="anomalies" element={<AnomalyDetection />} />
            <Route path="offline-import" element={<OfflineLogImport />} />
            <Route path="parking-booking" element={<ParkingBooking />} />
            <Route path="timetable" element={<TimetableUpload />} />
          </Route>

          {/* Catch all - redirect to dashboard */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  )
}

export default App

