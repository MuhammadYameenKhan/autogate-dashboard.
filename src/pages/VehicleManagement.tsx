import { useEffect, useState } from 'react'
import { Plus, Edit, Trash2, Search } from 'lucide-react'
import './VehicleManagement.css'
import { apiService } from '../services/api'

interface Vehicle {
  id: string
  plateNumber: string
  ownerName: string
  department: string
  contact: string
  vehicleType: string
  status: 'active' | 'inactive'
}

const VehicleManagement = () => {
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingVehicle, setEditingVehicle] = useState<Vehicle | null>(null)
  const [formData, setFormData] = useState({
    plateNumber: '',
    ownerName: '',
    department: '',
    contact: '',
    vehicleType: 'car',
    status: 'active' as 'active' | 'inactive'
  })

  useEffect(() => {
    fetchVehicles()
  }, [])

  const fetchVehicles = async () => {
    try {
      const data = await apiService.getVehicles()
      setVehicles(data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching vehicles:', error)
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingVehicle(null)
    setFormData({
      plateNumber: '',
      ownerName: '',
      department: '',
      contact: '',
      vehicleType: 'car',
      status: 'active'
    })
    setShowModal(true)
  }

  const handleEdit = (vehicle: Vehicle) => {
    setEditingVehicle(vehicle)
    setFormData({
      plateNumber: vehicle.plateNumber,
      ownerName: vehicle.ownerName,
      department: vehicle.department,
      contact: vehicle.contact,
      vehicleType: vehicle.vehicleType,
      status: vehicle.status
    })
    setShowModal(true)
  }

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this vehicle?')) {
      try {
        await apiService.deleteVehicle(id)
        fetchVehicles()
      } catch (error) {
        console.error('Error deleting vehicle:', error)
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingVehicle) {
        await apiService.updateVehicle(editingVehicle.id, formData)
      } else {
        await apiService.createVehicle(formData)
      }
      setShowModal(false)
      fetchVehicles()
    } catch (error) {
      console.error('Error saving vehicle:', error)
    }
  }

  const filteredVehicles = vehicles.filter(vehicle =>
    vehicle.plateNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
    vehicle.ownerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
    vehicle.department.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="vehicle-management-page">
      <div className="page-header">
        <div>
          <h1>Vehicle Management</h1>
          <p className="page-subtitle">Register and manage campus vehicles</p>
        </div>
        <button className="add-btn" onClick={handleAdd}>
          <Plus size={20} />
          Add Vehicle
        </button>
      </div>

      <div className="vehicle-controls">
        <div className="search-box">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="Search vehicles..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
      </div>

      {loading ? (
        <div className="loading-container">Loading vehicles...</div>
      ) : (
        <div className="vehicle-table-container">
          <table className="vehicle-table">
            <thead>
              <tr>
                <th>License Plate</th>
                <th>Owner Name</th>
                <th>Department</th>
                <th>Contact</th>
                <th>Vehicle Type</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredVehicles.map((vehicle) => (
                <tr key={vehicle.id}>
                  <td>
                    <span className="plate-text">{vehicle.plateNumber}</span>
                  </td>
                  <td>{vehicle.ownerName}</td>
                  <td>{vehicle.department}</td>
                  <td>{vehicle.contact}</td>
                  <td>{vehicle.vehicleType}</td>
                  <td>
                    <span className={`status-badge status-${vehicle.status}`}>
                      {vehicle.status}
                    </span>
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button
                        className="edit-btn"
                        onClick={() => handleEdit(vehicle)}
                        title="Edit"
                      >
                        <Edit size={16} />
                      </button>
                      <button
                        className="delete-btn"
                        onClick={() => handleDelete(vehicle.id)}
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>{editingVehicle ? 'Edit Vehicle' : 'Add New Vehicle'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>License Plate *</label>
                <input
                  type="text"
                  required
                  value={formData.plateNumber}
                  onChange={(e) => setFormData({ ...formData, plateNumber: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Owner Name *</label>
                <input
                  type="text"
                  required
                  value={formData.ownerName}
                  onChange={(e) => setFormData({ ...formData, ownerName: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Department *</label>
                <input
                  type="text"
                  required
                  value={formData.department}
                  onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Contact</label>
                <input
                  type="text"
                  value={formData.contact}
                  onChange={(e) => setFormData({ ...formData, contact: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Vehicle Type</label>
                <select
                  value={formData.vehicleType}
                  onChange={(e) => setFormData({ ...formData, vehicleType: e.target.value })}
                >
                  <option value="car">Car</option>
                  <option value="motorcycle">Motorcycle</option>
                  <option value="truck">Truck</option>
                </select>
              </div>
              <div className="form-group">
                <label>Status</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>
              <div className="form-actions">
                <button type="button" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default VehicleManagement

