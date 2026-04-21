# AutoGate LPR Service

License Plate Recognition microservice using YOLOv8 + Tesseract.

## Setup

```bash
cd lpr_service
pip install -r requirements.txt

# Install Tesseract OCR (system)
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr

# Windows: download installer from
# https://github.com/UB-Mannheim/tesseract/wiki
```

## YOLOv8 Model

Place your trained YOLOv8 model at `lpr_service/models/yolov8_lpr.pt`.

To train your own model on license plate data:
```bash
yolo detect train data=plates.yaml model=yolov8n.pt epochs=100
```

If no model is present, the service falls back to full-image Tesseract OCR.

## Run

```bash
cd lpr_service
python lpr_service.py
# Runs on http://localhost:5001
```

## Environment Variables
```
LPR_PORT=5001
BACKEND_EVENT_URL=http://localhost:5000/api/parking/event
CAMERA_SOURCE=0          # 0=webcam, or rtsp://... for IP camera
YOLO_MODEL_PATH=models/yolov8_lpr.pt
GATE_NAME=main
UPLOAD_FOLDER=/tmp/lpr_uploads
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/recognize` | Recognize plate from uploaded image |
| POST | `/trigger` | Capture live frame + recognize + notify backend |
| GET | `/camera/stream` | MJPEG stream |
| GET | `/camera/snapshot` | Single JPEG frame |
| GET | `/health` | Health check |
