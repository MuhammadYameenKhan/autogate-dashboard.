"""Tests for parking endpoints."""


def test_get_availability(client, auth_headers):
    resp = client.get('/api/parking/availability', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'totalCapacity' in data
    assert 'available' in data
    assert 'occupied' in data


def test_log_entry_event(client):
    resp = client.post('/api/parking/event', json={
        'plate_number': 'TEST-001',
        'event_type': 'entry',
        'gate': 'main',
        'confidence': 0.95,
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['status'] in ('allowed', 'denied', 'unknown')


def test_log_unknown_plate(client):
    resp = client.post('/api/parking/event', json={
        'plate_number': 'UNKNOWN-XYZ',
        'event_type': 'entry',
        'gate': 'main',
        'confidence': 0.80,
    })
    assert resp.status_code == 201
    assert resp.get_json()['status'] == 'unknown'


def test_currently_parked(client, auth_headers):
    # log an entry first
    client.post('/api/parking/event', json={
        'plate_number': 'TEST-001',
        'event_type': 'entry',
        'gate': 'main',
        'confidence': 1.0,
    })
    resp = client.get('/api/parking/currently-parked', headers=auth_headers)
    assert resp.status_code == 200
    assert 'vehicles' in resp.get_json()
