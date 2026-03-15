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

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('authToken')
    const userData = localStorage.getItem('userData')
    
    if (token && userData) {
      try {
        setUser(JSON.parse(userData))
      } catch (error) {
        localStorage.removeItem('authToken')
        localStorage.removeItem('userData')
      }
    }
    setLoading(false)
  }, [])

  const login = async (username: string, password: string) => {
    // PROTOTYPE MODE: Hardcoded credentials for demo
    // TODO: Replace with actual API call when backend is ready
    
    // Demo credentials
    const demoCredentials = {
      username: 'admin',
      password: 'admin123',
      userId: 'ADMIN001'
    }

    // Check hardcoded credentials
    if (username.toLowerCase() === demoCredentials.username && password === demoCredentials.password) {
      const demoUser: User = {
        id: demoCredentials.userId,
        username: demoCredentials.username,
        email: 'admin@autogate.com',
        role: 'admin'
      }
      
      localStorage.setItem('authToken', 'demo-token-' + Date.now())
      localStorage.setItem('userData', JSON.stringify(demoUser))
      setUser(demoUser)
      navigate('/dashboard')
      return
    }

    // Try API call if credentials don't match (for future use)
    try {
      const response = await apiService.login(username, password)
      localStorage.setItem('authToken', response.token)
      localStorage.setItem('userData', JSON.stringify(response.user))
      setUser(response.user)
      navigate('/dashboard')
    } catch (error: any) {
      throw new Error('Invalid username or password. Use: admin / admin123')
    }
  }

  const signup = async (username: string, email: string, password: string, userId: string) => {
    // PROTOTYPE MODE: Store locally for demo
    // TODO: Replace with actual API call when backend is ready
    
    // For now, just create a local user and log them in
    const newUser: User = {
      id: userId,
      username: username,
      email: email,
      role: 'user' // Default role for new signups
    }
    
    localStorage.setItem('authToken', 'demo-token-' + Date.now())
    localStorage.setItem('userData', JSON.stringify(newUser))
    setUser(newUser)
    navigate('/dashboard')
    
    // Uncomment when backend is ready:
    // try {
    //   const response = await apiService.signup(username, email, password, userId)
    //   localStorage.setItem('authToken', response.token)
    //   localStorage.setItem('userData', JSON.stringify(response.user))
    //   setUser(response.user)
    //   navigate('/dashboard')
    // } catch (error: any) {
    //   throw new Error(error.response?.data?.message || 'Signup failed')
    // }
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

