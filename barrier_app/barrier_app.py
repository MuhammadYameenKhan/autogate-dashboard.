"""
AutoGate Desktop Barrier Application
------------------------------------
- Listens on TCP port 9999 for gate commands from Flask backend
- Commands: open, close, emergency_stop, reset, status
- Simple PyQt5 GUI showing gate state + manual override buttons
- Also works in headless mode (no GUI) if PyQt5 not available

Run: python barrier_app.py [--headless] [--port 9999]
"""
import sys
import json
import socket
import logging
import threading
import argparse
import time
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ── Gate state ────────────────────────────────────────────────────────────────
class GateController:
    def __init__(self):
        self.is_open         = False
        self.emergency_stop  = False
        self.last_command    = 'none'
        self._lock           = threading.Lock()

    def execute(self, command: str) -> dict:
        with self._lock:
            if self.emergency_stop and command not in ('reset', 'status'):
                return {
                    'success': False,
                    'state': self._state(),
                    'message': 'Emergency stop active — reset first',
                }

            if command == 'open':
                self.is_open      = True
                self.last_command = 'open'
                logger.info("🔓 Gate OPENED")
                self._hardware_open()

            elif command == 'close':
                self.is_open      = False
                self.last_command = 'close'
                logger.info("🔒 Gate CLOSED")
                self._hardware_close()

            elif command == 'emergency_stop':
                self.emergency_stop = True
                self.is_open        = False
                self.last_command   = 'emergency_stop'
                logger.warning("🚨 EMERGENCY STOP ACTIVATED")
                self._hardware_close()

            elif command == 'reset':
                self.emergency_stop = False
                self.last_command   = 'reset'
                logger.info("✅ Emergency stop RESET")

            elif command == 'status':
                pass  # Just return current state

            else:
                return {
                    'success': False,
                    'state': self._state(),
                    'message': f'Unknown command: {command}',
                }

            return {'success': True, 'state': self._state()}

    def _state(self):
        return {
            'is_open': self.is_open,
            'emergency_stop': self.emergency_stop,
            'last_command': self.last_command,
        }

    def _hardware_open(self):
        """
        Replace this with actual GPIO / serial / relay control.
        Example for Raspberry Pi GPIO:
            import RPi.GPIO as GPIO
            GPIO.output(RELAY_PIN, GPIO.HIGH)
        """
        logger.debug("[HW] Sending OPEN signal to relay/GPIO")

    def _hardware_close(self):
        """
        Replace this with actual GPIO / serial / relay control.
        Example for Raspberry Pi GPIO:
            import RPi.GPIO as GPIO
            GPIO.output(RELAY_PIN, GPIO.LOW)
        """
        logger.debug("[HW] Sending CLOSE signal to relay/GPIO")


gate = GateController()


# ── TCP Server ────────────────────────────────────────────────────────────────
def handle_client(conn, addr):
    logger.info(f"Connection from {addr}")
    try:
        data = b''
        while True:
            chunk = conn.recv(1024)
            if not chunk:
                break
            data += chunk
            if b'\n' in data:
                break

        message = data.decode('utf-8').strip()
        payload = json.loads(message)
        command = payload.get('command', 'status')

        result   = gate.execute(command)
        response = json.dumps(result) + '\n'
        conn.sendall(response.encode('utf-8'))

    except json.JSONDecodeError:
        error_response = json.dumps({'success': False, 'error': 'Invalid JSON'}) + '\n'
        conn.sendall(error_response.encode('utf-8'))
    except Exception as e:
        logger.error(f"Client handler error: {e}")
    finally:
        conn.close()


def run_tcp_server(host='0.0.0.0', port=9999):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(10)
    logger.info(f"TCP gate server listening on {host}:{port}")

    while True:
        try:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Server error: {e}")


# ── PyQt5 GUI ─────────────────────────────────────────────────────────────────
def run_gui(port: int):
    try:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout,
            QHBoxLayout, QPushButton, QLabel, QFrame
        )
        from PyQt5.QtCore import Qt, QTimer
        from PyQt5.QtGui import QFont, QColor, QPalette
    except ImportError:
        logger.warning("PyQt5 not available — running headless")
        run_tcp_server(port=port)
        return

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("AutoGate — Barrier Control")
            self.setMinimumSize(460, 320)
            self._build_ui()

            # Poll gate state every 500 ms
            self._timer = QTimer()
            self._timer.timeout.connect(self._refresh_ui)
            self._timer.start(500)

        def _build_ui(self):
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setSpacing(14)
            layout.setContentsMargins(20, 20, 20, 20)

            # Title
            title = QLabel("🚗  AutoGate Barrier Control")
            title.setFont(QFont("Arial", 16, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            # Status indicator
            self.status_label = QLabel("● CLOSED")
            self.status_label.setFont(QFont("Arial", 22, QFont.Bold))
            self.status_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.status_label)

            self.emg_label = QLabel("")
            self.emg_label.setFont(QFont("Arial", 12))
            self.emg_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.emg_label)

            # Divider
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            layout.addWidget(line)

            # Control buttons
            btn_row = QHBoxLayout()

            self.btn_open = QPushButton("🔓  Open Gate")
            self.btn_open.setMinimumHeight(50)
            self.btn_open.setStyleSheet("background:#27ae60;color:white;font-size:14px;border-radius:6px;")
            self.btn_open.clicked.connect(lambda: gate.execute('open') or self._refresh_ui())
            btn_row.addWidget(self.btn_open)

            self.btn_close = QPushButton("🔒  Close Gate")
            self.btn_close.setMinimumHeight(50)
            self.btn_close.setStyleSheet("background:#2980b9;color:white;font-size:14px;border-radius:6px;")
            self.btn_close.clicked.connect(lambda: gate.execute('close') or self._refresh_ui())
            btn_row.addWidget(self.btn_close)

            layout.addLayout(btn_row)

            self.btn_emg = QPushButton("🚨  EMERGENCY STOP")
            self.btn_emg.setMinimumHeight(55)
            self.btn_emg.setStyleSheet("background:#e74c3c;color:white;font-size:15px;font-weight:bold;border-radius:6px;")
            self.btn_emg.clicked.connect(lambda: gate.execute('emergency_stop') or self._refresh_ui())
            layout.addWidget(self.btn_emg)

            self.btn_reset = QPushButton("✅  Reset Emergency Stop")
            self.btn_reset.setMinimumHeight(44)
            self.btn_reset.setStyleSheet("background:#e67e22;color:white;font-size:13px;border-radius:6px;")
            self.btn_reset.clicked.connect(lambda: gate.execute('reset') or self._refresh_ui())
            layout.addWidget(self.btn_reset)

            # Footer
            footer = QLabel(f"TCP Server: port {port}")
            footer.setAlignment(Qt.AlignCenter)
            footer.setStyleSheet("color:gray;font-size:11px;")
            layout.addWidget(footer)

        def _refresh_ui(self):
            state = gate._state()
            if state['emergency_stop']:
                self.status_label.setText("🚨  EMERGENCY STOP")
                self.status_label.setStyleSheet("color:#e74c3c;")
                self.emg_label.setText("All gate operations suspended")
            elif state['is_open']:
                self.status_label.setText("● OPEN")
                self.status_label.setStyleSheet("color:#27ae60;")
                self.emg_label.setText("")
            else:
                self.status_label.setText("● CLOSED")
                self.status_label.setStyleSheet("color:#2980b9;")
                self.emg_label.setText("")

    app_qt = QApplication(sys.argv)
    win = MainWindow()
    win.show()

    # Run TCP server in background thread
    tcp_thread = threading.Thread(target=run_tcp_server, kwargs={'port': port}, daemon=True)
    tcp_thread.start()

    sys.exit(app_qt.exec_())


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AutoGate Barrier App')
    parser.add_argument('--headless', action='store_true', help='Run without GUI')
    parser.add_argument('--port', type=int, default=9999, help='TCP port (default 9999)')
    parser.add_argument('--host', default='0.0.0.0', help='TCP host (default 0.0.0.0)')
    args = parser.parse_args()

    if args.headless:
        run_tcp_server(host=args.host, port=args.port)
    else:
        run_gui(port=args.port)
