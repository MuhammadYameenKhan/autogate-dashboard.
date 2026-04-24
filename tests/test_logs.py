"""Tests for logs endpoint."""


def test_get_logs(client, auth_headers):
    resp = client.get('/api/logs', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'logs' in data
    assert 'total' in data


def test_filter_logs_by_event(client, auth_headers):
    resp = client.get('/api/logs?event_type=entry', headers=auth_headers)
    assert resp.status_code == 200
    logs = resp.get_json()['logs']
    for log in logs:
        assert log['eventType'] == 'entry'


def test_filter_logs_by_status(client, auth_headers):
    resp = client.get('/api/logs?status=unknown', headers=auth_headers)
    assert resp.status_code == 200


def test_logs_pagination(client, auth_headers):
    resp = client.get('/api/logs?page=1&per_page=5', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['perPage'] == 5
