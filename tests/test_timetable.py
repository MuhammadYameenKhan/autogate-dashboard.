"""Tests for timetable endpoints."""


def test_get_timetable_empty(client, auth_headers):
    resp = client.get('/api/timetable/my', headers=auth_headers)
    assert resp.status_code == 200


def test_save_timetable(client, auth_headers):
    resp = client.post('/api/timetable/save', headers=auth_headers, json={
        'classes': [
            {'day': 'Monday', 'time': '08:00 - 09:30',
             'building': 'A', 'course': 'Data Structures'},
        ],
        'rawText': 'Monday 08:00 Data Structures Block A'
    })
    assert resp.status_code == 201
    assert resp.get_json()['classes'][0]['day'] == 'Monday'


def test_update_timetable(client, auth_headers):
    # First save
    client.post('/api/timetable/save', headers=auth_headers, json={
        'classes': [], 'rawText': ''
    })
    # Then update
    resp = client.put('/api/timetable/update', headers=auth_headers, json={
        'classes': [
            {'day': 'Tuesday', 'time': '10:00', 'building': 'B', 'course': 'OS'},
        ],
        'rawText': 'updated'
    })
    assert resp.status_code == 200


def test_get_timetable_after_save(client, auth_headers):
    client.post('/api/timetable/save', headers=auth_headers, json={
        'classes': [{'day': 'Friday', 'time': '11:00',
                     'building': 'C', 'course': 'Networks'}],
        'rawText': 'test'
    })
    resp = client.get('/api/timetable/my', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert 'classes' in data
