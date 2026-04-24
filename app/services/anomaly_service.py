"""
Anomaly Detection Service
Uses Isolation Forest to detect suspicious parking behaviors.
"""
import logging
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from ..extensions import db
from ..models import ParkingLog, Anomaly, Vehicle

logger = logging.getLogger(__name__)


def check_anomaly(log: ParkingLog):
    """
    Called after every parking event.
    Runs rule-based checks + Isolation Forest scoring.
    """
    try:
        _check_unknown_plate(log)
        _check_multiple_entry(log)
        _check_suspicious_time(log)
        _check_long_stay(log)
        _run_isolation_forest(log)
    except Exception as e:
        logger.error(f"Anomaly check failed: {e}")


# ── Rule-based checks ────────────────────────────────────────────────────────

def _check_unknown_plate(log: ParkingLog):
    vehicle = Vehicle.query.filter_by(plate_number=log.plate_number).first()
    if not vehicle:
        _create_anomaly(
            plate_number=log.plate_number,
            vehicle_id=None,
            anomaly_type='unknown_plate',
            severity='high',
            description=f"Unregistered plate '{log.plate_number}' attempted {log.event_type} at {log.gate}.",
            score=1.0,
        )


def _check_multiple_entry(log: ParkingLog):
    if log.event_type != 'entry':
        return
    window = datetime.utcnow() - timedelta(hours=1)
    count = ParkingLog.query.filter(
        ParkingLog.plate_number == log.plate_number,
        ParkingLog.event_type == 'entry',
        ParkingLog.timestamp >= window,
        ParkingLog.id != log.id,
    ).count()
    if count >= 2:
        _create_anomaly(
            plate_number=log.plate_number,
            vehicle_id=log.vehicle_id,
            anomaly_type='multiple_entry',
            severity='medium',
            description=f"Plate '{log.plate_number}' entered {count + 1} times within the last hour.",
            score=0.8,
        )


def _check_suspicious_time(log: ParkingLog):
    hour = log.timestamp.hour
    # Suspicious if between midnight and 5am
    if 0 <= hour < 5:
        _create_anomaly(
            plate_number=log.plate_number,
            vehicle_id=log.vehicle_id,
            anomaly_type='suspicious_time',
            severity='medium',
            description=f"Plate '{log.plate_number}' {log.event_type} at unusual hour ({hour:02d}:00).",
            score=0.7,
        )


def _check_long_stay(log: ParkingLog):
    if log.event_type != 'exit':
        return
    # Find corresponding entry
    entry = ParkingLog.query.filter(
        ParkingLog.plate_number == log.plate_number,
        ParkingLog.event_type == 'entry',
        ParkingLog.timestamp < log.timestamp,
    ).order_by(ParkingLog.timestamp.desc()).first()

    if entry:
        stay_hours = (log.timestamp - entry.timestamp).total_seconds() / 3600
        if stay_hours > 12:
            _create_anomaly(
                plate_number=log.plate_number,
                vehicle_id=log.vehicle_id,
                anomaly_type='long_stay',
                severity='low',
                description=f"Plate '{log.plate_number}' stayed for {stay_hours:.1f} hours.",
                score=0.6,
            )


# ── Isolation Forest ─────────────────────────────────────────────────────────

def _run_isolation_forest(log: ParkingLog):
    """
    Build feature vector for the current event and score it.
    Uses last 500 events as training data.
    """
    recent_logs = (
        ParkingLog.query
        .order_by(ParkingLog.timestamp.desc())
        .limit(500)
        .all()
    )

    if len(recent_logs) < 20:
        return  # Not enough data

    def featurize(l: ParkingLog):
        hour      = l.timestamp.hour
        dow       = l.timestamp.weekday()
        is_entry  = 1 if l.event_type == 'entry' else 0
        is_denied = 1 if l.status == 'denied' else 0
        conf      = l.confidence if l.confidence else 1.0
        return [hour, dow, is_entry, is_denied, conf]

    X = np.array([featurize(l) for l in recent_logs])
    x_new = np.array([featurize(log)]).reshape(1, -1)

    clf = IsolationForest(contamination=0.05, random_state=42)
    clf.fit(X)
    score = clf.decision_function(x_new)[0]   # negative = more anomalous
    pred  = clf.predict(x_new)[0]             # -1 = anomaly

    if pred == -1 and score < -0.1:
        normalized = max(0.0, min(1.0, -score))
        _create_anomaly(
            plate_number=log.plate_number,
            vehicle_id=log.vehicle_id,
            anomaly_type='ml_flagged',
            severity='medium' if normalized < 0.7 else 'high',
            description=(
                f"Isolation Forest flagged plate '{log.plate_number}' "
                f"({log.event_type}) — anomaly score: {normalized:.2f}."
            ),
            score=normalized,
        )


# ── Helper ────────────────────────────────────────────────────────────────────

def _create_anomaly(**kwargs):
    """Avoid duplicate active anomalies for the same plate+type."""
    existing = Anomaly.query.filter_by(
        plate_number=kwargs['plate_number'],
        anomaly_type=kwargs['anomaly_type'],
        resolved=False,
        false_positive=False,
    ).first()
    if existing:
        return  # Already flagged

    anomaly = Anomaly(
        plate_number=kwargs['plate_number'],
        vehicle_id=kwargs.get('vehicle_id'),
        anomaly_type=kwargs['anomaly_type'],
        severity=kwargs['severity'],
        description=kwargs['description'],
        anomaly_score=kwargs.get('score', 0.5),
    )
    db.session.add(anomaly)
    db.session.commit()
    logger.info(f"Anomaly created: {kwargs['anomaly_type']} for {kwargs['plate_number']}")
