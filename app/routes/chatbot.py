"""
Chatbot Routes: /api/chatbot/
Proxies to Rasa. Falls back to rule-based when Rasa is offline.
Frontend sends: { message: string }
Frontend reads: responses (array of {text})
"""
import requests
from flask import Blueprint, jsonify, request, current_app

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
            return (f"Currently {total - occupied} out of {total} "
                    f"parking spots are available ({occupied} occupied).")
        except Exception:
            return "Parking availability data is temporarily unavailable."

    elif any(w in msg for w in ['hello', 'hi', 'hey', 'salam']):
        return "Hello! I'm the AutoGate parking assistant. How can I help you?"

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
            return (f"Today's summary: {entries} entries, {exits} exits, "
                    f"{anomalies} active anomaly alerts.")
        except Exception:
            return "Today's summary is temporarily unavailable."

    elif any(w in msg for w in ['help', 'what can', 'feature']):
        return ("I can help you with:\n"
                "• Parking availability (e.g. 'How many spots are free?')\n"
                "• Today's summary (e.g. 'Give me today's report')\n"
                "• Vehicle status (e.g. 'Is LHR-1234 parked?')\n"
                "• General parking questions")

    return ("I'm here to help with parking queries. Ask about available spots, "
            "vehicle status, or today's parking summary.")
