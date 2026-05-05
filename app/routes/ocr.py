"""
OCR / Offline Log Import Routes: /api/ocr/
Frontend sends: image (file), eventType, timestamp, gateId (FormData)
"""
import os
import uuid
import requests
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models import ParkingLog, Vehicle

ocr_bp = Blueprint('ocr', __name__)


@ocr_bp.route('/live', methods=['POST'])
@jwt_required()
def live_recognize():
    """
    Recognize plate from a single frame captured in the browser.
    Frontend sends: image (file) as multipart/form-data.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'image file is required'}), 400

    image = request.files['image']
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp/autogate_uploads')
    os.makedirs(upload_folder, exist_ok=True)

    filename = f"{uuid.uuid4().hex}_{image.filename or 'frame.jpg'}"
    filepath = os.path.join(upload_folder, filename)
    image.save(filepath)

    try:
        lpr_url = current_app.config.get('LPR_SERVICE_URL', 'http://localhost:5001')
        with open(filepath, 'rb') as f:
            resp = requests.post(
                f'{lpr_url}/recognize',
                files={'image': f},
                timeout=10
            )

        if resp.status_code != 200:
            # Pass through LPR error where possible
            try:
                return jsonify(resp.json()), resp.status_code
            except Exception:
                return jsonify({'error': 'LPR service error'}), 502

        data = resp.json() or {}
        plate_number = (data.get('plate_number') or '').upper().strip()
        confidence = float(data.get('confidence') or 0.0)

        if not plate_number:
            return jsonify({'error': 'No plate detected', 'confidence': 0.0}), 422

        return jsonify({
            'plateNumber': plate_number,
            'confidence': confidence,
        }), 200
    except Exception as e:
        return jsonify({'error': f'LPR service error: {str(e)}'}), 502
    finally:
        try:
            os.remove(filepath)
        except OSError:
            pass


@ocr_bp.route('/offline', methods=['POST'])
@jwt_required()
def offline_import():
    if 'image' not in request.files:
        return jsonify({'error': 'image file is required'}), 400

    image       = request.files['image']
    # Frontend sends camelCase form fields
    event_type  = request.form.get('eventType') or request.form.get('event_type', 'entry')
    gate        = request.form.get('gateId')    or request.form.get('gate', 'main')
    manual_plate = request.form.get('plateNumber', '').upper().strip()
    timestamp_str = request.form.get('timestamp', '')

    # Save image
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp/autogate_uploads')
    os.makedirs(upload_folder, exist_ok=True)
    filename = f"{uuid.uuid4().hex}_{image.filename}"
    filepath = os.path.join(upload_folder, filename)
    image.save(filepath)

    plate_number = manual_plate
    confidence   = 1.0

    try:
        # Call LPR service if no manual plate provided
        if not plate_number:
            lpr_url = current_app.config.get('LPR_SERVICE_URL', 'http://localhost:5001')
            try:
                with open(filepath, 'rb') as f:
                    resp = requests.post(
                        f'{lpr_url}/recognize',
                        files={'image': f},
                        timeout=10
                    )
                if resp.status_code == 200:
                    lpr_data     = resp.json()
                    plate_number = lpr_data.get('plate_number', '').upper().strip()
                    confidence   = lpr_data.get('confidence', 0.0)
            except Exception as e:
                return jsonify({'error': f'LPR service error: {str(e)}'}), 502

        if not plate_number:
            return jsonify({'error': 'Could not detect plate number'}), 422

        vehicle = Vehicle.query.filter_by(plate_number=plate_number).first()
        status  = 'allowed' if (vehicle and vehicle.status == 'active') else (
            'denied' if vehicle else 'unknown'
        )

        log = ParkingLog(
            plate_number=plate_number,
            vehicle_id=vehicle.id if vehicle else None,
            event_type=event_type,
            gate=gate,
            status=status,
            confidence=confidence,
            image_path=filepath,
            notes='offline_import',
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'plateNumber': plate_number,
            'confidence':  confidence,
            'status':      status,
            'logId':       log.id,
            'vehicle':     vehicle.to_dict() if vehicle else None,
        }), 201
    finally:
        try:
            os.remove(filepath)
        except OSError:
            pass
