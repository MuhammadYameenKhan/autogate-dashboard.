"""Tests for parking booking endpoints."""
from app.extensions import db
from app.models import ParkingSpot, ParkingBooking


def test_get_available_slots(client, auth_headers):
    resp = client.get('/api/parking/slots/available?date=2026-04-01&time=09:00',
                      headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_book_slot(client, auth_headers, app):
    with app.app_context():
        spot = ParkingSpot.query.first()
        assert spot is not None
        spot_id = str(spot.id)

    resp = client.post('/api/parking/book', headers=auth_headers, json={
        'slotId':     spot_id,
        'date':       '2026-04-01',
        'time':       '09:00',
        'duration':   30,
        'expiryTime': '2026-04-01T09:30:00',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['slotId'] == spot_id


def test_my_bookings(client, auth_headers):
    resp = client.get('/api/parking/bookings/my', headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_suggested_slot(client, auth_headers):
    resp = client.get('/api/parking/suggested?date=2026-04-01&time=09:00',
                      headers=auth_headers)
    assert resp.status_code == 200


def test_booking_conflict_uses_time_overlap(client, auth_headers, app):
    with app.app_context():
        spot = ParkingSpot.query.first()
        assert spot is not None
        booking = ParkingBooking(
            user_id=1,
            spot_id=spot.id,
            booking_date='2026-04-01',
            booking_time='09:00',
            duration_minutes=30,
            expiry_time='2026-04-01T09:30:00',
            status='active',
            slot_location=spot.spot_number,
            building=spot.zone,
        )
        db.session.add(booking)
        db.session.commit()

    # Overlapping range (09:15-09:45) should conflict.
    overlap_resp = client.post('/api/parking/book', headers=auth_headers, json={
        'slotId': str(spot.id),
        'date': '2026-04-01',
        'time': '09:15',
        'duration': 30,
        'expiryTime': '2026-04-01T09:45:00',
    })
    assert overlap_resp.status_code == 409

    # Non-overlapping range (09:30-10:00) should be allowed.
    non_overlap_resp = client.post('/api/parking/book', headers=auth_headers, json={
        'slotId': str(spot.id),
        'date': '2026-04-01',
        'time': '09:30',
        'duration': 30,
        'expiryTime': '2026-04-01T10:00:00',
    })
    assert non_overlap_resp.status_code == 201
