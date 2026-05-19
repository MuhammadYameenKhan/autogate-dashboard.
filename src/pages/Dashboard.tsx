import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ParkingCircle, Car, FileText, AlertTriangle, Send, Video, Square, MessageCircle } from 'lucide-react'
import "./Dashboard.css"
import { apiService, type DashboardStats } from '../services/api'

const Dashboard = () => {
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats>({
    totalCapacity: 100,
    occupied: 0,
    available: 100,
    currentlyParked: 0,
    todayEntries: 0,
    todayExits: 0,
    activeAnomalies: 0
  })
  const [loading, setLoading] = useState(true)
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'bot', message: string }>>([
    { role: 'bot', message: 'Hello! I\'m the AutoGate assistant. How can I help you today?' }
  ])
  const [chatInput, setChatInput] = useState('')
  const [chatbotLoading, setChatbotLoading] = useState(false)
  const [emergencyStopActive, setEmergencyStopActive] = useState(false)
  const [gateStatus, setGateStatus] = useState<'idle' | 'processing' | 'open' | 'closed'>('idle')
  const chatEndRef = useRef<HTMLDivElement>(null)
  const cameraFeedRef = useRef<HTMLImageElement>(null)

  const quickActions = [
    { label: 'View All Logs', path: '/logs' },
    { label: 'Register Vehicle', path: '/vehicles' },
    { label: 'View Forecast', path: '/forecasting' },
    { label: 'Check Anomalies', path: '/anomalies' },
  ]

  useEffect(() => {
    fetchDashboardStats()
    // Refresh every 2 seconds for real-time updates
    const interval = setInterval(fetchDashboardStats, 2000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    // Scroll chat to bottom when new messages arrive
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  useEffect(() => {
    // Fetch live camera feed
    const updateCameraFeed = () => {
      if (cameraFeedRef.current) {
        // Update camera feed URL with timestamp to prevent caching
        const timestamp = new Date().getTime()
        cameraFeedRef.current.src = `${import.meta.env.VITE_CAMERA_FEED_URL || 'http://localhost:5000/api/camera/feed'}?t=${timestamp}`
      }
    }

    // Update camera feed every 500ms for live view
    const cameraInterval = setInterval(updateCameraFeed, 500)
    updateCameraFeed() // Initial load

    return () => clearInterval(cameraInterval)
  }, [])

  useEffect(() => {
    // Simulate gate status updates (in real implementation, this would come from WebSocket or API)
    const gateStatusInterval = setInterval(() => {
      // This would be replaced with actual gate status from backend
      // For now, we'll keep it as idle
    }, 1000)

    return () => clearInterval(gateStatusInterval)
  }, [])

  const fetchDashboardStats = async () => {
    try {
      const data = await apiService.getDashboardStats()
      setStats(data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching dashboard stats:', error)
      setLoading(false)
    }
  }

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim() || chatbotLoading) return

    const userMessage = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', message: userMessage }])
    setChatbotLoading(true)

    try {
      // Send message to chatbot API
      const response = await apiService.sendChatbotMessage(userMessage)
      setChatMessages(prev => [...prev, { role: 'bot', message: response.message }])
    } catch (error) {
      console.error('Error sending chatbot message:', error)
      setChatMessages(prev => [...prev, {
        role: 'bot',
        message: 'Sorry, I encountered an error. Please try again.'
      }])
    } finally {
      setChatbotLoading(false)
    }
  }

  const handleEmergencyStop = async () => {
    if (window.confirm('Are you sure you want to activate emergency stop? This will immediately close the gate.')) {
      try {
        await apiService.emergencyStop()
        setEmergencyStopActive(true)
        setGateStatus('closed')
        // Show alert
        alert('Emergency stop activated! Gate is now closed.')
      } catch (error) {
        console.error('Error activating emergency stop:', error)
        alert('Failed to activate emergency stop. Please try again.')
      }
    }
  }

  const handleResetEmergencyStop = async () => {
    try {
      await apiService.resetEmergencyStop()
      setEmergencyStopActive(false)
      setGateStatus('idle')
      alert('Emergency stop reset. System is back to normal operation.')
    } catch (error) {
      console.error('Error resetting emergency stop:', error)
    }
  }

  const occupancyPercentage = stats.totalCapacity > 0
    ? Math.round((stats.occupied / stats.totalCapacity) * 100)
    : 0

  const statCards = [
    {
      title: 'Parking Availability',
      value: `${stats.available} / ${stats.totalCapacity}`,
      subtitle: `${occupancyPercentage}% Occupied`,
      icon: ParkingCircle,
      color: 'blue',
      trend: stats.available > 20 ? 'good' : stats.available > 10 ? 'warning' : 'danger'
    },
    {
      title: 'Currently Parked',
      value: stats.currentlyParked.toString(),
      subtitle: 'Vehicles on campus',
      icon: Car,
      color: 'green'
    },
    {
      title: 'Today\'s Entries',
      value: stats.todayEntries.toString(),
      subtitle: 'Vehicles entered',
      icon: FileText,
      color: 'blue'
    },
    {
      title: 'Active Anomalies',
      value: stats.activeAnomalies.toString(),
      subtitle: 'Requires attention',
      icon: AlertTriangle,
      color: stats.activeAnomalies > 0 ? 'red' : 'gray'
    }
  ]

  if (loading) {
    return <div className="loading-container">Loading dashboard...</div>
  }

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <h1>Dashboard Overview</h1>
        <p className="page-subtitle">Real-time parking management and monitoring</p>
      </div>

      <div className="stats-grid">
        {statCards.map((card, index) => {
          const Icon = card.icon
          return (
            <div key={index} className={`stat-card stat-card-${card.color}`}>
              <div className="stat-card-header">
                <div className="stat-icon-wrapper">
                  <Icon className="stat-icon" size={24} />
                </div>
                <h3 className="stat-title">{card.title}</h3>
              </div>
              <div className="stat-content">
                <div className="stat-value">{card.value}</div>
                <div className="stat-subtitle">{card.subtitle}</div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="dashboard-main-grid">
        {/* Live Camera Feed Section */}
        <div className="camera-section">
          <div className="camera-card">
            <div className="camera-header">
              <Video size={20} />
              <h2>Live Gate Camera</h2>
              <div className={`gate-status-indicator status-${gateStatus}`}>
                <span className="status-dot"></span>
                <span className="status-text">
                  {gateStatus === 'idle' && 'Idle'}
                  {gateStatus === 'processing' && 'Processing...'}
                  {gateStatus === 'open' && 'Gate Open'}
                  {gateStatus === 'closed' && 'Gate Closed'}
                </span>
              </div>
            </div>
            <div className="camera-feed-container">
              <img
                ref={cameraFeedRef}
                className="camera-feed"
                alt="Live gate camera feed"
                onError={(e) => {
                  // Fallback if camera feed is unavailable
                  const target = e.target as HTMLImageElement
                  target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="800" height="450"%3E%3Crect fill="%23f1f5f9" width="800" height="450"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%2394a3b8" font-family="sans-serif" font-size="24"%3ECamera Feed Unavailable%3C/text%3E%3C/svg%3E'
                }}
              />
            </div>
            <div className="camera-controls">
              <button
                className={`emergency-stop-btn ${emergencyStopActive ? 'active' : ''}`}
                onClick={emergencyStopActive ? handleResetEmergencyStop : handleEmergencyStop}
              >
                <Square size={20} />
                {emergencyStopActive ? 'Reset Emergency Stop' : 'Emergency Stop'}
              </button>
            </div>
          </div>
        </div>

        {/* Chatbot Section */}
        <div className="chatbot-section">
          <div className="chatbot-card">
            <div className="chatbot-header">
              <MessageCircle size={20} />
              <h2>AutoGate Assistant</h2>
            </div>
            <div className="chatbot-messages">
              {chatMessages.map((msg, index) => (
                <div key={index} className={`chat-message ${msg.role}`}>
                  <div className="message-content">
                    {msg.message}
                  </div>
                </div>
              ))}
              {chatbotLoading && (
                <div className="chat-message bot">
                  <div className="message-content">
                    <span className="typing-indicator">Thinking...</span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
            <form className="chatbot-input-form" onSubmit={handleChatSubmit}>
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask about parking availability, vehicle logs, or summaries..."
                className="chatbot-input"
                disabled={chatbotLoading}
              />
              <button
                type="submit"
                className="chatbot-send-btn"
                disabled={!chatInput.trim() || chatbotLoading}
              >
                <Send size={18} />
              </button>
            </form>
          </div>
        </div>
      </div>

      <div className="dashboard-sections">
        <div className="dashboard-section">
          <h2>Quick Actions</h2>
          <div className="quick-actions">
            {quickActions.map((action) => (
              <button
                key={action.label}
                type="button"
                className="action-btn"
                onClick={() => navigate(action.path)}
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard

