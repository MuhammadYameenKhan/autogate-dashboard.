"""
Logs Routes: /api/logs/
Response uses camelCase to match frontend: log.plateNumber, log.eventType,
log.timestamp, log.gateId, log.status, log.duration
"""
from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required
from datetime import datetime
from ..models import ParkingLog

logs_bp = Blueprint('logs', __name__)


def _to_camel(log: ParkingLog) -> dict:
    return {
        'id':          str(log.id),
        'plateNumber': log.plate_number,
        'vehicleId':   log.vehicle_id,
        'eventType':   log.event_type,
        'timestamp':   log.timestamp.isoformat(),
        'gateId':      log.gate,
        'gate':        log.gate,
        'status':      log.status,
        'confidence':  log.confidence,
        'duration':    None,   # calculated if needed
        'notes':       log.notes,
    }


@logs_bp.route('', methods=['GET'])
@jwt_required()
def get_logs():
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    search    = request.args.get('search', '').strip()
    event     = request.args.get('eventType') or request.args.get('event_type', '')
    status    = request.args.get('status', '')
    date_from = request.args.get('dateFrom') or request.args.get('date_from', '')
    date_to   = request.args.get('dateTo') or request.args.get('date_to', '')

    query = ParkingLog.query

    if search:
        query = query.filter(ParkingLog.plate_number.ilike(f'%{search}%'))
    if event and event != 'all':
        query = query.filter_by(event_type=event)
    if status and status != 'all':
        query = query.filter_by(status=status)
    if date_from:
        try:
            query = query.filter(ParkingLog.timestamp >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(ParkingLog.timestamp <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    pagination = query.order_by(ParkingLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'logs':    [_to_camel(l) for l in pagination.items],
        'total':   pagination.total,
        'page':    page,
        'perPage': per_page,
        'pages':   pagination.pages,
    }), 200


@logs_bp.route('/<int:log_id>', methods=['GET'])
@jwt_required()
def get_log(log_id):
    log = ParkingLog.query.get_or_404(log_id)
    return jsonify(_to_camel(log)), 200


@logs_bp.route('/export', methods=['GET'])
@jwt_required()
def export_logs():
    import csv, io
    logs     = ParkingLog.query.order_by(ParkingLog.timestamp.desc()).limit(10000).all()
    output   = io.StringIO()
    writer   = csv.DictWriter(output, fieldnames=[
        'id', 'plateNumber', 'eventType', 'timestamp',
        'gateId', 'status', 'confidence', 'notes'
    ])
    writer.writeheader()
    for log in logs:
        writer.writerow({
            'id': log.id,
            'plateNumber': log.plate_number,
            'eventType': log.event_type,
            'timestamp': log.timestamp.isoformat(),
            'gateId': log.gate,
            'status': log.status,
            'confidence': log.confidence,
            'notes': log.notes or '',
        })
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=parking_logs.csv'
    return response
