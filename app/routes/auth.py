"""
Auth Routes: /api/auth/
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from ..extensions import db
from ..models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    user_id_or_username = data.get('user_id') or data.get('username')
    password = data.get('password')

    if not user_id_or_username or not password:
        return jsonify({'error': 'user_id/username and password are required'}), 400

    user = User.query.filter(
        (User.user_id == user_id_or_username) |
        (User.username == user_id_or_username)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 403

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        'token': access_token,           # frontend reads response.token
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Frontend sends: { username, email, password, userId }
    username  = data.get('username')
    email     = data.get('email')
    password  = data.get('password')
    user_id   = data.get('userId') or data.get('user_id')

    if not all([username, email, password, user_id]):
        return jsonify({'error': 'username, email, password and userId are required'}), 400

    if User.query.filter_by(user_id=user_id).first():
        return jsonify({'error': 'User ID already registered'}), 409
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(
        user_id=user_id,
        username=username,
        email=email,
        role=data.get('role', 'user')
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        'token': access_token,           # frontend reads response.token
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 201


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({'access_token': access_token}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200


@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    """Admin: list all users"""
    current_user = User.query.get(int(get_jwt_identity()))
    if current_user.role != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    users = User.query.all()
    return jsonify([u.to_dict() for u in users]), 200
