import { useState } from 'react'
import { Upload, Image as ImageIcon, CheckCircle, XCircle } from 'lucide-react'
import './OfflineLogImport.css'
import { apiService } from '../services/api'

const OfflineLogImport = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    eventType: 'entry' as 'entry' | 'exit',
    timestamp: new Date().toISOString().slice(0, 16),
    gateId: 'gate1'
  })
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState<{
    success: boolean
    plateNumber?: string
    confidence?: number
    message: string
  } | null>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      if (file.type.startsWith('image/')) {
        setSelectedFile(file)
        const reader = new FileReader()
        reader.onloadend = () => {
          setPreview(reader.result as string)
        }
        reader.readAsDataURL(file)
        setResult(null)
      } else {
        alert('Please select an image file (JPG, PNG, etc.)')
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) {
      alert('Please select an image file')
      return
    }

    setProcessing(true)
    setResult(null)

    try {
      const response = await apiService.uploadOfflineImage(selectedFile, formData)
      setResult({
        success: true,
        plateNumber: response.plateNumber,
        confidence: response.confidence,
        message: 'License plate extracted successfully!'
      })
      // Reset form
      setSelectedFile(null)
      setPreview(null)
      setFormData({
        eventType: 'entry',
        timestamp: new Date().toISOString().slice(0, 16),
        gateId: 'gate1'
      })
    } catch (error: any) {
      setResult({
        success: false,
        message: error.message || 'Failed to process image. Please try again.'
      })
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="offline-import-page">
      <div className="page-header">
        <h1>Offline Log Import</h1>
        <p className="page-subtitle">Upload images for manual license plate recognition and log extraction</p>
      </div>

      <div className="import-container">
        <div className="import-card">
          <h2>Upload Image</h2>
          <form onSubmit={handleSubmit}>
            <div className="upload-section">
              <div className="upload-area">
                {preview ? (
                  <div className="preview-container">
                    <img src={preview} alt="Preview" className="preview-image" />
                    <button
                      type="button"
                      className="remove-image-btn"
                      onClick={() => {
                        setSelectedFile(null)
                        setPreview(null)
                      }}
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  <label className="upload-label">
                    <Upload size={48} className="upload-icon" />
                    <span>Click to upload or drag and drop</span>
                    <span className="upload-hint">JPG, PNG up to 10MB</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="file-input"
                    />
                  </label>
                )}
              </div>
            </div>

            <div className="form-section">
              <div className="form-group">
                <label>Event Type *</label>
                <select
                  value={formData.eventType}
                  onChange={(e) => setFormData({ ...formData, eventType: e.target.value as any })}
                  required
                >
                  <option value="entry">Entry</option>
                  <option value="exit">Exit</option>
                </select>
              </div>

              <div className="form-group">
                <label>Timestamp *</label>
                <input
                  type="datetime-local"
                  value={formData.timestamp}
                  onChange={(e) => setFormData({ ...formData, timestamp: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>Gate ID *</label>
                <input
                  type="text"
                  value={formData.gateId}
                  onChange={(e) => setFormData({ ...formData, gateId: e.target.value })}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="process-btn"
              disabled={!selectedFile || processing}
            >
              {processing ? 'Processing...' : 'Process Image'}
            </button>
          </form>

          {result && (
            <div className={`result-message result-${result.success ? 'success' : 'error'}`}>
              {result.success ? (
                <>
                  <CheckCircle size={20} />
                  <div>
                    <p><strong>{result.message}</strong></p>
                    {result.plateNumber && (
                      <p>License Plate: <strong>{result.plateNumber}</strong></p>
                    )}
                    {result.confidence !== undefined && (
                      <p>Confidence: <strong>{(result.confidence * 100).toFixed(1)}%</strong></p>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <XCircle size={20} />
                  <p>{result.message}</p>
                </>
              )}
            </div>
          )}
        </div>

        <div className="info-card">
          <h3>Instructions</h3>
          <ul>
            <li>Upload a clear image containing a visible license plate</li>
            <li>Supported formats: JPG, PNG (max 10MB)</li>
            <li>Ensure the license plate is clearly visible and readable</li>
            <li>Provide accurate timestamp and gate information</li>
            <li>The system will extract the plate number and create a log entry</li>
          </ul>
          <div className="info-note">
            <strong>Note:</strong> This feature is for offline log recovery when real-time 
            processing was unavailable (e.g., system downtime, camera failure).
          </div>
        </div>
      </div>
    </div>
  )
}

export default OfflineLogImport

