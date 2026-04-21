"""Tests for dashboard stats endpoint."""


def test_dashboard_stats(client, auth_headers):
    resp = client.get('/api/dashboard/stats', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    expected_keys = [
        'total_spots', 'available_spots', 'currently_parked',
        'occupancy_percentage', 'entries_today', 'exits_today',
        'denied_today', 'active_anomalies', 'hourly_traffic', 'timestamp'
    ]
    for key in expected_keys:
        assert key in data, f"Missing key: {key}"


def test_dashboard_requires_auth(client):
    resp = client.get('/api/dashboard/stats')
    assert resp.status_code == 401
