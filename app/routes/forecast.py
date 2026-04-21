"""
Forecast Routes: /api/forecast/
Frontend reads: data (array) directly — setForecastData(data)
Each item: { timestamp, predictedOccupancy, actualOccupancy? }
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from ..models import ForecastCache
from ..services.forecast_service import generate_forecast

forecast_bp = Blueprint('forecast', __name__)


@forecast_bp.route('', methods=['GET'])
@jwt_required()
def get_forecast():
    period = request.args.get('period', '24h')
    if period not in ('24h', '48h', '72h'):
        return jsonify({'error': 'period must be 24h, 48h, or 72h'}), 400

    cached = (
        ForecastCache.query
        .filter_by(period=period)
        .order_by(ForecastCache.generated_at.desc())
        .first()
    )

    if cached:
        import json
        # Frontend calls setForecastData(data) — expects a plain array
        forecast_list = json.loads(cached.forecast_json)
        return jsonify(forecast_list), 200

    result = generate_forecast(period)
    # result['forecast'] is the array
    return jsonify(result.get('forecast', [])), 200


@forecast_bp.route('/refresh', methods=['POST'])
@jwt_required()
def refresh_forecast():
    body   = request.get_json(silent=True) or {}
    period = body.get('period', '24h')
    result = generate_forecast(period)
    return jsonify(result.get('forecast', [])), 200
