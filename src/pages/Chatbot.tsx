import { useState, useRef, useEffect } from 'react'
import { Send, MessageCircle, ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import { apiService } from '../services/api'
import './Chatbot.css'

const Chatbot = () => {
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'bot', message: string }>>([
    { 
      role: 'bot', 
      message: 'Hello! I\'m the AutoGate assistant. I can help you with:\n• Parking availability\n• Vehicle entry/exit information\n• Daily/weekly summaries\n\nHow can I assist you today?' 
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', message: userMessage }])
    setLoading(true)

    try {
      const response = await apiService.sendChatbotMessage(userMessage)
      setMessages(prev => [...prev, { role: 'bot', message: response.message }])
    } catch (error) {
      console.error('Error sending chatbot message:', error)
      setMessages(prev => [...prev, { 
        role: 'bot', 
        message: 'Sorry, I encountered an error. Please try again or contact support.' 
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chatbot-page">
      <div className="chatbot-container">
        <div className="chatbot-header">
          <Link to="/" className="back-link">
            <ArrowLeft size={20} />
            Back
          </Link>
          <div className="chatbot-title">
            <MessageCircle size={24} />
            <h1>AutoGate Assistant</h1>
          </div>
          <div style={{ width: '80px' }}></div> {/* Spacer for centering */}
        </div>

        <div className="chatbot-messages-container">
          {messages.map((msg, index) => (
            <div key={index} className={`chatbot-message ${msg.role}`}>
              <div className="message-avatar">
                {msg.role === 'bot' ? (
                  <MessageCircle size={20} />
                ) : (
                  <div className="user-avatar">U</div>
                )}
              </div>
              <div className="message-content-wrapper">
                <div className="message-content">
                  {msg.message.split('\n').map((line, i) => (
                    <span key={i}>
                      {line}
                      {i < msg.message.split('\n').length - 1 && <br />}
                    </span>
                  ))}
                </div>
                <div className="message-time">
                  {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="chatbot-message bot">
              <div className="message-avatar">
                <MessageCircle size={20} />
              </div>
              <div className="message-content-wrapper">
                <div className="message-content">
                  <span className="typing-indicator">Thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form className="chatbot-input-container" onSubmit={handleSubmit}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me about parking availability, vehicle logs, or summaries..."
            className="chatbot-input"
            disabled={loading}
          />
          <button
            type="submit"
            className="chatbot-send-button"
            disabled={!input.trim() || loading}
          >
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  )
}

export default Chatbot

