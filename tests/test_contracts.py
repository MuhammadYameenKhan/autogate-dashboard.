"""Contract tests for documented API behaviors."""


def test_chatbot_response_contract(client):
    resp = client.post('/api/chatbot/message', json={'message': 'hello'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'responses' in data
    assert isinstance(data['responses'], list)
    assert 'message' in data
    assert isinstance(data['message'], str)


def test_logs_export_endpoint(client, auth_headers):
    resp = client.get('/api/logs/export', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type') == 'text/csv'


def test_gate_endpoints(client, auth_headers):
    status_resp = client.get('/api/gate/status', headers=auth_headers)
    assert status_resp.status_code == 200
    data = status_resp.get_json()
    assert 'gate_name' in data

    stop_resp = client.post('/api/gate/emergency-stop', headers=auth_headers)
    assert stop_resp.status_code == 200
    assert 'gate' in stop_resp.get_json()

    reset_resp = client.post('/api/gate/reset-emergency-stop', headers=auth_headers)
    assert reset_resp.status_code == 200
    assert 'gate' in reset_resp.get_json()


def test_camera_feed_endpoint(client):
    # Depends on external LPR service; in tests this may return 503.
    resp = client.get('/api/camera/feed')
    assert resp.status_code in (200, 503)
