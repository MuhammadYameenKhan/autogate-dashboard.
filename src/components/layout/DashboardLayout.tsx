import { useState } from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { 
  LayoutDashboard, 
  Car, 
  ParkingCircle, 
  FileText, 
  Users, 
  TrendingUp, 
  AlertTriangle,
  Upload,
  Calendar,
  BookOpen,
  Menu,
  X,
  LogOut
} from 'lucide-react'
import './DashboardLayout.css'

const DashboardLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { user, logout } = useAuth()

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Parking Availability', href: '/parking-availability', icon: ParkingCircle },
    { name: 'Book Parking Slot', href: '/parking-booking', icon: Calendar },
    { name: 'My Timetable', href: '/timetable', icon: BookOpen },
    { name: 'Currently Parked', href: '/currently-parked', icon: Car },
    { name: 'Entry/Exit Logs', href: '/logs', icon: FileText },
    { name: 'Vehicle Management', href: '/vehicles', icon: Users },
    { name: 'Forecasting', href: '/forecasting', icon: TrendingUp },
    { name: 'Anomaly Detection', href: '/anomalies', icon: AlertTriangle },
    { name: 'Offline Import', href: '/offline-import', icon: Upload },
  ]

  return (
    <div className="dashboard-container">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <div className="logo">
            <Car className="logo-icon" />
            <h1 className="logo-text">AutoGate</h1>
          </div>
          <button 
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle sidebar"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        <nav className="sidebar-nav">
          {navigation.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  `nav-link ${isActive ? 'active' : ''}`
                }
              >
                <Icon className="nav-icon" size={20} />
                {sidebarOpen && <span className="nav-text">{item.name}</span>}
              </NavLink>
            )
          })}
        </nav>

        <div className="sidebar-footer">
          <button className="logout-btn" onClick={logout}>
            <LogOut size={20} />
            {sidebarOpen && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="top-header">
          <div className="header-content">
            <h2 className="page-title">Admin Dashboard</h2>
            <div className="header-actions">
              <div className="user-info">
                <span className="user-name">{user?.username || 'User'}</span>
                <span className="user-role">({user?.role || 'user'})</span>
              </div>
            </div>
          </div>
        </header>

        <div className="content-wrapper">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default DashboardLayout

