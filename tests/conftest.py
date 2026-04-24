"""
Test configuration and fixtures.
Run: pytest tests/
"""
import pytest
from app import create_app
from app.extensions import db as _db
from app.models import User, Vehicle, ParkingSpot


@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        _seed_test_data()
        yield app
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def auth_headers(client):
    resp = client.post('/api/auth/login', json={
        'username': 'testadmin',
        'password': 'Test@123'
    })
    data = resp.get_json()
    # auth.py now returns 'token' not 'access_token'
    token = data.get('token') or data.get('access_token')
    return {'Authorization': f'Bearer {token}'}


def _seed_test_data():
    admin = User(user_id='TESTADMIN', username='testadmin',
                 email='admin@test.com', role='admin')
    admin.set_password('Test@123')
    _db.session.add(admin)

    v = Vehicle(plate_number='TEST-001', owner_name='Test User',
                owner_id='TEST001', contact='0300000001', status='active')
    _db.session.add(v)

    # Add some parking spots for booking tests
    for zone in ['A', 'B']:
        for i in range(5):
            _db.session.add(ParkingSpot(
                spot_number=f"{zone}{i+1:02d}", zone=zone
            ))

    _db.session.commit()
