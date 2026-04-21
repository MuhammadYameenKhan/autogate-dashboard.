"""Tests for vehicle CRUD endpoints."""


def test_list_vehicles(client, auth_headers):
    resp = client.get('/api/vehicles', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'vehicles' in data


def test_create_vehicle(client, auth_headers):
    resp = client.post('/api/vehicles', headers=auth_headers, json={
        'plate_number': 'NEW-999',
        'owner_name': 'Test Owner',
        'owner_id': 'OWN001',
        'vehicle_type': 'car',
        'department': 'CS',
        'status': 'active',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['plate_number'] == 'NEW-999'


def test_create_duplicate_plate(client, auth_headers):
    client.post('/api/vehicles', headers=auth_headers, json={
        'plate_number': 'DUP-001',
        'owner_name': 'First Owner',
    })
    resp = client.post('/api/vehicles', headers=auth_headers, json={
        'plate_number': 'DUP-001',
        'owner_name': 'Second Owner',
    })
    assert resp.status_code == 409


def test_update_vehicle(client, auth_headers):
    # create first
    r = client.post('/api/vehicles', headers=auth_headers, json={
        'plate_number': 'UPD-001',
        'owner_name': 'Old Name',
    })
    vid = r.get_json()['id']
    resp = client.put(f'/api/vehicles/{vid}', headers=auth_headers, json={
        'owner_name': 'New Name',
    })
    assert resp.status_code == 200
    assert resp.get_json()['owner_name'] == 'New Name'


def test_delete_vehicle(client, auth_headers):
    r = client.post('/api/vehicles', headers=auth_headers, json={
        'plate_number': 'DEL-001',
        'owner_name': 'To Delete',
    })
    vid = r.get_json()['id']
    resp = client.delete(f'/api/vehicles/{vid}', headers=auth_headers)
    assert resp.status_code == 200
