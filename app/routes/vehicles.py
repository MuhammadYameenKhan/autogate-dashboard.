"""
Vehicle Management Routes: /api/vehicles/
Accepts camelCase from frontend, stores as snake_case in DB,
returns camelCase to frontend.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models import Vehicle, User

vehicles_bp = Blueprint('vehicles', __name__)


def _to_camel(v: Vehicle) -> dict:
    """Return vehicle dict with camelCase keys matching the frontend interface."""
    return {
        'id':          str(v.id),
        'plateNumber': v.plate_number,
        'ownerName':   v.owner_name,
        'ownerId':     v.owner_id,
        'department':  v.department or '',
        'contact':     v.contact or '',
        'vehicleType': v.vehicle_type,
        'status':      v.status,
        'notes':       v.notes or '',
        'registeredAt': v.registered_at.isoformat(),
    }


def _require_admin_or_security():
    user = User.query.get(int(get_jwt_identity()))
    return user and user.role in ('admin', 'security')


@vehicles_bp.route('', methods=['GET'])
@jwt_required()
def list_vehicles():
    search   = request.args.get('search', '').strip()
    status   = request.args.get('status', '')
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 100))

    query = Vehicle.query
    if search:
        query = query.filter(
            Vehicle.plate_number.ilike(f'%{search}%') |
            Vehicle.owner_name.ilike(f'%{search}%') |
            Vehicle.owner_id.ilike(f'%{search}%')
        )
    if status:
        query = query.filter_by(status=status)

    pagination = query.order_by(Vehicle.registered_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    # Frontend calls setVehicles(data) — expects a plain array
    return jsonify([_to_camel(v) for v in pagination.items]), 200


@vehicles_bp.route('/<int:vehicle_id>', methods=['GET'])
@jwt_required()
def get_vehicle(vehicle_id):
    v = Vehicle.query.get_or_404(vehicle_id)
    return jsonify(_to_camel(v)), 200


@vehicles_bp.route('', methods=['POST'])
@jwt_required()
def create_vehicle():
    if not _require_admin_or_security():
        return jsonify({'error': 'Forbidden'}), 403

    data  = request.get_json() or {}
    # Frontend sends camelCase
    plate = (data.get('plateNumber') or data.get('plate_number', '')).upper().strip()
    owner = data.get('ownerName') or data.get('owner_name', '')

    if not plate or not owner:
        return jsonify({'error': 'plateNumber and ownerName are required'}), 400

    if Vehicle.query.filter_by(plate_number=plate).first():
        return jsonify({'error': 'Plate number already registered'}), 409

    v = Vehicle(
        plate_number=plate,
        owner_name=owner,
        owner_id=data.get('ownerId') or data.get('owner_id'),
        vehicle_type=data.get('vehicleType') or data.get('vehicle_type', 'car'),
        department=data.get('department'),
        contact=data.get('contact'),
        status=data.get('status', 'active'),
        notes=data.get('notes'),
    )
    db.session.add(v)
    db.session.commit()
    return jsonify(_to_camel(v)), 201


@vehicles_bp.route('/<int:vehicle_id>', methods=['PUT'])
@jwt_required()
def update_vehicle(vehicle_id):
    if not _require_admin_or_security():
        return jsonify({'error': 'Forbidden'}), 403

    v    = Vehicle.query.get_or_404(vehicle_id)
    data = request.get_json() or {}

    if 'plateNumber' in data or 'plate_number' in data:
        plate = (data.get('plateNumber') or data.get('plate_number')).upper().strip()
        existing = Vehicle.query.filter_by(plate_number=plate).first()
        if existing and existing.id != vehicle_id:
            return jsonify({'error': 'Plate number already registered'}), 409
        v.plate_number = plate

    field_map = {
        'ownerName':   'owner_name',
        'ownerId':     'owner_id',
        'vehicleType': 'vehicle_type',
        'department':  'department',
        'contact':     'contact',
        'status':      'status',
        'notes':       'notes',
    }
    for camel, snake in field_map.items():
        if camel in data:
            setattr(v, snake, data[camel])
        elif snake in data:
            setattr(v, snake, data[snake])

    db.session.commit()
    return jsonify(_to_camel(v)), 200


@vehicles_bp.route('/<int:vehicle_id>', methods=['DELETE'])
@jwt_required()
def delete_vehicle(vehicle_id):
    if not _require_admin_or_security():
        return jsonify({'error': 'Forbidden'}), 403
    v = Vehicle.query.get_or_404(vehicle_id)
    db.session.delete(v)
    db.session.commit()
    return jsonify({'message': 'Vehicle deleted'}), 200
