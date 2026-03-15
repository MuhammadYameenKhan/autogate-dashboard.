import { useEffect, useState } from 'react'
import { FileText, Search, Filter, Download } from 'lucide-react'
import './LogsViewer.css'
import { apiService } from '../services/api'

interface LogEntry {
  id: string
  plateNumber: string
  eventType: 'entry' | 'exit'
  timestamp: string
  gateId: string
  status: 'success' | 'failed'
  duration?: string
}

const LogsViewer = () => {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    search: '',
    eventType: 'all' as 'all' | 'entry' | 'exit',
    dateFrom: '',
    dateTo: '',
    status: 'all' as 'all' | 'success' | 'failed'
  })

  useEffect(() => {
    fetchLogs()
  }, [filters])

  const fetchLogs = async () => {
    try {
      const data = await apiService.getLogs(filters)
      setLogs(data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching logs:', error)
      setLoading(false)
    }
  }

  const handleExport = () => {
    // Export functionality
    console.log('Exporting logs...')
  }

  const filteredLogs = logs.filter(log => {
    if (filters.search && !log.plateNumber.toLowerCase().includes(filters.search.toLowerCase())) {
      return false
    }
    if (filters.eventType !== 'all' && log.eventType !== filters.eventType) {
      return false
    }
    if (filters.status !== 'all' && log.status !== filters.status) {
      return false
    }
    return true
  })

  return (
    <div className="logs-viewer-page">
      <div className="page-header">
        <h1>Entry/Exit Logs</h1>
        <p className="page-subtitle">View and filter historical vehicle entry and exit records</p>
      </div>

      <div className="logs-controls">
        <div className="filters-section">
          <div className="filter-group">
            <Search size={18} className="filter-icon" />
            <input
              type="text"
              placeholder="Search by plate number..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="filter-input"
            />
          </div>

          <div className="filter-group">
            <Filter size={18} className="filter-icon" />
            <select
              value={filters.eventType}
              onChange={(e) => setFilters({ ...filters, eventType: e.target.value as any })}
              className="filter-select"
            >
              <option value="all">All Events</option>
              <option value="entry">Entry Only</option>
              <option value="exit">Exit Only</option>
            </select>
          </div>

          <div className="filter-group">
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value as any })}
              className="filter-select"
            >
              <option value="all">All Status</option>
              <option value="success">Success</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div className="filter-group">
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
              className="filter-input"
              placeholder="From Date"
            />
          </div>

          <div className="filter-group">
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
              className="filter-input"
              placeholder="To Date"
            />
          </div>

          <button className="export-btn" onClick={handleExport}>
            <Download size={18} />
            Export
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-container">Loading logs...</div>
      ) : filteredLogs.length === 0 ? (
        <div className="empty-state">
          <FileText size={48} className="empty-icon" />
          <h3>No logs found</h3>
          <p>No log entries match your filter criteria.</p>
        </div>
      ) : (
        <div className="logs-table-container">
          <table className="logs-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>License Plate</th>
                <th>Event Type</th>
                <th>Gate ID</th>
                <th>Status</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => (
                <tr key={log.id}>
                  <td>{new Date(log.timestamp).toLocaleString()}</td>
                  <td>
                    <span className="plate-text">{log.plateNumber}</span>
                  </td>
                  <td>
                    <span className={`event-badge event-${log.eventType}`}>
                      {log.eventType.toUpperCase()}
                    </span>
                  </td>
                  <td>{log.gateId}</td>
                  <td>
                    <span className={`status-badge status-${log.status}`}>
                      {log.status}
                    </span>
                  </td>
                  <td>{log.duration || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default LogsViewer

