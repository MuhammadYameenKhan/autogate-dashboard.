import { useState, useEffect } from 'react'
import { Upload, FileText, CheckCircle, XCircle, Calendar, Clock, MapPin } from 'lucide-react'
import './TimetableUpload.css'
import { apiService } from '../services/api'
import { useAuth } from '../context/AuthContext'

interface ClassSchedule {
  day: string
  time: string
  building: string
  course: string
}

interface ExtractedSchedule {
  classes: ClassSchedule[]
  rawText: string
}

const TimetableUpload = () => {
  const { user } = useAuth()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [extractedSchedule, setExtractedSchedule] = useState<ExtractedSchedule | null>(null)
  const [savedSchedule, setSavedSchedule] = useState<ExtractedSchedule | null>(null)
  const [result, setResult] = useState<{
    success: boolean
    message: string
  } | null>(null)

  useEffect(() => {
    fetchSavedSchedule()
  }, [])

  const fetchSavedSchedule = async () => {
    try {
      const data = await apiService.getMyTimetable()
      if (data) {
        setSavedSchedule(data)
        setExtractedSchedule(data)
      }
    } catch (error) {
      console.error('Error fetching saved schedule:', error)
    }
  }

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
        setExtractedSchedule(null)
      } else {
        alert('Please select an image file (JPG, PNG, etc.)')
      }
    }
  }

  const handleExtract = async () => {
    if (!selectedFile) {
      alert('Please select an image file')
      return
    }

    setProcessing(true)
    setResult(null)

    try {
      const response = await apiService.extractTimetable(selectedFile)
      setExtractedSchedule(response)
      setResult({
        success: true,
        message: 'Timetable extracted successfully! Please review and save.'
      })
    } catch (error: any) {
      setResult({
        success: false,
        message: error.message || 'Failed to extract timetable. Please try again.'
      })
    } finally {
      setProcessing(false)
    }
  }

  const handleSave = async () => {
    if (!extractedSchedule) {
      alert('No schedule to save')
      return
    }

    setProcessing(true)
    try {
      await apiService.saveTimetable(extractedSchedule)
      setSavedSchedule(extractedSchedule)
      setResult({
        success: true,
        message: 'Timetable saved successfully! You will now receive smart parking suggestions.'
      })
      // Reset form
      setSelectedFile(null)
      setPreview(null)
    } catch (error: any) {
      setResult({
        success: false,
        message: error.message || 'Failed to save timetable.'
      })
    } finally {
      setProcessing(false)
    }
  }

  const handleUpdate = async () => {
    if (!extractedSchedule) {
      alert('No schedule to update')
      return
    }

    setProcessing(true)
    try {
      await apiService.updateTimetable(extractedSchedule)
      setSavedSchedule(extractedSchedule)
      setResult({
        success: true,
        message: 'Timetable updated successfully!'
      })
    } catch (error: any) {
      setResult({
        success: false,
        message: error.message || 'Failed to update timetable.'
      })
    } finally {
      setProcessing(false)
    }
  }

  const groupClassesByDay = (classes: ClassSchedule[]) => {
    const grouped: { [key: string]: ClassSchedule[] } = {}
    classes.forEach(cls => {
      if (!grouped[cls.day]) {
        grouped[cls.day] = []
      }
      grouped[cls.day].push(cls)
    })
    return grouped
  }

  return (
    <div className="timetable-upload-page">
      <div className="page-header">
        <h1>Timetable Management</h1>
        <p className="page-subtitle">Upload your timetable for smart parking suggestions</p>
      </div>

      <div className="timetable-container">
        {/* Upload Section */}
        <div className="upload-section-card">
          <h2>Upload Timetable</h2>
          <p className="section-description">
            Upload an image of your class timetable. Our system will extract your schedule 
            and suggest the nearest parking slot based on your classes.
          </p>

          <div className="upload-area">
            {preview ? (
              <div className="preview-container">
                <img src={preview} alt="Timetable preview" className="preview-image" />
                <button
                  type="button"
                  className="remove-image-btn"
                  onClick={() => {
                    setSelectedFile(null)
                    setPreview(null)
                    setExtractedSchedule(null)
                    setResult(null)
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

          {selectedFile && !extractedSchedule && (
            <button
              className="extract-btn"
              onClick={handleExtract}
              disabled={processing}
            >
              {processing ? 'Extracting...' : 'Extract Timetable'}
            </button>
          )}

          {result && (
            <div className={`result-message result-${result.success ? 'success' : 'error'}`}>
              {result.success ? (
                <>
                  <CheckCircle size={20} />
                  <p>{result.message}</p>
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

        {/* Extracted Schedule */}
        {extractedSchedule && (
          <div className="schedule-section-card">
            <div className="schedule-header">
              <h2>Extracted Schedule</h2>
              {savedSchedule && (
                <span className="update-badge">Update Available</span>
              )}
            </div>

            <div className="schedule-preview">
              {extractedSchedule.classes.length === 0 ? (
                <div className="no-classes">
                  <p>No classes found in the timetable. Please try with a clearer image.</p>
                </div>
              ) : (
                <div className="schedule-grid">
                  {Object.entries(groupClassesByDay(extractedSchedule.classes)).map(([day, classes]) => (
                    <div key={day} className="day-schedule">
                      <h3 className="day-header">{day}</h3>
                      {classes.map((cls, index) => (
                        <div key={index} className="class-item">
                          <div className="class-time">
                            <Clock size={14} />
                            <span>{cls.time}</span>
                          </div>
                          <div className="class-details">
                            <div className="class-course">{cls.course}</div>
                            <div className="class-building">
                              <MapPin size={14} />
                              <span>Building {cls.building}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="schedule-actions">
              {!savedSchedule ? (
                <button
                  className="save-btn"
                  onClick={handleSave}
                  disabled={processing || extractedSchedule.classes.length === 0}
                >
                  {processing ? 'Saving...' : 'Save Timetable'}
                </button>
              ) : (
                <button
                  className="update-btn"
                  onClick={handleUpdate}
                  disabled={processing}
                >
                  {processing ? 'Updating...' : 'Update Timetable'}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Saved Schedule Info */}
        {savedSchedule && !extractedSchedule && (
          <div className="saved-schedule-card">
            <h2>Your Saved Timetable</h2>
            <p className="info-text">
              Your timetable is saved. The system will suggest parking slots based on your classes.
            </p>
            <div className="schedule-stats">
              <div className="stat-item">
                <Calendar size={20} />
                <div>
                  <span className="stat-value">{savedSchedule.classes.length}</span>
                  <span className="stat-label">Total Classes</span>
                </div>
              </div>
              <div className="stat-item">
                <FileText size={20} />
                <div>
                  <span className="stat-value">{new Set(savedSchedule.classes.map(c => c.day)).size}</span>
                  <span className="stat-label">Days</span>
                </div>
              </div>
            </div>
            <button
              className="upload-new-btn"
              onClick={() => {
                setSelectedFile(null)
                setPreview(null)
                setExtractedSchedule(null)
              }}
            >
              Upload New Timetable
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default TimetableUpload

