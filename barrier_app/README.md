# AutoGate Barrier (Desktop) App

TCP socket server + optional PyQt5 GUI for controlling the physical gate barrier.

## Setup

```bash
cd barrier_app
pip install -r requirements.txt   # only needed for GUI mode
```

## Run

GUI mode (default):
```bash
python barrier_app.py
```

Headless mode (no GUI, e.g. on Raspberry Pi):
```bash
python barrier_app.py --headless --port 9999
```

## Hardware Integration

Edit `_hardware_open()` and `_hardware_close()` in `barrier_app.py` to control your relay/GPIO:

```python
# Raspberry Pi example
import RPi.GPIO as GPIO
RELAY_PIN = 17

def _hardware_open(self):
    GPIO.output(RELAY_PIN, GPIO.HIGH)

def _hardware_close(self):
    GPIO.output(RELAY_PIN, GPIO.LOW)
```

## TCP Protocol

The Flask backend connects to `127.0.0.1:9999` and sends JSON commands:

```json
{"command": "open"}
{"command": "close"}
{"command": "emergency_stop"}
{"command": "reset"}
{"command": "status"}
```

Response:
```json
{"success": true, "state": {"is_open": true, "emergency_stop": false, "last_command": "open"}}
```
