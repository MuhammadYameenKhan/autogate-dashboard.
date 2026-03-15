import { useEffect, useState } from 'react'
import { Calendar, Clock, MapPin, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import './ParkingBooking.css'
import { apiService } from '../services/api'
import { useAuth } from '../context/AuthContext'

interface Booking {
  id: string
  slotId: string
  slotLocation: string
  bookingTime: string
  expiryTime: string
  status: 'active' | 'expired' | 'completed' | 'cancelled'
  building: string
}

interface AvailableSlot {
  id: string
  location: string
  building: string
  distance: number
  available: boolean
}

const ParkingBooking = () => {
  const { user } = useAuth()
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const [selectedTime, setSelectedTime] = useState('')
  const [duration, setDuration] = useState(30) // minutes
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null)
  const [availableSlots, setAvailableSlots] = useState<AvailableSlot[]>([])
  const [myBookings, setMyBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(false)
  const [suggestedSlot, setSuggestedSlot] = useState<AvailableSlot | null>(null)

  useEffect(() => {
    fetchMyBookings()
    fetchAvailableSlots()
    fetchSuggestedSlot()
  }, [])

  useEffect(() => {
    if (selectedDate && selectedTime) {
      fetchAvailableSlots()
      fetchSuggestedSlot()
    }
  }, [selectedDate, selectedTime])

  const fetchMyBookings = async () => {
    try {
      const data = await apiService.getMyBookings()
      setMyBookings(data)
    } catch (error) {
      console.error('Error fetching bookings:', error)
    }
  }

  const fetchAvailableSlots = async () => {
    try {
      const data = await apiService.getAvailableSlots({
        date: selectedDate,
        time: selectedTime
      })
      setAvailableSlots(data)
    } catch (error) {
      console.error('Error fetching available slots:', error)
    }
  }

  const fetchSuggestedSlot = async () => {
    try {
      const data = await apiService.getSuggestedParkingSlot({
        date: selectedDate,
        time: selectedTime
      })
      if (data) {
        setSuggestedSlot(data)
      }
    } catch (error) {
      console.error('Error fetching suggested slot:', error)
    }
  }

  const handleBookSlot = async () => {
    if (!selectedSlot || !selectedDate || !selectedTime) {
      alert('Please select a slot, date, and time')
      return
    }

    setLoading(true)
    try {
      const expiryTime = new Date(`${selectedDate}T${selectedTime}`)
      expiryTime.setMinutes(expiryTime.getMinutes() + duration)

      await apiService.bookParkingSlot({
        slotId: selectedSlot,
        date: selectedDate,
        time: selectedTime,
        duration: duration,
        expiryTime: expiryTime.toISOString()
      })

      alert('Parking slot booked successfully!')
      setSelectedSlot(null)
      fetchMyBookings()
      fetchAvailableSlots()
    } catch (error: any) {
      alert(error.message || 'Failed to book slot. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleCancelBooking = async (bookingId: string) => {
    if (window.confirm('Are you sure you want to cancel this booking?')) {
      try {
        await apiService.cancelBooking(bookingId)
        fetchMyBookings()
        fetchAvailableSlots()
      } catch (error) {
        alert('Failed to cancel booking')
      }
    }
  }

  const getBookingStatus = (booking: Booking) => {
    const now = new Date()
    const expiry = new Date(booking.expiryTime)

    if (booking.status === 'completed' || booking.status === 'cancelled') {
      return booking.status
    }

    if (now > expiry) {
      return 'expired'
    }

    return 'active'
  }

  const formatTime = (timeString: string) => {
    return new Date(timeString).toLocaleString()
  }

  return (
    <div className="parking-booking-page">
      <div className="page-header">
        <h1>Parking Slot Booking</h1>
        <p className="page-subtitle">Book your parking slot in advance</p>
      </div>

      <div className="booking-grid">
        {/* Booking Form */}
        <div className="booking-form-card">
          <h2>Book a Slot</h2>

          {suggestedSlot && (
            <div className="suggested-slot-banner">
              <AlertCircle size={20} />
              <div>
                <strong>Smart Suggestion:</strong>
                <p>Based on your timetable, we suggest parking at <strong>{suggestedSlot.location}</strong> 
                (Building {suggestedSlot.building}) - {suggestedSlot.distance}m away</p>
              </div>
            </div>
          )}

          <div className="form-section">
            <div className="form-group">
              <label>
                <Calendar size={18} />
                Date
              </label>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
              />
            </div>

            <div className="form-group">
              <label>
                <Clock size={18} />
                Time
              </label>
              <input
                type="time"
                value={selectedTime}
                onChange={(e) => setSelectedTime(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>
                <Clock size={18} />
                Arrival Window (minutes)
              </label>
              <select
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
              >
                <option value={15}>15 minutes</option>
                <option value={30}>30 minutes</option>
                <option value={45}>45 minutes</option>
                <option value={60}>60 minutes</option>
              </select>
              <p className="form-hint">
                You must arrive within {duration} minutes of the selected time, or your booking will be cancelled.
              </p>
            </div>
          </div>

          <div className="slots-section">
            <h3>Available Slots</h3>
            {availableSlots.length === 0 ? (
              <p className="no-slots">No available slots for selected date/time</p>
            ) : (
              <div className="slots-grid">
                {availableSlots.map((slot) => (
                  <div
                    key={slot.id}
                    className={`slot-card ${selectedSlot === slot.id ? 'selected' : ''} ${!slot.available ? 'unavailable' : ''}`}
                    onClick={() => slot.available && setSelectedSlot(slot.id)}
                  >
                    <div className="slot-header">
                      <MapPin size={16} />
                      <span className="slot-location">{slot.location}</span>
                    </div>
                    <div className="slot-details">
                      <span>Building {slot.building}</span>
                      <span className="slot-distance">{slot.distance}m away</span>
                    </div>
                    {selectedSlot === slot.id && (
                      <CheckCircle className="selected-icon" size={20} />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <button
            className="book-btn"
            onClick={handleBookSlot}
            disabled={!selectedSlot || loading || !selectedDate || !selectedTime}
          >
            {loading ? 'Booking...' : 'Book Slot'}
          </button>
        </div>

        {/* My Bookings */}
        <div className="bookings-list-card">
          <h2>My Bookings</h2>
          {myBookings.length === 0 ? (
            <div className="no-bookings">
              <p>You have no active bookings</p>
            </div>
          ) : (
            <div className="bookings-list">
              {myBookings.map((booking) => {
                const status = getBookingStatus(booking)
                return (
                  <div key={booking.id} className={`booking-item booking-${status}`}>
                    <div className="booking-header">
                      <div>
                        <h4>{booking.slotLocation}</h4>
                        <p>Building {booking.building}</p>
                      </div>
                      <span className={`status-badge status-${status}`}>
                        {status.charAt(0).toUpperCase() + status.slice(1)}
                      </span>
                    </div>
                    <div className="booking-details">
                      <div className="detail-item">
                        <Clock size={14} />
                        <span>Booked: {formatTime(booking.bookingTime)}</span>
                      </div>
                      <div className="detail-item">
                        <Clock size={14} />
                        <span>Expires: {formatTime(booking.expiryTime)}</span>
                      </div>
                    </div>
                    {status === 'active' && (
                      <button
                        className="cancel-btn"
                        onClick={() => handleCancelBooking(booking.id)}
                      >
                        Cancel Booking
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ParkingBooking

