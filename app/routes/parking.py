"""
Parking Routes: /api/parking/
Response fields use camelCase to match the React frontend exactly.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from datetime import datetime
from sqlalchemy import func
from ..extensions import db
from ..models import Vehicle, ParkingLog, ParkingSpot, ParkingBooking
from ..config import BaseConfig

parking_bp = Blueprint('parking', __name__)


def _bookings_overlap(start_a, end_a, start_b, end_b):
    """Half-open interval overlap check: [start, end)."""
    if not all([start_a, end_a, start_b, end_b]):
        return False
    return start_a < end_b and start_b < end_a


# ── Availability ──────────────────────────────────────────────────────────────
@parking_bp.route('/availability', methods=['GET'])
@jwt_required()
def availability():
    total = BaseConfig.TOTAL_PARKING_SPOTS
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    occupied = (
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

    available = max(0, total - occupied)
    pct = round((occupied / total) * 100, 1) if total else 0

    # Trend vs 1 hour ago
    one_hour_ago = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    one_hour_ago_cutoff = one_hour_ago.replace(hour=max(0, one_hour_ago.hour - 1))
    prev_occupied = (
        db.session.query(func.count(func.distinct(ParkingLog.plate_number)))
        .filter(
            ParkingLog.event_type == 'entry',
            ParkingLog.timestamp >= today,
            ParkingLog.timestamp < one_hour_ago,
            ~ParkingLog.plate_number.in_(
                db.session.query(ParkingLog.plate_number)
                .filter(
                    ParkingLog.event_type == 'exit',
                    ParkingLog.timestamp >= today,
                    ParkingLog.timestamp < one_hour_ago
                )
            )
        )
        .scalar()
    ) or 0

    if occupied > prev_occupied:
        trend = 'up'
    elif occupied < prev_occupied:
        trend = 'down'
    else:
        trend = 'stable'

    # Frontend reads: data.totalCapacity, data.occupied, data.available,
    #                 data.occupancyPercentage, data.trend
    return jsonify({
        'totalCapacity':       total,
        'occupied':            occupied,
        'available':           available,
        'occupancyPercentage': pct,
        'trend':               trend,
        'lastUpdated':         datetime.utcnow().isoformat(),
    }), 200


# ── Currently Parked ──────────────────────────────────────────────────────────
@parking_bp.route('/currently-parked', methods=['GET'])
@jwt_required()
def currently_parked():
    search   = request.args.get('search', '').strip()
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    today    = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    now      = datetime.utcnow()

    exited = (
        db.session.query(ParkingLog.plate_number)
        .filter(ParkingLog.event_type == 'exit', ParkingLog.timestamp >= today)
        .distinct()
        .subquery()
    )

    query = (
        db.session.query(
            ParkingLog.plate_number,
            func.max(ParkingLog.timestamp).label('entry_time'),
            ParkingLog.gate,
        )
        .filter(
            ParkingLog.event_type == 'entry',
            ParkingLog.timestamp >= today,
            ~ParkingLog.plate_number.in_(exited)
        )
        .group_by(ParkingLog.plate_number, ParkingLog.gate)
    )

    if search:
        query = query.filter(ParkingLog.plate_number.ilike(f'%{search}%'))

    total = query.count()
    results = query.offset((page - 1) * per_page).limit(per_page).all()

    vehicles = []
    for row in results:
        vehicle  = Vehicle.query.filter_by(plate_number=row.plate_number).first()
        dur_mins = int((now - row.entry_time).total_seconds() / 60)
        hrs, mins = divmod(dur_mins, 60)
        duration_str = f"{hrs}h {mins}m" if hrs else f"{mins}m"

        # Frontend reads: vehicle.plateNumber, vehicle.ownerName, vehicle.department,
        #                 vehicle.entryTime, vehicle.duration
        vehicles.append({
            'plateNumber': row.plate_number,
            'ownerName':   vehicle.owner_name if vehicle else 'Unknown',
            'department':  vehicle.department if vehicle else '-',
            'vehicleType': vehicle.vehicle_type if vehicle else 'unknown',
            'entryTime':   row.entry_time.isoformat(),
            'duration':    duration_str,
            'durationMins': dur_mins,
            'gate':        row.gate,
        })

    return jsonify({'vehicles': vehicles, 'total': total}), 200


# ── LPR Event (called by LPR service, not frontend) ──────────────────────────
@parking_bp.route('/event', methods=['POST'])
def log_event():
    data  = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    plate      = data.get('plate_number', '').upper().strip()
    event      = data.get('event_type', 'entry')
    gate       = data.get('gate', 'main')
    confidence = float(data.get('confidence', 1.0))
    image_path = data.get('image_path')

    if not plate:
        return jsonify({'error': 'plate_number required'}), 400

    vehicle = Vehicle.query.filter_by(plate_number=plate).first()
    status  = 'allowed' if (vehicle and vehicle.status == 'active') else (
        'denied' if vehicle else 'unknown'
    )

    log = ParkingLog(
        plate_number=plate,
        vehicle_id=vehicle.id if vehicle else None,
        event_type=event,
        gate=gate,
        status=status,
        confidence=confidence,
        image_path=image_path,
    )
    db.session.add(log)
    db.session.commit()

    from ..services.anomaly_service import check_anomaly
    check_anomaly(log)

    if status == 'allowed':
        from ..services.gate_service import send_gate_command
        send_gate_command('open')

    return jsonify({'status': status, 'log_id': log.id,
                    'vehicle': vehicle.to_dict() if vehicle else None}), 201


# ── Parking Slots (ParkingBooking page) ───────────────────────────────────────
@parking_bp.route('/slots/available', methods=['GET'])
@jwt_required()
def available_slots():
    """Return available parking slots for a given date/time."""
    date = request.args.get('date', '')
    time = request.args.get('time', '')

    # Get all spots
    spots = ParkingSpot.query.all()

    # Check which spots are booked for the requested date/time
    booked_slot_ids = set()
    if date and time:
        try:
            from datetime import timedelta
            target_start = datetime.fromisoformat(f"{date}T{time}")
            # Availability checks one instant in time.
            target_end = target_start + timedelta(minutes=1)
            active_bookings = ParkingBooking.query.filter(
                ParkingBooking.status == 'active',
                ParkingBooking.booking_date == date,
            ).all()
            for booking in active_bookings:
                try:
                    booking_start = datetime.fromisoformat(
                        f"{booking.booking_date}T{booking.booking_time}"
                    )
                    duration = int(booking.duration_minutes or 30)
                    booking_end = booking_start + timedelta(minutes=duration)
                    if _bookings_overlap(target_start, target_end, booking_start, booking_end):
                        booked_slot_ids.add(booking.spot_id)
                except Exception:
                    continue
        except Exception:
            pass

    # Frontend reads: slot.id, slot.location, slot.building, slot.distance, slot.available
    result = []
    for spot in spots:
        result.append({
            'id':        str(spot.id),
            'location':  spot.spot_number,
            'building':  spot.zone,
            'distance':  _mock_distance(spot.spot_number),
            'available': spot.id not in booked_slot_ids and not spot.is_occupied,
        })

    return jsonify(result), 200


@parking_bp.route('/suggested', methods=['GET'])
@jwt_required()
def suggested_slot():
    """Return a smart parking suggestion based on user timetable."""
    from flask_jwt_extended import get_jwt_identity
    from ..models import Timetable

    date = request.args.get('date', '')
    time = request.args.get('time', '')
    user_id = int(get_jwt_identity())

    # Try to find a slot near the user's next class building
    timetable = Timetable.query.filter_by(user_id=user_id).first()
    target_zone = 'A'  # default

    if timetable and date and time:
        try:
            import json
            classes = json.loads(timetable.classes_json)
            # Find class closest to requested time
            from datetime import datetime as dt
            req_time = dt.strptime(time, '%H:%M').time() if time else None
            if req_time:
                for cls in classes:
                    cls_time_str = cls.get('time', '').split('-')[0].strip()
                    try:
                        cls_time = dt.strptime(cls_time_str, '%H:%M').time()
                        if cls_time >= req_time:
                            # Map building to zone
                            building = cls.get('building', 'A')
                            target_zone = building[0].upper() if building else 'A'
                            break
                    except Exception:
                        pass
        except Exception:
            pass

    # Find first available spot in target zone
    spot = ParkingSpot.query.filter_by(zone=target_zone, is_occupied=False).first()
    if not spot:
        spot = ParkingSpot.query.filter_by(is_occupied=False).first()

    if not spot:
        return jsonify(None), 200

    return jsonify({
        'id':        str(spot.id),
        'location':  spot.spot_number,
        'building':  spot.zone,
        'distance':  _mock_distance(spot.spot_number),
        'available': True,
    }), 200


@parking_bp.route('/book', methods=['POST'])
@jwt_required()
def book_slot():
    """Book a parking slot."""
    from flask_jwt_extended import get_jwt_identity
    user_id = int(get_jwt_identity())
    data    = request.get_json() or {}

    slot_id     = data.get('slotId')
    date        = data.get('date')
    time        = data.get('time')
    duration    = int(data.get('duration', 30))
    expiry_time = data.get('expiryTime')

    if not all([slot_id, date, time]):
        return jsonify({'error': 'slotId, date and time are required'}), 400

    # Check spot exists
    spot = ParkingSpot.query.get(int(slot_id))
    if not spot:
        return jsonify({'error': 'Slot not found'}), 404

    # Check overlap with existing active bookings for same spot/date.
    try:
        from datetime import timedelta
        requested_start = datetime.fromisoformat(f"{date}T{time}")
        requested_end = requested_start + timedelta(minutes=duration)
    except Exception:
        return jsonify({'error': 'Invalid date/time format'}), 400

    existing_bookings = ParkingBooking.query.filter_by(
        spot_id=spot.id,
        booking_date=date,
        status='active'
    ).all()

    for existing in existing_bookings:
        try:
            existing_start = datetime.fromisoformat(
                f"{existing.booking_date}T{existing.booking_time}"
            )
            existing_duration = int(existing.duration_minutes or 30)
            existing_end = existing_start + timedelta(minutes=existing_duration)
            if _bookings_overlap(requested_start, requested_end, existing_start, existing_end):
                return jsonify({'error': 'Slot already booked for this time range'}), 409
        except Exception:
            continue

    booking = ParkingBooking(
        user_id=user_id,
        spot_id=spot.id,
        booking_date=date,
        booking_time=time,
        duration_minutes=duration,
        expiry_time=expiry_time,
        status='active',
        slot_location=spot.spot_number,
        building=spot.zone,
    )
    db.session.add(booking)
    db.session.commit()

    return jsonify({
        'id':           str(booking.id),
        'slotId':       str(spot.id),
        'slotLocation': spot.spot_number,
        'building':     spot.zone,
        'bookingTime':  booking.created_at.isoformat(),
        'expiryTime':   expiry_time,
        'status':       'active',
    }), 201


@parking_bp.route('/bookings/my', methods=['GET'])
@jwt_required()
def my_bookings():
    """Get all bookings for the current user."""
    from flask_jwt_extended import get_jwt_identity
    user_id  = int(get_jwt_identity())
    bookings = ParkingBooking.query.filter_by(user_id=user_id).order_by(
        ParkingBooking.created_at.desc()
    ).all()

    # Frontend reads: booking.id, booking.slotId, booking.slotLocation,
    #                 booking.bookingTime, booking.expiryTime, booking.status, booking.building
    result = []
    for b in bookings:
        # Auto-expire check
        status = b.status
        if status == 'active' and b.expiry_time:
            try:
                exp = datetime.fromisoformat(b.expiry_time)
                if datetime.utcnow() > exp:
                    status = 'expired'
                    b.status = 'expired'
                    db.session.commit()
            except Exception:
                pass

        result.append({
            'id':           str(b.id),
            'slotId':       str(b.spot_id),
            'slotLocation': b.slot_location,
            'building':     b.building,
            'bookingTime':  b.created_at.isoformat(),
            'expiryTime':   b.expiry_time,
            'status':       status,
        })

    return jsonify(result), 200


@parking_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_booking(booking_id):
    """Cancel a booking."""
    from flask_jwt_extended import get_jwt_identity
    user_id = int(get_jwt_identity())

    booking = ParkingBooking.query.filter_by(id=booking_id, user_id=user_id).first()
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404

    booking.status = 'cancelled'
    db.session.commit()
    return jsonify({'message': 'Booking cancelled', 'id': str(booking.id)}), 200


def _mock_distance(spot_number: str) -> int:
    """Return a mock walking distance in metres based on spot number."""
    try:
        num = int(''.join(filter(str.isdigit, spot_number)))
        return 50 + (num * 7) % 300
    except Exception:
        return 100
