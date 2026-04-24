"""
Gate Service
Sends commands to the Desktop Barrier App via TCP socket.
"""
import socket
import json
import logging
from flask import current_app

logger = logging.getLogger(__name__)


def send_gate_command(command: str) -> dict:
    """
    Send a command string to the barrier app over TCP.
    Commands: 'open', 'close', 'emergency_stop', 'reset', 'status'
    """
    host    = current_app.config.get('GATE_HOST', '127.0.0.1')
    port    = int(current_app.config.get('GATE_PORT', 9999))
    timeout = int(current_app.config.get('GATE_TIMEOUT', 5))

    payload = json.dumps({'command': command}) + '\n'

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(payload.encode('utf-8'))
            response_data = b''
            while True:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                response_data += chunk
                if b'\n' in response_data:
                    break

        response = json.loads(response_data.decode('utf-8').strip())
        logger.info(f"Gate command '{command}' sent. Response: {response}")
        return {'success': True, 'command': command, 'response': response}

    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        logger.warning(f"Gate controller unreachable: {e}. Command '{command}' not sent.")
        return {'success': False, 'command': command, 'error': str(e)}
    except json.JSONDecodeError:
        logger.error("Invalid JSON response from gate controller")
        return {'success': False, 'command': command, 'error': 'Invalid response'}


def get_gate_status() -> dict:
    return send_gate_command('status')
