"""
Anomaly Routes: /api/anomalies/
Response fields use camelCase to match the React frontend.
Frontend sends: ?filter=all|active|resolved
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from ..extensions import db
from ..models import Anomaly

anomalies_bp = Blueprint('anomalies', __name__)


def _to_camel(a: Anomaly) -> dict:
    """camelCase keys matching the frontend Anomaly interface."""
    return {
        'id':           str(a.id),
        'plateNumber':  a.plate_number,
        'vehicleId':    a.vehicle_id,
        'anomalyType':  a.anomaly_type,
        'severity':     a.severity,
        'score':        a.anomaly_score,
        'reason':       a.description,
        'description':  a.description,
        'timestamp':    a.detected_at.isoformat(),
        'detectedAt':   a.detected_at.isoformat(),
        # Frontend checks: anomaly.status === 'active' | 'resolved' | 'false_positive'
        'status': (
            'false_positive' if a.false_positive else
            'resolved'       if a.resolved       else
            'active'
        ),
    }


@anomalies_bp.route('', methods=['GET'])
@jwt_required()
def list_anomalies():
    # Frontend sends: ?filter=all|active|resolved
    filter_val = request.args.get('filter', 'all')
    page       = int(request.args.get('page', 1))
    per_page   = int(request.args.get('per_page', 100))

    query = Anomaly.query
    if filter_val == 'active':
        query = query.filter_by(resolved=False, false_positive=False)
    elif filter_val == 'resolved':
        query = query.filter_by(resolved=True)
    # 'all' → no filter

    pagination = query.order_by(Anomaly.detected_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    # Frontend calls setAnomalies(data) — expects a plain array
    return jsonify([_to_camel(a) for a in pagination.items]), 200


@anomalies_bp.route('/<int:anomaly_id>/resolve', methods=['POST'])
@jwt_required()
def resolve_anomaly(anomaly_id):
    anomaly = Anomaly.query.get_or_404(anomaly_id)
    anomaly.resolved    = True
    anomaly.resolved_at = datetime.utcnow()
    anomaly.resolved_by = int(get_jwt_identity())
    db.session.commit()
    return jsonify(_to_camel(anomaly)), 200


@anomalies_bp.route('/<int:anomaly_id>/false-positive', methods=['POST'])
@jwt_required()
def false_positive(anomaly_id):
    anomaly = Anomaly.query.get_or_404(anomaly_id)
    anomaly.false_positive = True
    anomaly.resolved       = True
    anomaly.resolved_at    = datetime.utcnow()
    anomaly.resolved_by    = int(get_jwt_identity())
    db.session.commit()
    return jsonify(_to_camel(anomaly)), 200
