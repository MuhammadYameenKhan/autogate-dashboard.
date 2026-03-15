import { useEffect, useState } from 'react'
import { ParkingCircle, TrendingUp, TrendingDown } from 'lucide-react'
import './ParkingAvailability.css'
import { apiService } from '../services/api'

interface ParkingAvailabilityData {
  totalCapacity: number
  occupied: number
  available: number
  occupancyPercentage: number
  trend: 'up' | 'down' | 'stable'
}

const ParkingAvailability = () => {
  const [data, setData] = useState<ParkingAvailabilityData>({
    totalCapacity: 100,
    occupied: 0,
    available: 100,
    occupancyPercentage: 0,
    trend: 'stable'
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchParkingAvailability()
    // Refresh every 2 seconds for real-time updates
    const interval = setInterval(fetchParkingAvailability, 2000)
    return () => clearInterval(interval)
  }, [])

  const fetchParkingAvailability = async () => {
    try {
      const response = await apiService.getParkingAvailability()
      setData(response)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching parking availability:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="loading-container">Loading parking availability...</div>
  }

  const getStatusColor = () => {
    if (data.occupancyPercentage >= 90) return 'danger'
    if (data.occupancyPercentage >= 70) return 'warning'
    return 'success'
  }

  const statusColor = getStatusColor()

  return (
    <div className="parking-availability-page">
      <div className="page-header">
        <h1>Parking Availability</h1>
        <p className="page-subtitle">Real-time parking capacity and occupancy status</p>
      </div>

      <div className="availability-cards">
        <div className={`availability-card availability-card-${statusColor}`}>
          <div className="availability-header">
            <ParkingCircle className="availability-icon" size={32} />
            <div>
              <h2>Current Status</h2>
              <p className="availability-subtitle">Live parking information</p>
            </div>
          </div>
          <div className="availability-stats">
            <div className="stat-item">
              <span className="stat-label">Total Capacity</span>
              <span className="stat-value-large">{data.totalCapacity}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Occupied</span>
              <span className="stat-value-large">{data.occupied}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Available</span>
              <span className="stat-value-large">{data.available}</span>
            </div>
          </div>
        </div>

        <div className="occupancy-card">
          <h3>Occupancy Rate</h3>
          <div className="occupancy-display">
            <div className="occupancy-percentage">
              {data.occupancyPercentage}%
            </div>
            <div className="occupancy-bar-container">
              <div 
                className={`occupancy-bar occupancy-bar-${statusColor}`}
                style={{ width: `${data.occupancyPercentage}%` }}
              />
            </div>
          </div>
          <div className="trend-indicator">
            {data.trend === 'up' && (
              <>
                <TrendingUp size={16} />
                <span>Occupancy increasing</span>
              </>
            )}
            {data.trend === 'down' && (
              <>
                <TrendingDown size={16} />
                <span>Occupancy decreasing</span>
              </>
            )}
            {data.trend === 'stable' && (
              <span>Occupancy stable</span>
            )}
          </div>
        </div>
      </div>

      <div className="availability-info">
        <div className="info-card">
          <h3>Status Legend</h3>
          <div className="legend">
            <div className="legend-item">
              <div className="legend-color legend-success"></div>
              <span>Good (0-69% occupied)</span>
            </div>
            <div className="legend-item">
              <div className="legend-color legend-warning"></div>
              <span>Warning (70-89% occupied)</span>
            </div>
            <div className="legend-item">
              <div className="legend-color legend-danger"></div>
              <span>Critical (90-100% occupied)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ParkingAvailability

