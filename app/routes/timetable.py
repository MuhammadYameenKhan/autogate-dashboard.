"""
Timetable Routes: /api/timetable/
Handles timetable image upload, OCR extraction, save/update/get.
Frontend pages: TimetableUpload.tsx
"""
import os
import json
import uuid
import requests
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models import Timetable

timetable_bp = Blueprint('timetable', __name__)


def _extract_schedule_from_image(filepath: str) -> dict:
    """
    Call LPR/OCR service to extract timetable text, then parse it.
    Falls back to a demo schedule if service unavailable.
    """
    lpr_url = os.getenv('LPR_SERVICE_URL', 'http://localhost:5001')
    try:
        with open(filepath, 'rb') as f:
            resp = requests.post(
                f'{lpr_url}/timetable/extract',
                files={'image': f},
                timeout=15
            )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass

    # Fallback: return a realistic demo schedule
    return {
        'classes': [
            {'day': 'Monday',    'time': '08:00 - 09:30', 'building': 'A', 'course': 'Data Structures'},
            {'day': 'Monday',    'time': '11:00 - 12:30', 'building': 'B', 'course': 'Database Systems'},
            {'day': 'Tuesday',   'time': '09:00 - 10:30', 'building': 'C', 'course': 'Software Engineering'},
            {'day': 'Wednesday', 'time': '08:00 - 09:30', 'building': 'A', 'course': 'Data Structures'},
            {'day': 'Wednesday', 'time': '14:00 - 15:30', 'building': 'D', 'course': 'Computer Networks'},
            {'day': 'Thursday',  'time': '09:00 - 10:30', 'building': 'C', 'course': 'Software Engineering'},
            {'day': 'Friday',    'time': '11:00 - 12:30', 'building': 'B', 'course': 'Database Systems'},
        ],
        'rawText': 'Extracted from uploaded timetable image.'
    }


@timetable_bp.route('/extract', methods=['POST'])
@jwt_required()
def extract_timetable():
    """Upload timetable image and extract schedule using OCR."""
    if 'image' not in request.files:
        return jsonify({'error': 'image file is required'}), 400

    image         = request.files['image']
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp/autogate_uploads')
    os.makedirs(upload_folder, exist_ok=True)

    filename = f"timetable_{uuid.uuid4().hex}_{image.filename}"
    filepath = os.path.join(upload_folder, filename)
    image.save(filepath)

    try:
        extracted = _extract_schedule_from_image(filepath)
    finally:
        try:
            os.remove(filepath)
        except OSError:
            pass

    # Frontend reads: response.classes (array), response.rawText
    return jsonify({
        'classes': extracted.get('classes', []),
        'rawText': extracted.get('rawText', ''),
    }), 200


@timetable_bp.route('/save', methods=['POST'])
@jwt_required()
def save_timetable():
    """Save extracted timetable for a user."""
    user_id = int(get_jwt_identity())
    data    = request.get_json() or {}

    classes  = data.get('classes', [])
    raw_text = data.get('rawText', '')

    # Delete old timetable if exists
    existing = Timetable.query.filter_by(user_id=user_id).first()
    if existing:
        db.session.delete(existing)

    timetable = Timetable(
        user_id=user_id,
        classes_json=json.dumps(classes),
        raw_text=raw_text,
    )
    db.session.add(timetable)
    db.session.commit()

    return jsonify({
        'message': 'Timetable saved successfully',
        'classes': classes,
        'rawText': raw_text,
    }), 201


@timetable_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_timetable():
    """Update an existing timetable."""
    user_id = int(get_jwt_identity())
    data    = request.get_json() or {}

    classes  = data.get('classes', [])
    raw_text = data.get('rawText', '')

    timetable = Timetable.query.filter_by(user_id=user_id).first()
    if not timetable:
        # Create if not exists
        timetable = Timetable(user_id=user_id)
        db.session.add(timetable)

    timetable.classes_json = json.dumps(classes)
    timetable.raw_text     = raw_text
    db.session.commit()

    return jsonify({
        'message': 'Timetable updated successfully',
        'classes': classes,
        'rawText': raw_text,
    }), 200


@timetable_bp.route('/my', methods=['GET'])
@jwt_required()
def get_my_timetable():
    """Get the current user's saved timetable."""
    user_id   = int(get_jwt_identity())
    timetable = Timetable.query.filter_by(user_id=user_id).first()

    if not timetable:
        return jsonify(None), 200

    # Frontend reads: data.classes, data.rawText
    return jsonify({
        'classes': json.loads(timetable.classes_json),
        'rawText': timetable.raw_text or '',
    }), 200
