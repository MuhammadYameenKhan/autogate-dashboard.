"""Tests for auth endpoints."""


def test_login_success(client):
    resp = client.post('/api/auth/login', json={
        'user_id': 'TESTADMIN',
        'password': 'Test@123'
    })
    data = resp.get_json()
    assert resp.status_code == 200
    assert 'token' in data
    assert data['user']['role'] == 'admin'


def test_login_wrong_password(client):
    resp = client.post('/api/auth/login', json={
        'user_id': 'TESTADMIN',
        'password': 'wrongpassword'
    })
    assert resp.status_code == 401


def test_signup(client):
    resp = client.post('/api/auth/signup', json={
        'user_id': 'NEWUSER01',
        'username': 'newuser',
        'email': 'newuser@test.com',
        'password': 'NewUser@123'
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'token' in data


def test_me(client, auth_headers):
    resp = client.get('/api/auth/me', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['username'] == 'testadmin'
