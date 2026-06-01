"""
Chatbot Routes: /api/chatbot/
Proxies to Rasa when running. Falls back to rules + knowledge-base AI.
Frontend sends: { message: string }
Frontend reads: responses (array of {text}) and message (string)
"""
import re
import requests
from flask import Blueprint, jsonify, request, current_app

from ..services.knowledge_base import (
    ask_knowledge_base,
    is_knowledge_query,
    search_knowledge_base_local,
)

chatbot_bp = Blueprint('chatbot', __name__)


def _has_word(msg: str, words: tuple) -> bool:
    return any(re.search(rf'\b{re.escape(w)}\b', msg) for w in words)


@chatbot_bp.route('/message', methods=['POST'])
def send_message():
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'message is required'}), 400

    sender = data.get('sender', 'user')
    message = (data.get('message') or '').strip()

    # Fast paths: live DB stats + local KB/PDF (skip slow Rasa/RAG)
    fast_reply = _fast_intent(message)
    if fast_reply:
        return _chat_response(sender, fast_reply)

    # Knowledge-base / documentation questions use local AI (skip Rasa)
    if is_knowledge_query(message):
        text = _knowledge_response(message)
        return _chat_response(sender, text)

    rasa_url = current_app.config.get('RASA_SERVER_URL', 'http://localhost:5005')
    try:
        resp = requests.post(
            f'{rasa_url}/webhooks/rest/webhook',
            json={'sender': sender, 'message': message},
            timeout=5,
        )
        resp.raise_for_status()
        responses = resp.json()
        first_text = ''
        if isinstance(responses, list) and responses:
            first_text = responses[0].get('text', '') or ''
        if first_text.strip():
            return jsonify({
                'responses': responses,
                'message': first_text,
                'sender': sender,
            }), 200
    except Exception:
        pass

    fallback_text = _fallback(message)
    return _chat_response(sender, fallback_text)


def _chat_response(sender: str, text: str):
    return jsonify({
        'responses': [{'text': text}],
        'message': text,
        'sender': sender,
    }), 200


def _fast_intent(message: str) -> str | None:
    """Operational intents answered from database or local KB/PDF."""
    msg = message.lower().strip()

    if _has_word(msg, ('summary', 'report', 'today', 'daily', 'stats')):
        return _daily_summary()

    if _has_word(msg, ('penalty', 'penalties', 'fine', 'fines', 'violation', 'violations')):
        return _penalty_info(message)

    if _has_word(msg, ('available', 'free', 'capacity', 'occupancy')) and _has_word(
        msg, ('spot', 'space', 'parking', 'park')
    ):
        return _parking_availability()

    return None


def _penalty_info(message: str) -> str:
    answer = search_knowledge_base_local(message)
    if 'do not have specific information' in answer.lower():
        return (
            '📋 **Parking Penalties**\n\n'
            'No penalty details are in the knowledge base yet. '
            'Contact campus security for violation fees and appeals.'
        )
    return f'📋 **Parking Penalties**\n\n{answer}'


def _knowledge_response(message: str) -> str:
    try:
        answer = ask_knowledge_base(message)
        return f'🤖 **AutoGate AI (Knowledge Base):**\n\n{answer}'
    except Exception as exc:
        print('Knowledge base error:', exc)
        return (
            '🤔 I could not access the knowledge base right now.\n\n'
            'Try again or ask: "What is AutoGate?" or "Explain parking policy".'
        )


def _fallback(message: str) -> str:
    msg = message.lower().strip()

    # Live parking availability (specific phrases only)
    if _has_word(msg, ('available', 'free', 'capacity', 'occupancy')) and _has_word(
        msg, ('spot', 'space', 'parking', 'park')
    ):
        return _parking_availability()

    if _has_word(msg, ('hello', 'hi', 'hey', 'salam')):
        return (
            '👋 **Welcome to AutoGate AI!**\n\n'
            'I can check live parking, daily reports, or answer questions from the '
            'knowledge base (e.g. "What is AutoGate?" or "Explain parking policy").\n\n'
            'How can I assist you today?'
        )

    if _has_word(msg, ('help', 'feature', 'can you')):
        return (
            '🤖 **AutoGate Assistant Features:**\n\n'
            '🚘 **Live data:** "How many spots are free?"\n'
            '📈 **Reports:** "Today\'s summary"\n'
            '📚 **Knowledge base:** "What is AutoGate?" or "Explain LPR"\n\n'
            'Type your question below!'
        )

    # Default: knowledge base for general questions
    return _knowledge_response(message)


def _parking_availability() -> str:
    try:
        from ..models import ParkingLog
        from ..config import BaseConfig
        from datetime import datetime
        from sqlalchemy import func
        from ..extensions import db

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        exited = (
            db.session.query(ParkingLog.plate_number)
            .filter(
                ParkingLog.event_type == 'exit',
                ParkingLog.timestamp >= today,
            )
        )
        occupied = (
            db.session.query(func.count(func.distinct(ParkingLog.plate_number)))
            .filter(
                ParkingLog.event_type == 'entry',
                ParkingLog.timestamp >= today,
                ~ParkingLog.plate_number.in_(exited),
            )
            .scalar()
        ) or 0
        total = BaseConfig.TOTAL_PARKING_SPOTS
        available = total - occupied
        return (
            f'🟢 **Live Parking Status**\n\n'
            f'🔹 **Total Capacity:** {total} spots\n'
            f'🔹 **Currently Occupied:** {occupied} vehicles 🚗\n'
            f'🔹 **Available Spots:** {available} ✅\n\n'
            f'The gate is fully operational.'
        )
    except Exception:
        return '⚠️ **Alert:** Parking availability data is temporarily unavailable.'


def _daily_summary() -> str:
    try:
        from ..models import ParkingLog, Anomaly
        from datetime import datetime

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        entries = ParkingLog.query.filter(
            ParkingLog.event_type == 'entry',
            ParkingLog.timestamp >= today,
        ).count()
        exits = ParkingLog.query.filter(
            ParkingLog.event_type == 'exit',
            ParkingLog.timestamp >= today,
        ).count()
        anomalies = Anomaly.query.filter_by(
            resolved=False, false_positive=False,
        ).count()
        return (
            f'📊 **AutoGate Daily Report**\n\n'
            f'📥 **Total Entries:** {entries} vehicles\n'
            f'📤 **Total Exits:** {exits} vehicles\n'
            f'🚨 **Active Anomalies:** {anomalies}\n\n'
            f'System is running smoothly. ✨'
        )
    except Exception:
        return "⚠️ **Alert:** Today's summary is temporarily unavailable."
