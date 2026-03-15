import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TrendingUp, Calendar } from 'lucide-react'
import './Forecasting.css'
import { apiService } from '../services/api'

interface ForecastData {
  timestamp: string
  predictedOccupancy: number
  actualOccupancy?: number
}

const Forecasting = () => {
  const [forecastData, setForecastData] = useState<ForecastData[]>([])
  const [loading, setLoading] = useState(true)
  const [forecastPeriod, setForecastPeriod] = useState<'24h' | '48h' | '72h'>('24h')

  useEffect(() => {
    fetchForecast()
  }, [forecastPeriod])

  const fetchForecast = async () => {
    try {
      const data = await apiService.getForecast(forecastPeriod)
      setForecastData(data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching forecast:', error)
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    setLoading(true)
    fetchForecast()
  }

  if (loading) {
    return <div className="loading-container">Generating forecast...</div>
  }

  return (
    <div className="forecasting-page">
      <div className="page-header">
        <div>
          <h1>Parking Forecast</h1>
          <p className="page-subtitle">Predictive analytics for future parking availability</p>
        </div>
        <div className="forecast-controls">
          <select
            value={forecastPeriod}
            onChange={(e) => setForecastPeriod(e.target.value as any)}
            className="period-select"
          >
            <option value="24h">Next 24 Hours</option>
            <option value="48h">Next 48 Hours</option>
            <option value="72h">Next 72 Hours</option>
          </select>
          <button className="refresh-btn" onClick={handleRefresh}>
            Refresh
          </button>
        </div>
      </div>

      <div className="forecast-cards">
        <div className="forecast-card">
          <div className="forecast-card-header">
            <TrendingUp className="forecast-icon" size={24} />
            <div>
              <h3>Forecast Accuracy</h3>
              <p className="forecast-subtitle">Model Performance (MAPE)</p>
            </div>
          </div>
          <div className="forecast-metric">
            <span className="metric-value">8.5%</span>
            <span className="metric-label">Mean Absolute Percentage Error</span>
          </div>
        </div>

        <div className="forecast-card">
          <div className="forecast-card-header">
            <Calendar className="forecast-icon" size={24} />
            <div>
              <h3>Forecast Period</h3>
              <p className="forecast-subtitle">Time Range</p>
            </div>
          </div>
          <div className="forecast-metric">
            <span className="metric-value">{forecastPeriod}</span>
            <span className="metric-label">Prediction Horizon</span>
          </div>
        </div>
      </div>

      <div className="forecast-chart-container">
        <div className="chart-card">
          <h2>Occupancy Forecast</h2>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={forecastData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="timestamp" 
                tickFormatter={(value) => new Date(value).toLocaleTimeString()}
              />
              <YAxis 
                label={{ value: 'Occupancy %', angle: -90, position: 'insideLeft' }}
                domain={[0, 100]}
              />
              <Tooltip 
                labelFormatter={(value) => new Date(value).toLocaleString()}
                formatter={(value: number) => [`${value.toFixed(1)}%`, 'Occupancy']}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="predictedOccupancy" 
                stroke="#2563eb" 
                strokeWidth={2}
                name="Predicted Occupancy"
                dot={false}
              />
              {forecastData.some(d => d.actualOccupancy !== undefined) && (
                <Line 
                  type="monotone" 
                  dataKey="actualOccupancy" 
                  stroke="#10b981" 
                  strokeWidth={2}
                  name="Actual Occupancy"
                  dot={false}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="forecast-info">
        <div className="info-card">
          <h3>About the Forecast</h3>
          <p>
            This forecast uses the Prophet time-series model to predict parking occupancy 
            based on historical patterns. The model considers daily, weekly, and seasonal 
            trends to provide accurate predictions for the next 24-72 hours.
          </p>
          <p className="info-note">
            <strong>Note:</strong> Forecast accuracy may vary during special events, 
            holidays, or unusual campus activities.
          </p>
        </div>
      </div>
    </div>
  )
}

export default Forecasting

