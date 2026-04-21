"""Tests for anomaly endpoints."""
from app.extensions import db
from app.models import Anomaly


def test_list_anomalies(client, auth_headers):
    resp = client.get('/api/anomalies', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'anomalies' in data


def test_resolve_anomaly(client, auth_headers, app):
    with app.app_context():
        a = Anomaly(
            plate_number='RES-001',
            anomaly_type='unknown_plate',
            severity='high',
            description='Test anomaly',
        )
        db.session.add(a)
        db.session.commit()
        aid = a.id

    resp = client.post(f'/api/anomalies/{aid}/resolve', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['resolved'] is True


def test_false_positive(client, auth_headers, app):
    with app.app_context():
        a = Anomaly(
            plate_number='FP-001',
            anomaly_type='ml_flagged',
            severity='medium',
            description='False positive test',
        )
        db.session.add(a)
        db.session.commit()
        aid = a.id

    resp = client.post(f'/api/anomalies/{aid}/false-positive', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['false_positive'] is True
    assert data['resolved'] is True
