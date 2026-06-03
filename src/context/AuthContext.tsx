import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiService } from '../services/api'

interface User {
  id: string
  username: string
  email: string
  role: 'admin' | 'security' | 'user'
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  signup: (username: string, email: string, password: string, userId: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const isJwtLike = (token: string | null) => {
  return typeof token === 'string' && token.split('.').length === 3
}

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('authToken')
    const userData = localStorage.getItem('userData')

    if (isJwtLike(token) && userData) {
      try {
        setUser(JSON.parse(userData))
      } catch (error) {
        localStorage.removeItem('authToken')
        localStorage.removeItem('userData')
      }
    } else if (token) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('userData')
    }
    setLoading(false)
  }, [])

  const login = async (username: string, password: string) => {
    try {
      const response = await apiService.login(username.trim(), password)
      if (!response?.token) {
        throw new Error('Login failed: no token received from server')
      }
      localStorage.setItem('authToken', response.token)
      localStorage.setItem('userData', JSON.stringify(response.user))
      setUser(response.user)
      navigate('/dashboard')
    } catch (error: any) {
      // Log full error for debugging network/auth issues (temporary)
      // This will surface network errors and axios response details in the browser console.
      // Remove or reduce verbosity once issue is resolved.
      // eslint-disable-next-line no-console
      console.error('Auth login error:', error)
      const msg = error.response?.data?.msg ||
        error.response?.data?.error ||
        error.message
      throw new Error(msg || 'Invalid username or password')
    }
  }

  const signup = async (username: string, email: string, password: string, userId: string) => {
    try {
      const response = await apiService.signup(username, email, password, userId)
      localStorage.setItem('authToken', response.token)
      localStorage.setItem('userData', JSON.stringify(response.user))
      setUser(response.user)
      navigate('/dashboard')
    } catch (error: any) {
      throw new Error(error.response?.data?.msg || error.response?.data?.error || 'Signup failed')
    }
  }

  const logout = () => {
    localStorage.removeItem('authToken')
    localStorage.removeItem('userData')
    setUser(null)
    navigate('/login')
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        signup,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

