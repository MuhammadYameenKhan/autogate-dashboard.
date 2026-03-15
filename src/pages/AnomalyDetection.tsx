import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle, XCircle, RefreshCw } from 'lucide-react'
import './AnomalyDetection.css'
import { apiService } from '../services/api'

interface Anomaly {
  id: string
  plateNumber: string
  timestamp: string
  anomalyType: string
  score: number
  reason: string
  severity: 'low' | 'medium' | 'high'
  status: 'active' | 'resolved' | 'false_positive'
}

const AnomalyDetection = () => {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'active' | 'resolved'>('all')

  useEffect(() => {
    fetchAnomalies()
    // Refresh every 5 seconds for real-time updates
    const interval = setInterval(fetchAnomalies, 5000)
    return () => clearInterval(interval)
  }, [filter])

  const fetchAnomalies = async () => {
    try {
      const data = await apiService.getAnomalies(filter)
      setAnomalies(data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching anomalies:', error)
      setLoading(false)
    }
  }

  const handleResolve = async (id: string) => {
    try {
      await apiService.resolveAnomaly(id)
      fetchAnomalies()
    } catch (error) {
      console.error('Error resolving anomaly:', error)
    }
  }

  const handleMarkFalsePositive = async (id: string) => {
    try {
      await apiService.markAnomalyFalsePositive(id)
      fetchAnomalies()
    } catch (error) {
      console.error('Error marking anomaly as false positive:', error)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'danger'
      case 'medium':
        return 'warning'
      default:
        return 'info'
    }
  }

  const activeAnomalies = anomalies.filter(a => a.status === 'active')
  const highSeverityAnomalies = activeAnomalies.filter(a => a.severity === 'high')

  if (loading) {
    return <div className="loading-container">Loading anomalies...</div>
  }

  return (
    <div className="anomaly-detection-page">
      <div className="page-header">
        <div>
          <h1>Anomaly Detection</h1>
          <p className="page-subtitle">Monitor and manage suspicious parking behaviors</p>
        </div>
        <div className="anomaly-controls">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="filter-select"
          >
            <option value="all">All Anomalies</option>
            <option value="active">Active Only</option>
            <option value="resolved">Resolved</option>
          </select>
          <button className="refresh-btn" onClick={fetchAnomalies}>
            <RefreshCw size={18} />
            Refresh
          </button>
        </div>
      </div>

      <div className="anomaly-stats">
        <div className="stat-card stat-card-danger">
          <div className="stat-header">
            <AlertTriangle className="stat-icon" size={24} />
            <h3>Active Anomalies</h3>
          </div>
          <div className="stat-value-large">{activeAnomalies.length}</div>
        </div>
        <div className="stat-card stat-card-warning">
          <div className="stat-header">
            <XCircle className="stat-icon" size={24} />
            <h3>High Severity</h3>
          </div>
          <div className="stat-value-large">{highSeverityAnomalies.length}</div>
        </div>
        <div className="stat-card stat-card-success">
          <div className="stat-header">
            <CheckCircle className="stat-icon" size={24} />
            <h3>Resolved</h3>
          </div>
          <div className="stat-value-large">
            {anomalies.filter(a => a.status === 'resolved').length}
          </div>
        </div>
      </div>

      {anomalies.length === 0 ? (
        <div className="empty-state">
          <CheckCircle size={48} className="empty-icon" />
          <h3>No Anomalies Detected</h3>
          <p>All parking activities appear normal.</p>
        </div>
      ) : (
        <div className="anomalies-list">
          {anomalies.map((anomaly) => (
            <div key={anomaly.id} className={`anomaly-card anomaly-${getSeverityColor(anomaly.severity)}`}>
              <div className="anomaly-header">
                <div className="anomaly-info">
                  <div className="anomaly-plate">
                    <AlertTriangle size={20} />
                    <span className="plate-text">{anomaly.plateNumber}</span>
                  </div>
                  <div className="anomaly-meta">
                    <span className="anomaly-type">{anomaly.anomalyType}</span>
                    <span className="anomaly-time">
                      {new Date(anomaly.timestamp).toLocaleString()}
                    </span>
                  </div>
                </div>
                <div className="anomaly-badges">
                  <span className={`severity-badge severity-${anomaly.severity}`}>
                    {anomaly.severity.toUpperCase()}
                  </span>
                  <span className={`status-badge status-${anomaly.status}`}>
                    {anomaly.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
              <div className="anomaly-body">
                <p className="anomaly-reason">{anomaly.reason}</p>
                <div className="anomaly-score">
                  Anomaly Score: <strong>{anomaly.score.toFixed(2)}</strong>
                </div>
              </div>
              {anomaly.status === 'active' && (
                <div className="anomaly-actions">
                  <button
                    className="resolve-btn"
                    onClick={() => handleResolve(anomaly.id)}
                  >
                    Mark as Resolved
                  </button>
                  <button
                    className="false-positive-btn"
                    onClick={() => handleMarkFalsePositive(anomaly.id)}
                  >
                    Mark as False Positive
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AnomalyDetection

