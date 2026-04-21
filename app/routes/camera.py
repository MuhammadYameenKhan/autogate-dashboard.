"""
Camera Feed Routes: /api/camera/
"""
import requests
from flask import Blueprint, Response, current_app, jsonify

camera_bp = Blueprint('camera', __name__)


@camera_bp.route('/feed', methods=['GET'])
def camera_feed():
    """Proxy the MJPEG stream from LPR service."""
    lpr_url = current_app.config.get('LPR_SERVICE_URL', 'http://localhost:5001')
    camera_url = f'{lpr_url}/camera/stream'

    try:
        req = requests.get(camera_url, stream=True, timeout=5)
        return Response(
            req.iter_content(chunk_size=1024),
            content_type=req.headers.get('Content-Type', 'image/jpeg'),
            status=200
        )
    except Exception as e:
        # Return a placeholder image or error
        return jsonify({'error': f'Camera unavailable: {str(e)}'}), 503


@camera_bp.route('/snapshot', methods=['GET'])
def snapshot():
    """Get a single snapshot from the camera."""
    lpr_url = current_app.config.get('LPR_SERVICE_URL', 'http://localhost:5001')
    try:
        resp = requests.get(f'{lpr_url}/camera/snapshot', timeout=5)
        return Response(resp.content, content_type='image/jpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 503
