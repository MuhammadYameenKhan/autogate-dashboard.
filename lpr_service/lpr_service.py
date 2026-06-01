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
import re

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


def stop_camera(wait: float = 2.0):
    """
    Stop the camera worker and release the capture device.
    Intended for emergency-stop / maintenance operations.
    """
    global _camera_thread, _camera_running
    _camera_running = False
    if _camera_thread and _camera_thread.is_alive():
        _camera_thread.join(timeout=wait)


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
    h, w = image.shape[:2]
    for result in results:
        for box in result.boxes:
            conf  = float(box.conf[0])
            if conf < 0.4:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            # Pad crop slightly; tight boxes can clip characters.
            pad_x = int(max(4, (x2 - x1) * 0.08))
            pad_y = int(max(4, (y2 - y1) * 0.15))
            x1p, y1p = max(0, x1 - pad_x), max(0, y1 - pad_y)
            x2p, y2p = min(w, x2 + pad_x), min(h, y2 + pad_y)
            crop = image[y1p:y2p, x1p:x2p]
            if crop.size > 0:
                plates.append((crop, conf))
    return plates if plates else [(image, 0.3)]


_PLATE_RE = re.compile(r'^[A-Z0-9]{4,10}$')


def _preprocess_variants(plate_bgr: np.ndarray):
    """
    Build multiple preprocessed variants for robust OCR.
    Returns a list of single-channel uint8 images.
    """
    if plate_bgr is None or plate_bgr.size == 0:
        return []

    gray = cv2.cvtColor(plate_bgr, cv2.COLOR_BGR2GRAY)

    # Enlarge to help OCR on small plates.
    h, w = gray.shape[:2]
    scale = 3.0 if max(h, w) < 160 else 2.0
    resized = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Add border so characters near edges are not lost.
    bordered = cv2.copyMakeBorder(resized, 12, 12, 12, 12, cv2.BORDER_REPLICATE)

    # Normalize contrast.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    norm = clahe.apply(bordered)

    # Denoise lightly.
    den = cv2.fastNlMeansDenoising(norm, None, h=12, templateWindowSize=7, searchWindowSize=21)

    # Two binarization strategies.
    blur = cv2.GaussianBlur(den, (3, 3), 0)
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    adap = cv2.adaptiveThreshold(
        den, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 7
    )

    # Morph close to connect broken strokes.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    otsu_closed = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel, iterations=1)
    adap_closed = cv2.morphologyEx(adap, cv2.MORPH_CLOSE, kernel, iterations=1)

    return [otsu, adap, otsu_closed, adap_closed]


def _score_plate_text(raw: str):
    """
    Clean and score OCR output; higher score = more plausible plate.
    Returns (clean_plate, score).
    """
    clean = ''.join(c for c in (raw or '').upper() if c.isalnum())
    if not clean:
        return '', 0.0

    score = 0.0
    if _PLATE_RE.match(clean):
        score += 2.5

    # Prefer typical plate lengths (keep flexible).
    if 5 <= len(clean) <= 8:
        score += 1.5
    elif 4 <= len(clean) <= 10:
        score += 0.5

    # Penalize repetitive noise like "IIIIII" or "00000".
    if len(clean) >= 5 and len(set(clean)) <= 2:
        score -= 1.0

    return clean, score


def ocr_plate(plate_img: np.ndarray) -> str:
    """
    Run Tesseract OCR on a cropped plate image.
    Returns cleaned plate string.
    """
    # If Tesseract isn't on PATH, allow overriding via env var.
    tcmd = os.getenv('TESSERACT_CMD')
    if tcmd:
        pytesseract.pytesseract.tesseract_cmd = tcmd

    variants = _preprocess_variants(plate_img)
    if not variants:
        return ''

    # Try multiple page segmentation modes; plates vary.
    tesseract_confs = [
        '--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        '--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
    ]

    best_plate = ''
    best_score = 0.0

    for img in variants:
        for cfg in tesseract_confs:
            try:
                raw = pytesseract.image_to_string(img, config=cfg)
            except Exception as e:
                logger.warning(f"Tesseract OCR failed: {e}")
                continue
            plate, score = _score_plate_text(raw)
            if score > best_score:
                best_plate, best_score = plate, score

    return best_plate


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
    while _camera_running:
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


def ocr_timetable_text(image: np.ndarray) -> str:
    """OCR full timetable image (document mode, not plate mode)."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    scale = max(1.0, 1800 / max(w, h))
    if scale > 1.0:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    config = '--oem 3 --psm 6'
    return pytesseract.image_to_string(thresh, config=config).strip()


def _parse_timetable_text(raw_text: str) -> list:
    """Lightweight parser for timetable OCR output."""
    import re

    days = {
        'mon': 'Monday', 'monday': 'Monday', 'tue': 'Tuesday', 'tuesday': 'Tuesday',
        'wed': 'Wednesday', 'wednesday': 'Wednesday', 'thu': 'Thursday', 'thursday': 'Thursday',
        'fri': 'Friday', 'friday': 'Friday', 'sat': 'Saturday', 'saturday': 'Saturday',
        'sun': 'Sunday', 'sunday': 'Sunday',
    }
    day_re = re.compile(
        r'\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|'
        r'Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b', re.I
    )
    time_range_re = re.compile(
        r'(\d{1,2})\s*[:.]\s*(\d{2})\s*(?:-|–|—|to)\s*(\d{1,2})\s*[:.]\s*(\d{2})', re.I
    )
    time_single_re = re.compile(r'\b(\d{1,2})\s*[:.]\s*(\d{2})\b')
    building_re = re.compile(
        r'\b(?:block|building|bldg|room)\s*([A-Za-z0-9]{1,4})\b', re.I
    )

    classes = []
    seen = set()
    current_day = None

    for line in raw_text.splitlines():
        line = re.sub(r'\s+', ' ', line).strip()
        if not line:
            continue
        m = day_re.search(line)
        if m:
            key = m.group(1).lower()
            current_day = days.get(key) or days.get(key[:3]) or m.group(1).title()
        if not current_day:
            continue

        time_str = ''
        tr = time_range_re.search(line)
        if tr:
            time_str = f'{int(tr.group(1)):02d}:{tr.group(2)} - {int(tr.group(3)):02d}:{tr.group(4)}'
        else:
            times = time_single_re.findall(line)
            if len(times) >= 2:
                time_str = (
                    f'{int(times[0][0]):02d}:{times[0][1]} - '
                    f'{int(times[1][0]):02d}:{times[1][1]}'
                )
            elif times:
                time_str = f'{int(times[0][0]):02d}:{times[0][1]}'

        if not time_str:
            continue

        building = ''
        bm = building_re.search(line)
        if bm:
            building = bm.group(1).upper()

        course = day_re.sub('', line)
        course = time_range_re.sub('', course)
        course = time_single_re.sub('', course)
        course = building_re.sub('', course)
        course = re.sub(r'\s+', ' ', course).strip() or 'Class'

        entry = {
            'day': current_day,
            'time': time_str,
            'building': building or 'A',
            'course': course[:120],
        }
        key = (entry['day'], entry['time'], entry['course'])
        if key not in seen:
            seen.add(key)
            classes.append(entry)

    return classes


@app.route('/timetable/extract', methods=['POST'])
def timetable_extract():
    """Extract class schedule from uploaded timetable image."""
    if 'image' not in request.files:
        return jsonify({'error': 'image file required'}), 400

    file = request.files['image']
    img_bytes = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
    if image is None:
        return jsonify({'error': 'Invalid image'}), 422

    try:
        raw_text = ocr_timetable_text(image)
    except Exception as exc:
        return jsonify({'error': f'OCR failed: {exc}'}), 422

    classes = _parse_timetable_text(raw_text)
    return jsonify({'classes': classes, 'rawText': raw_text}), 200


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
