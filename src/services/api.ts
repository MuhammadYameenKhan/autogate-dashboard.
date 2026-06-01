import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api'
export interface DashboardStats {
  totalCapacity: number
  occupied: number
  available: number
  currentlyParked: number
  todayEntries: number
  todayExits: number
  activeAnomalies: number
}

export interface ChatbotMessageResponse {
  message: string
}

export interface AuthUserResponse {
  id: string
  username: string
  email: string
  role: 'admin' | 'security' | 'user'
}

export interface AuthResponse {
  token: string
  refresh_token?: string
  user: AuthUserResponse
}

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

export interface LiveOcrResponse {
  plateNumber: string
  confidence: number
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

const isJwtLike = (token: string | null) => {
  return typeof token === 'string' && token.split('.').length === 3
}

// Response interceptor already returns response.data; do not read .data again.
const unwrap = async <T>(request: Promise<T>): Promise<T> => {
  return request
}

// Request interceptor for adding auth tokens
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (isJwtLike(token)) {
      config.headers.Authorization = `Bearer ${token}`
    } else if (token) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('userData')
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
    const isAuthRequest = error.config?.url?.includes('/auth/login') ||
      error.config?.url?.includes('/auth/signup')
    if (!isAuthRequest && (error.response?.status === 401 || error.response?.status === 422)) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('userData')
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const apiService = {
  // Dashboard
  getDashboardStats: async (): Promise<DashboardStats> => {
    return unwrap(apiClient.get<DashboardStats>('/dashboard/stats'))
  },

  // Parking Availability
  getParkingAvailability: async (): Promise<{ totalCapacity: number; occupied: number; available: number; occupancyPercentage: number; trend: string; lastUpdated: string }> => {
    return unwrap(apiClient.get('/parking/availability'))
  },

  // Currently Parked
  getCurrentlyParked: async (): Promise<GetCurrentlyParkedResponse> => {
    return unwrap(apiClient.get<GetCurrentlyParkedResponse>('/parking/currently-parked'))
  },

  // Logs
  getLogs: async (filters: {
    search?: string
    eventType?: string
    dateFrom?: string
    dateTo?: string
    status?: string
  }): Promise<GetLogsResponse> => {
    return unwrap(apiClient.get<GetLogsResponse>('/logs', { params: filters }))
  },

  exportLogs: async (): Promise<Blob | string> => {
    return unwrap(apiClient.get('/logs/export', {
      responseType: 'blob',
      headers: {
        Accept: 'text/csv',
      },
    }))
  },

  // Vehicle Management
  getVehicles: async (): Promise<unknown[]> => {
    return unwrap(apiClient.get<unknown[]>('/vehicles'))
  },

  createVehicle: async (data: {
    plateNumber: string
    ownerName: string
    department: string
    contact: string
    vehicleType: string
    status: string
  }) => {
    return unwrap(apiClient.post('/vehicles', data))
  },

  updateVehicle: async (id: string, data: {
    plateNumber: string
    ownerName: string
    department: string
    contact: string
    vehicleType: string
    status: string
  }) => {
    return unwrap(apiClient.put(`/vehicles/${id}`, data))
  },

  deleteVehicle: async (id: string) => {
    return unwrap(apiClient.delete(`/vehicles/${id}`))
  },

  // Forecasting
  getForecast: async (period: '24h' | '48h' | '72h'): Promise<unknown[]> => {
    return unwrap(apiClient.get<unknown[]>('/forecast', { params: { period } }))
  },

  // Anomaly Detection
  getAnomalies: async (filter: 'all' | 'active' | 'resolved'): Promise<unknown[]> => {
    return unwrap(apiClient.get<unknown[]>('/anomalies', { params: { filter } }))
  },

  resolveAnomaly: async (id: string) => {
    return unwrap(apiClient.post(`/anomalies/${id}/resolve`))
  },

  markAnomalyFalsePositive: async (id: string) => {
    return unwrap(apiClient.post(`/anomalies/${id}/false-positive`))
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

    return unwrap(apiClient.post('/ocr/offline', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }))
  },

  // Live OCR (browser camera frames)
  liveRecognize: async (file: File): Promise<LiveOcrResponse> => {
    const formData = new FormData()
    formData.append('image', file)

    return apiClient.post('/ocr/live', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  // Chatbot
  sendChatbotMessage: async (message: string): Promise<ChatbotMessageResponse> => {
    return unwrap(apiClient.post<ChatbotMessageResponse>(
      '/chatbot/message',
      { message },
      { timeout: 15000 },
    ))
  },

  // Emergency Stop
  emergencyStop: async () => {
    return unwrap(apiClient.post('/gate/emergency-stop'))
  },

  resetEmergencyStop: async () => {
    return unwrap(apiClient.post('/gate/reset-emergency-stop'))
  },

  // Authentication
  login: async (username: string, password: string): Promise<AuthResponse> => {
    return unwrap(apiClient.post<AuthResponse>('/auth/login', { username, password }))
  },

  signup: async (username: string, email: string, password: string, userId: string): Promise<AuthResponse> => {
    return unwrap(apiClient.post<AuthResponse>('/auth/signup', { username, email, password, userId }))
  },

  // Parking Booking
  getAvailableSlots: async (params: { date: string, time: string }): Promise<unknown[]> => {
    return unwrap(apiClient.get<unknown[]>('/parking/slots/available', { params }))
  },

  bookParkingSlot: async (data: {
    slotId: string
    date: string
    time: string
    duration: number
    expiryTime: string
  }) => {
    return unwrap(apiClient.post('/parking/book', data))
  },

  getMyBookings: async () => {
    return unwrap(apiClient.get<unknown[]>('/parking/bookings/my'))
  },

  cancelBooking: async (bookingId: string) => {
    return unwrap(apiClient.post(`/parking/bookings/${bookingId}/cancel`))
  },

  getSuggestedParkingSlot: async (params: { date: string, time: string }): Promise<unknown | null> => {
    return unwrap(apiClient.get<unknown | null>('/parking/suggested', { params }))
  },

  // Timetable Management
  extractTimetable: async (file: File) => {
    const formData = new FormData()
    formData.append('image', file)

    return unwrap(apiClient.post('/timetable/extract', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }))
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
    return unwrap(apiClient.post('/timetable/save', schedule))
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
    return unwrap(apiClient.put('/timetable/update', schedule))
  },

  getMyTimetable: async () => {
    return unwrap(apiClient.get<unknown>('/timetable/my'))
  },
}

