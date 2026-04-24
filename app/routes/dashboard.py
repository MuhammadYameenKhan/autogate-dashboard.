"""
Dashboard Routes: /api/dashboard/
All response fields use camelCase to match the React frontend exactly.
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime, timedelta
from sqlalchemy import func
from ..extensions import db
from ..models import Vehicle, ParkingLog, Anomaly
from ..config import BaseConfig

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def stats():
    total_capacity = BaseConfig.TOTAL_PARKING_SPOTS
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Plates that entered today and have NOT exited
    exited_today = (
        db.session.query(ParkingLog.plate_number)
        .filter(ParkingLog.event_type == 'exit', ParkingLog.timestamp >= today)
        .distinct()
        .subquery()
    )
    currently_parked = (
        db.session.query(func.count(func.distinct(ParkingLog.plate_number)))
        .filter(
            ParkingLog.event_type == 'entry',
            ParkingLog.timestamp >= today,
            ~ParkingLog.plate_number.in_(
                db.session.query(ParkingLog.plate_number)
                .filter(ParkingLog.event_type == 'exit', ParkingLog.timestamp >= today)
            )
        )
        .scalar()
    ) or 0

    available      = max(0, total_capacity - currently_parked)
    occupied       = currently_parked
    today_entries  = ParkingLog.query.filter(
        ParkingLog.event_type == 'entry', ParkingLog.timestamp >= today
    ).count()
    active_anomalies = Anomaly.query.filter_by(resolved=False, false_positive=False).count()

    # Hourly traffic last 24h
    last_24h = datetime.utcnow() - timedelta(hours=24)
    hourly_rows = (
        db.session.query(
            func.date_trunc('hour', ParkingLog.timestamp).label('hour'),
            func.count(ParkingLog.id).label('count')
        )
        .filter(ParkingLog.timestamp >= last_24h)
        .group_by('hour')
        .order_by('hour')
        .all()
    )
    hourly_traffic = [{'hour': r.hour.isoformat(), 'count': r.count} for r in hourly_rows]

    # Frontend reads: stats.totalCapacity, stats.occupied, stats.available,
    #                 stats.currentlyParked, stats.todayEntries, stats.activeAnomalies
    return jsonify({
        'totalCapacity':   total_capacity,
        'occupied':        occupied,
        'available':       available,
        'currentlyParked': currently_parked,
        'todayEntries':    today_entries,
        'activeAnomalies': active_anomalies,
        'hourlyTraffic':   hourly_traffic,
        'timestamp':       datetime.utcnow().isoformat(),
    }), 200
