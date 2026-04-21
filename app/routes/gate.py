"""
Gate Control Routes: /api/gate/
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from ..services.gate_service import send_gate_command, get_gate_status
from ..models import GateStatus
from ..extensions import db
from datetime import datetime

gate_bp = Blueprint('gate', __name__)


@gate_bp.route('/status', methods=['GET'])
@jwt_required()
def status():
    gs = GateStatus.query.filter_by(gate_name='main').first()
    if not gs:
        gs = GateStatus(gate_name='main')
        db.session.add(gs)
        db.session.commit()
    return jsonify(gs.to_dict()), 200


@gate_bp.route('/open', methods=['POST'])
@jwt_required()
def open_gate():
    result = send_gate_command('open')
    return jsonify(result), 200


@gate_bp.route('/close', methods=['POST'])
@jwt_required()
def close_gate():
    result = send_gate_command('close')
    return jsonify(result), 200


@gate_bp.route('/emergency-stop', methods=['POST'])
@jwt_required()
def emergency_stop():
    result = send_gate_command('emergency_stop')
    gs = GateStatus.query.filter_by(gate_name='main').first()
    if not gs:
        gs = GateStatus(gate_name='main')
        db.session.add(gs)
    gs.emergency_stop = True
    gs.is_open = False
    gs.last_command = 'emergency_stop'
    gs.last_updated = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Emergency stop activated', 'gate': gs.to_dict()}), 200


@gate_bp.route('/reset-emergency-stop', methods=['POST'])
@jwt_required()
def reset_emergency_stop():
    result = send_gate_command('reset')
    gs = GateStatus.query.filter_by(gate_name='main').first()
    if not gs:
        gs = GateStatus(gate_name='main')
        db.session.add(gs)
    gs.emergency_stop = False
    gs.last_command = 'reset'
    gs.last_updated = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Emergency stop reset', 'gate': gs.to_dict()}), 200
