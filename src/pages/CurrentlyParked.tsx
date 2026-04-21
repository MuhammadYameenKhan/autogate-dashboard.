import { useEffect, useState } from 'react'
import { Car, Clock, User } from 'lucide-react'
import './CurrentlyParked.css'
import { apiService } from '../services/api'

interface ParkedVehicle {
  plateNumber: string
  ownerName: string
  department: string
  entryTime: string
  duration: string
}

interface CurrentlyParkedApiResponse {
  vehicles?: ParkedVehicle[]
}

const CurrentlyParked = () => {
  const [vehicles, setVehicles] = useState<ParkedVehicle[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    fetchCurrentlyParked()
    // Refresh every 2 seconds for real-time updates
    const interval = setInterval(fetchCurrentlyParked, 2000)
    return () => clearInterval(interval)
  }, [])

  const fetchCurrentlyParked = async () => {
    try {
      const data = await apiService.getCurrentlyParked()
      if (Array.isArray(data)) {
        setVehicles(data)
      } else if (Array.isArray((data as CurrentlyParkedApiResponse)?.vehicles)) {
        setVehicles((data as CurrentlyParkedApiResponse).vehicles ?? [])
      } else {
        console.warn('Unexpected currently parked response shape:', data)
        setVehicles([])
      }
      setLoading(false)
    } catch (error) {
      console.error('Error fetching currently parked vehicles:', error)
      setVehicles([])
      setLoading(false)
    }
  }

  const safeVehicles = Array.isArray(vehicles) ? vehicles : []

  const filteredVehicles = safeVehicles.filter(vehicle =>
    vehicle.plateNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
    vehicle.ownerName.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (loading) {
    return <div className="loading-container">Loading currently parked vehicles...</div>
  }

  return (
    <div className="currently-parked-page">
      <div className="page-header">
        <h1>Currently Parked Vehicles</h1>
        <p className="page-subtitle">Real-time list of all vehicles currently on campus</p>
      </div>

      <div className="parked-controls">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search by plate number or owner name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        <div className="parked-count">
          <Car size={20} />
          <span>{filteredVehicles.length} vehicles currently parked</span>
        </div>
      </div>

      {filteredVehicles.length === 0 ? (
        <div className="empty-state">
          <Car size={48} className="empty-icon" />
          <h3>No vehicles currently parked</h3>
          <p>There are no vehicles on campus at this time.</p>
        </div>
      ) : (
        <div className="parked-table-container">
          <table className="parked-table">
            <thead>
              <tr>
                <th>License Plate</th>
                <th>Owner</th>
                <th>Department</th>
                <th>Entry Time</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {filteredVehicles.map((vehicle, index) => (
                <tr key={index}>
                  <td>
                    <div className="plate-number">
                      <Car size={16} />
                      <span className="plate-text">{vehicle.plateNumber}</span>
                    </div>
                  </td>
                  <td>
                    <div className="owner-info">
                      <User size={16} />
                      <span>{vehicle.ownerName}</span>
                    </div>
                  </td>
                  <td>{vehicle.department}</td>
                  <td>
                    <div className="time-info">
                      <Clock size={16} />
                      <span>{vehicle.entryTime}</span>
                    </div>
                  </td>
                  <td>
                    <span className="duration-badge">{vehicle.duration}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default CurrentlyParked

