"""
AutoGate Backend - Main Entry Point
Run: python run.py
"""
from app import create_app
from app.extensions import db
from app.models import User, Vehicle, ParkingLog, ParkingSpot, Anomaly, ForecastCache, GateStatus, ParkingBooking, Timetable
import os

app = create_app(os.getenv('FLASK_ENV', 'development'))

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Vehicle': Vehicle,
        'ParkingLog': ParkingLog,
        'ParkingSpot': ParkingSpot,
        'Anomaly': Anomaly,
        'ForecastCache': ForecastCache,
        'ParkingBooking': ParkingBooking,
        'Timetable': Timetable,
    }

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        # port=int(os.getenv('PORT', 5000)),  # temporarily commented to investigate JWT error
        port=5000,
        debug=os.getenv('FLASK_ENV') == 'development'
    )
