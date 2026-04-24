"""
AutoGate Database Models
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.String(50), unique=True, nullable=False)   # e.g. L1F22BSCS0747
    username     = db.Column(db.String(80), unique=True, nullable=False)
    email        = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role         = db.Column(db.String(20), default='user')               # admin / security / user
    is_active    = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
        }


class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id             = db.Column(db.Integer, primary_key=True)
    plate_number   = db.Column(db.String(20), unique=True, nullable=False)
    owner_name     = db.Column(db.String(100), nullable=False)
    owner_id       = db.Column(db.String(50))                              # student/staff ID
    vehicle_type   = db.Column(db.String(30), default='car')               # car / bike / van
    department     = db.Column(db.String(100))
    status         = db.Column(db.String(20), default='active')            # active / suspended / expired
    contact        = db.Column(db.String(50))                              # phone / email of owner
    registered_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes          = db.Column(db.Text)

    logs = db.relationship('ParkingLog', backref='vehicle', lazy='dynamic')

    def to_dict(self):
        return {
            'id':           str(self.id),
            'plateNumber':  self.plate_number,
            'ownerName':    self.owner_name,
            'ownerId':      self.owner_id,
            'vehicleType':  self.vehicle_type,
            'department':   self.department or '',
            'contact':      self.contact or '',
            'status':       self.status,
            'notes':        self.notes or '',
            'registeredAt': self.registered_at.isoformat(),
            'updatedAt':    self.updated_at.isoformat(),
        }


class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'

    id          = db.Column(db.Integer, primary_key=True)
    spot_number = db.Column(db.String(10), unique=True, nullable=False)
    zone        = db.Column(db.String(10), default='A')
    is_occupied = db.Column(db.Boolean, default=False)
    vehicle_id  = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    occupied_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'spot_number': self.spot_number,
            'zone': self.zone,
            'is_occupied': self.is_occupied,
            'vehicle_id': self.vehicle_id,
            'occupied_at': self.occupied_at.isoformat() if self.occupied_at else None,
        }


class ParkingLog(db.Model):
    __tablename__ = 'parking_logs'

    id           = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), nullable=False)
    vehicle_id   = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    event_type   = db.Column(db.String(10), nullable=False)   # entry / exit
    timestamp    = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    gate         = db.Column(db.String(20), default='main')
    status       = db.Column(db.String(20), default='allowed')  # allowed / denied / unknown
    confidence   = db.Column(db.Float, default=1.0)             # LPR confidence score
    image_path   = db.Column(db.String(256))
    notes        = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'plate_number': self.plate_number,
            'vehicle_id': self.vehicle_id,
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'gate': self.gate,
            'status': self.status,
            'confidence': self.confidence,
            'image_path': self.image_path,
            'notes': self.notes,
        }


class Anomaly(db.Model):
    __tablename__ = 'anomalies'

    id           = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20))
    vehicle_id   = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=True)
    anomaly_type = db.Column(db.String(50))                          # unknown_plate / long_stay / multiple_entry / suspicious_time
    severity     = db.Column(db.String(10), default='medium')        # low / medium / high
    description  = db.Column(db.Text)
    detected_at  = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    resolved     = db.Column(db.Boolean, default=False)
    false_positive = db.Column(db.Boolean, default=False)
    resolved_at  = db.Column(db.DateTime, nullable=True)
    resolved_by  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    anomaly_score = db.Column(db.Float)

    def to_dict(self):
        return {
            'id': self.id,
            'plate_number': self.plate_number,
            'vehicle_id': self.vehicle_id,
            'anomaly_type': self.anomaly_type,
            'severity': self.severity,
            'description': self.description,
            'detected_at': self.detected_at.isoformat(),
            'resolved': self.resolved,
            'false_positive': self.false_positive,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'anomaly_score': self.anomaly_score,
        }


class ForecastCache(db.Model):
    __tablename__ = 'forecast_cache'

    id          = db.Column(db.Integer, primary_key=True)
    period      = db.Column(db.String(10), nullable=False)   # 24h / 48h / 72h
    forecast_json = db.Column(db.Text, nullable=False)
    accuracy    = db.Column(db.Float)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'period': self.period,
            'forecast': json.loads(self.forecast_json),
            'accuracy': self.accuracy,
            'generated_at': self.generated_at.isoformat(),
        }


class GateStatus(db.Model):
    __tablename__ = 'gate_status'

    id               = db.Column(db.Integer, primary_key=True)
    gate_name        = db.Column(db.String(20), default='main')
    is_open          = db.Column(db.Boolean, default=False)
    emergency_stop   = db.Column(db.Boolean, default=False)
    last_command     = db.Column(db.String(20))
    last_updated     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'gate_name': self.gate_name,
            'is_open': self.is_open,
            'emergency_stop': self.emergency_stop,
            'last_command': self.last_command,
            'last_updated': self.last_updated.isoformat(),
        }


class ParkingBooking(db.Model):
    """Booking made by a user for a future parking slot."""
    __tablename__ = 'parking_bookings'

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spot_id          = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable=False)
    booking_date     = db.Column(db.String(10), nullable=False)   # YYYY-MM-DD
    booking_time     = db.Column(db.String(5),  nullable=False)   # HH:MM
    duration_minutes = db.Column(db.Integer, default=30)
    expiry_time      = db.Column(db.String(50))                   # ISO string
    status           = db.Column(db.String(20), default='active') # active/expired/cancelled/completed
    slot_location    = db.Column(db.String(20))
    building         = db.Column(db.String(10))
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    spot = db.relationship('ParkingSpot', backref='bookings', lazy='select')
    user = db.relationship('User', backref='bookings', lazy='select')

    def to_dict(self):
        return {
            'id':             str(self.id),
            'userId':         self.user_id,
            'spotId':         self.spot_id,
            'bookingDate':    self.booking_date,
            'bookingTime':    self.booking_time,
            'durationMinutes': self.duration_minutes,
            'expiryTime':     self.expiry_time,
            'status':         self.status,
            'slotLocation':   self.slot_location,
            'building':       self.building,
            'createdAt':      self.created_at.isoformat(),
        }


class Timetable(db.Model):
    """User's class timetable extracted from uploaded image."""
    __tablename__ = 'timetables'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    classes_json = db.Column(db.Text, default='[]')  # JSON array of class objects
    raw_text    = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('timetable', uselist=False))
