import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'

export interface LogEntry {
  id: string
  plateNumber: string
  eventType: 'entry' | 'exit'
  timestamp: string
  gateId: string
  status: 'success' | 'failed'
  duration?: string
}

export interface GetLogsResponse {
  logs: LogEntry[]
  total: number
  page: number
  perPage: number
  pages: number
}

export interface ParkedVehicle {
  plateNumber: string
  ownerName: string
  department: string
  entryTime: string
  duration: string
}

export interface GetCurrentlyParkedResponse {
  vehicles: ParkedVehicle[]
  total: number
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for adding auth tokens
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('authToken')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const apiService = {
  // Dashboard
  getDashboardStats: async () => {
    return apiClient.get('/dashboard/stats')
  },

  // Parking Availability
  getParkingAvailability: async () => {
    return apiClient.get('/parking/availability')
  },

  // Currently Parked
  getCurrentlyParked: async (): Promise<GetCurrentlyParkedResponse> => {
    return apiClient.get('/parking/currently-parked')
  },

  // Logs
  getLogs: async (filters: {
    search?: string
    eventType?: string
    dateFrom?: string
    dateTo?: string
    status?: string
  }): Promise<GetLogsResponse> => {
    return apiClient.get('/logs', { params: filters })
  },

  exportLogs: async (): Promise<Blob | string> => {
    return apiClient.get('/logs/export', {
      responseType: 'blob',
      headers: {
        Accept: 'text/csv',
      },
    })
  },

  // Vehicle Management
  getVehicles: async () => {
    return apiClient.get('/vehicles')
  },

  createVehicle: async (data: {
    plateNumber: string
    ownerName: string
    department: string
    contact: string
    vehicleType: string
    status: string
  }) => {
    return apiClient.post('/vehicles', data)
  },

  updateVehicle: async (id: string, data: {
    plateNumber: string
    ownerName: string
    department: string
    contact: string
    vehicleType: string
    status: string
  }) => {
    return apiClient.put(`/vehicles/${id}`, data)
  },

  deleteVehicle: async (id: string) => {
    return apiClient.delete(`/vehicles/${id}`)
  },

  // Forecasting
  getForecast: async (period: '24h' | '48h' | '72h') => {
    return apiClient.get('/forecast', { params: { period } })
  },

  // Anomaly Detection
  getAnomalies: async (filter: 'all' | 'active' | 'resolved') => {
    return apiClient.get('/anomalies', { params: { filter } })
  },

  resolveAnomaly: async (id: string) => {
    return apiClient.post(`/anomalies/${id}/resolve`)
  },

  markAnomalyFalsePositive: async (id: string) => {
    return apiClient.post(`/anomalies/${id}/false-positive`)
  },

  // Offline Log Import
  uploadOfflineImage: async (file: File, metadata: {
    eventType: 'entry' | 'exit'
    timestamp: string
    gateId: string
  }) => {
    const formData = new FormData()
    formData.append('image', file)
    formData.append('eventType', metadata.eventType)
    formData.append('timestamp', metadata.timestamp)
    formData.append('gateId', metadata.gateId)

    return apiClient.post('/ocr/offline', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  // Chatbot
  sendChatbotMessage: async (message: string) => {
    return apiClient.post('/chatbot/message', { message })
  },

  // Emergency Stop
  emergencyStop: async () => {
    return apiClient.post('/gate/emergency-stop')
  },

  resetEmergencyStop: async () => {
    return apiClient.post('/gate/reset-emergency-stop')
  },

  // Authentication
  login: async (username: string, password: string) => {
    return apiClient.post('/auth/login', { username, password })
  },

  signup: async (username: string, email: string, password: string, userId: string) => {
    return apiClient.post('/auth/signup', { username, email, password, userId })
  },

  // Parking Booking
  getAvailableSlots: async (params: { date: string, time: string }) => {
    return apiClient.get('/parking/slots/available', { params })
  },

  bookParkingSlot: async (data: {
    slotId: string
    date: string
    time: string
    duration: number
    expiryTime: string
  }) => {
    return apiClient.post('/parking/book', data)
  },

  getMyBookings: async () => {
    return apiClient.get('/parking/bookings/my')
  },

  cancelBooking: async (bookingId: string) => {
    return apiClient.post(`/parking/bookings/${bookingId}/cancel`)
  },

  getSuggestedParkingSlot: async (params: { date: string, time: string }) => {
    return apiClient.get('/parking/suggested', { params })
  },

  // Timetable Management
  extractTimetable: async (file: File) => {
    const formData = new FormData()
    formData.append('image', file)

    return apiClient.post('/timetable/extract', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  saveTimetable: async (schedule: {
    classes: Array<{
      day: string
      time: string
      building: string
      course: string
    }>
    rawText: string
  }) => {
    return apiClient.post('/timetable/save', schedule)
  },

  updateTimetable: async (schedule: {
    classes: Array<{
      day: string
      time: string
      building: string
      course: string
    }>
    rawText: string
  }) => {
    return apiClient.put('/timetable/update', schedule)
  },

  getMyTimetable: async () => {
    return apiClient.get('/timetable/my')
  },
}

