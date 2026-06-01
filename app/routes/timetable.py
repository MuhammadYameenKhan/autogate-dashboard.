"""
Timetable Routes: /api/timetable/
Handles timetable image upload, OCR extraction, save/update/get.
Frontend pages: TimetableUpload.tsx
"""
import os
import json
import uuid
import logging
import requests
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models import Timetable

logger = logging.getLogger(__name__)
timetable_bp = Blueprint('timetable', __name__)


def _extract_via_lpr_service(filepath: str) -> dict | None:
    """Optional: delegate to LPR microservice if running."""
    lpr_url = os.getenv('LPR_SERVICE_URL', 'http://localhost:5001')
    try:
        with open(filepath, 'rb') as f:
            resp = requests.post(
                f'{lpr_url}/timetable/extract',
                files={'image': f},
                timeout=15,
            )
        if resp.status_code == 200:
            data = resp.json()
            if data.get('classes') or data.get('rawText'):
                return data
    except Exception as exc:
        logger.debug('LPR timetable extract unavailable: %s', exc)
    return None


def _extract_schedule_from_image(filepath: str) -> dict:
    """
    Extract schedule from uploaded timetable image using OCR.
    Tries local Tesseract first, then optional LPR service.
    """
    from ..services.timetable_ocr import extract_schedule_from_image

    try:
        return extract_schedule_from_image(filepath)
    except ImportError:
        logger.warning('OCR dependencies missing (pytesseract/opencv)')
    except RuntimeError as exc:
        logger.warning('Local OCR failed: %s', exc)
    except Exception as exc:
        logger.warning('Local OCR error: %s', exc)

    lpr_result = _extract_via_lpr_service(filepath)
    if lpr_result:
        return lpr_result

    raise RuntimeError(
        'Could not extract text from the timetable image. '
        'Ensure Tesseract is installed (brew install tesseract) and '
        'OCR packages are installed (pip install pytesseract opencv-python-headless Pillow).'
    )


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
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 422
    finally:
        try:
            os.remove(filepath)
        except OSError:
            pass

    classes = extracted.get('classes', [])
    raw_text = extracted.get('rawText', '')

    if not classes:
        return jsonify({
            'error': (
                'No classes could be parsed from the image. '
                'Try a clearer photo with readable day, time, and room labels.'
            ),
            'classes': [],
            'rawText': raw_text,
        }), 422

    # Frontend reads: response.classes (array), response.rawText
    return jsonify({
        'classes': classes,
        'rawText': raw_text,
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
