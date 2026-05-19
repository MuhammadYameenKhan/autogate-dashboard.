"""
Chatbot Routes: /api/chatbot/
Proxies to Rasa. Falls back to rule-based when Rasa is offline.
Frontend sends: { message: string }
Frontend reads: responses (array of {text})
"""
import requests
from flask import Blueprint, jsonify, request, current_app
from .rag_assistant import ask_custom_bot
chatbot_bp = Blueprint('chatbot', __name__)


@chatbot_bp.route('/message', methods=['POST'])
def send_message():
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'message is required'}), 400

    sender  = data.get('sender', 'user')
    message = data['message']

    rasa_url = current_app.config.get('RASA_SERVER_URL', 'http://localhost:5005')

    try:
        resp = requests.post(
            f'{rasa_url}/webhooks/rest/webhook',
            json={'sender': sender, 'message': message},
            timeout=5
        )
        resp.raise_for_status()
        responses = resp.json()
        first_text = ''
        if isinstance(responses, list) and responses:
            first_text = responses[0].get('text', '') or ''
        # Keep both `responses` and flattened `message` for clients.
        return jsonify({
            'responses': responses,
            'message': first_text,
            'sender': sender
        }), 200
    except Exception:
        fallback_text = _fallback(message)
        # Fallback rule-based
        return jsonify({
            'responses': [{'text': fallback_text}],
            'message': fallback_text,
            'sender': sender,
        }), 200


def _fallback(message: str) -> str:
    msg = message.lower()

    if any(w in msg for w in ['available', 'free', 'spot', 'park', 'space']):
        try:
            from ..models import ParkingLog
            from ..config import BaseConfig
            from datetime import datetime
            from sqlalchemy import func
            from ..extensions import db
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            occupied = (
                db.session.query(func.count(func.distinct(ParkingLog.plate_number)))
                .filter(
                    ParkingLog.event_type == 'entry',
                    ParkingLog.timestamp >= today,
                    ~ParkingLog.plate_number.in_(
                        db.session.query(ParkingLog.plate_number)
                        .filter(ParkingLog.event_type == 'exit',
                                ParkingLog.timestamp >= today)
                    )
                ).scalar()
            ) or 0
            total = BaseConfig.TOTAL_PARKING_SPOTS
            available = total - occupied
            
            return (f"🟢 **Live Parking Status**\n\n"
                    f"🔹 **Total Capacity:** {total} spots\n"
                    f"🔹 **Currently Occupied:** {occupied} vehicles 🚗\n"
                    f"🔹 **Available Spots:** {available} ✅\n\n"
                    f"The gate is fully operational.")
        except Exception:
            return "⚠️ **Alert:** Parking availability data is temporarily unavailable. Please check the database connection."

    elif any(w in msg for w in ['hello', 'hi', 'hey', 'salam']):
        return ("👋 **Welcome to AutoGate AI!**\n\n"
                "I am your smart parking assistant. I can help you check live parking availability, generate daily reports, and monitor gate activity.\n\n"
                "How can I assist you today?")

    elif any(w in msg for w in ['summary', 'today', 'report']):
        try:
            from ..models import ParkingLog, Anomaly
            from datetime import datetime
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            entries  = ParkingLog.query.filter(
                ParkingLog.event_type == 'entry',
                ParkingLog.timestamp >= today).count()
            exits    = ParkingLog.query.filter(
                ParkingLog.event_type == 'exit',
                ParkingLog.timestamp >= today).count()
            anomalies = Anomaly.query.filter_by(
                resolved=False, false_positive=False).count()
            
            return (f"📊 **AutoGate Daily Report**\n\n"
                    f"📥 **Total Entries:** {entries} vehicles\n"
                    f"📤 **Total Exits:** {exits} vehicles\n"
                    f"🚨 **Active Anomalies:** {anomalies} (Unregistered/Suspicious)\n\n"
                    f"System is running smoothly without critical errors. ✨")
        except Exception:
            return "⚠️ **Alert:** Today's summary is temporarily unavailable."

    elif any(w in msg for w in ['help', 'what can', 'feature']):
        return ("🤖 **AutoGate Assistant Features:**\n\n"
                "Here is what I can do for you:\n"
                "🚘 **Availability:** Ask *'How many spots are free?'*\n"
                "📈 **Reports:** Ask *'Give me today's report'* or *'Summary'*\n"
                "🔍 **Monitoring:** Ask *'Help'* to see this menu.\n\n"
                "Just type your query below!")

    # --- THE GOOGLE GEMINI AI INTEGRATION (RAG) ---
    # Agar upar wala koi rule match nahi hua, toh sawal seedha Gemini (PDF Reader) ke paas jayega
    try:
        # LangChain + PDF ko sawal bhejain
        ai_response = ask_custom_bot(message)
        return f"🤖 **AutoGate AI (Knowledge Base):**\n\n{ai_response}"
    except Exception as e:
        # Agar internet band ho ya API issue ho
        print("Gemini API Error:", e)
        return ("🤔 I am currently offline and cannot access the knowledge base.\n\n"
                "I can only answer specific queries right now. Try asking:\n"
                "• *'Today's summary'*\n"
                "• *'Available parking spots'*")
