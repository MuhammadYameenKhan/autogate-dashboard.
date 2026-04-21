"""
AutoGate LPR (License Plate Recognition) Microservice
Runs on port 5001.

Endpoints:
  POST /recognize        — recognize plate from uploaded image
  GET  /camera/stream    — MJPEG stream from IP camera
  GET  /camera/snapshot  — single JPEG snapshot

Depends on: ultralytics (YOLOv8), pytesseract, opencv-python, flask
"""
import os
import io
import cv2
import time
import uuid
import logging
import requests
import threading
import numpy as np
import pytesseract
from flask import Flask, request, jsonify, Response
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BACKEND_EVENT_URL = os.getenv('BACKEND_EVENT_URL', 'http://localhost:5000/api/parking/event')
CAMERA_SOURCE     = os.getenv('CAMERA_SOURCE', '0')          # '0' = webcam, or RTSP URL
YOLO_MODEL_PATH   = os.getenv('YOLO_MODEL_PATH', 'models/yolov8_lpr.pt')
GATE_NAME         = os.getenv('GATE_NAME', 'main')
UPLOAD_FOLDER     = os.getenv('UPLOAD_FOLDER', '/tmp/lpr_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Load YOLOv8 model ─────────────────────────────────────────────────────────
try:
    model = YOLO(YOLO_MODEL_PATH)
    logger.info(f"YOLOv8 model loaded from {YOLO_MODEL_PATH}")
except Exception:
    logger.warning("YOLOv8 model not found — using fallback detection")
    model = None

# ── Camera thread globals ─────────────────────────────────────────────────────
_camera_lock  = threading.Lock()
_latest_frame = None
_camera_thread = None
_camera_running = False


def _camera_worker():
    """Background thread that continuously reads frames from camera."""
    global _latest_frame, _camera_running

    source = int(CAMERA_SOURCE) if CAMERA_SOURCE.isdigit() else CAMERA_SOURCE
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        logger.error(f"Cannot open camera source: {CAMERA_SOURCE}")
        _camera_running = False
        return

    logger.info(f"Camera opened: {CAMERA_SOURCE}")
    while _camera_running:
        ret, frame = cap.read()
        if ret:
            with _camera_lock:
                _latest_frame = frame.copy()
        time.sleep(0.033)  # ~30 fps

    cap.release()
    logger.info("Camera worker stopped")


def start_camera():
    global _camera_thread, _camera_running
    if _camera_thread and _camera_thread.is_alive():
        return
    _camera_running = True
    _camera_thread = threading.Thread(target=_camera_worker, daemon=True)
    _camera_thread.start()


# Start camera on import
start_camera()

# ── LPR Pipeline ─────────────────────────────────────────────────────────────

def detect_plate_yolo(image: np.ndarray):
    """
    Run YOLOv8 to detect license plate bounding boxes.
    Returns list of cropped plate images with confidence scores.
    """
    if model is None:
        return [(image, 0.5)]  # Fallback: whole image

    results = model(image, verbose=False)
    plates = []
    for result in results:
        for box in result.boxes:
            conf  = float(box.conf[0])
            if conf < 0.4:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            crop = image[max(0, y1):y2, max(0, x1):x2]
            if crop.size > 0:
                plates.append((crop, conf))
    return plates if plates else [(image, 0.3)]


def ocr_plate(plate_img: np.ndarray) -> str:
    """
    Run Tesseract OCR on a cropped plate image.
    Returns cleaned plate string.
    """
    # Pre-process
    gray     = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
    resized  = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    blurred  = cv2.GaussianBlur(resized, (3, 3), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    config = '--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    text   = pytesseract.image_to_string(thresh, config=config)

    # Clean
    clean = ''.join(c for c in text.upper() if c.isalnum()).strip()
    return clean


def recognize_plate_from_image(image: np.ndarray):
    """Full pipeline: detect → OCR → return best plate."""
    plates = detect_plate_yolo(image)

    best_plate = ''
    best_conf  = 0.0

    for crop, det_conf in plates:
        text = ocr_plate(crop)
        if len(text) >= 4:
            # Combined confidence
            conf = det_conf * 0.7 + 0.3
            if conf > best_conf:
                best_plate = text
                best_conf  = conf

    return best_plate, best_conf


# ── Flask Endpoints ───────────────────────────────────────────────────────────

@app.route('/recognize', methods=['POST'])
def recognize():
    """Recognize plate from uploaded image file."""
    if 'image' not in request.files:
        return jsonify({'error': 'image file required'}), 400

    file = request.files['image']
    img_bytes = np.frombuffer(file.read(), np.uint8)
    image     = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)

    if image is None:
        return jsonify({'error': 'Invalid image'}), 422

    plate, confidence = recognize_plate_from_image(image)

    if not plate:
        return jsonify({'error': 'No plate detected', 'confidence': 0.0}), 422

    # Save image
    filename  = f"{uuid.uuid4().hex}.jpg"
    filepath  = os.path.join(UPLOAD_FOLDER, filename)
    cv2.imwrite(filepath, image)

    return jsonify({
        'plate_number': plate,
        'confidence': round(confidence, 3),
        'image_path': filepath,
    }), 200


@app.route('/trigger', methods=['POST'])
def trigger():
    """
    Capture frame from live camera, run LPR, and POST event to backend.
    Called by hardware trigger (e.g. IR sensor).
    """
    data       = request.get_json(silent=True) or {}
    event_type = data.get('event_type', 'entry')

    with _camera_lock:
        frame = _latest_frame.copy() if _latest_frame is not None else None

    if frame is None:
        return jsonify({'error': 'No camera frame available'}), 503

    plate, confidence = recognize_plate_from_image(frame)

    if not plate:
        return jsonify({'error': 'No plate detected', 'confidence': 0.0}), 422

    # Save snapshot
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    cv2.imwrite(filepath, frame)

    # Notify backend
    try:
        resp = requests.post(BACKEND_EVENT_URL, json={
            'plate_number': plate,
            'event_type':   event_type,
            'gate':         GATE_NAME,
            'confidence':   round(confidence, 3),
            'image_path':   filepath,
        }, timeout=5)
        backend_response = resp.json()
    except Exception as e:
        backend_response = {'error': str(e)}

    return jsonify({
        'plate_number': plate,
        'confidence':   round(confidence, 3),
        'event_type':   event_type,
        'backend':      backend_response,
    }), 200


def _generate_mjpeg():
    """Generator for MJPEG stream."""
    while True:
        with _camera_lock:
            frame = _latest_frame.copy() if _latest_frame is not None else None

        if frame is not None:
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' +
                buffer.tobytes() +
                b'\r\n'
            )
        time.sleep(0.033)


@app.route('/camera/stream', methods=['GET'])
def camera_stream():
    return Response(
        _generate_mjpeg(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/camera/snapshot', methods=['GET'])
def camera_snapshot():
    with _camera_lock:
        frame = _latest_frame.copy() if _latest_frame is not None else None

    if frame is None:
        return jsonify({'error': 'No frame available'}), 503

    _, buffer = cv2.imencode('.jpg', frame)
    return Response(buffer.tobytes(), mimetype='image/jpeg')


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'camera_running': _camera_running,
        'model_loaded': model is not None,
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('LPR_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
