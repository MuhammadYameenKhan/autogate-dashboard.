"""
Database initialization and seeding script.
Run: python migrations/init_db.py
Creates all tables and seeds demo data.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User, Vehicle, ParkingSpot, GateStatus, ParkingBooking, Timetable


def init_db():
    app = create_app('development')
    with app.app_context():
        print("Creating all tables...")
        db.create_all()

        # ── Admin user ───────────────────────────────────────────────────────
        if not User.query.filter_by(username='admin').first():
            admin = User(user_id='ADMIN001', username='admin',
                         email='admin@ucp.edu.pk', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            print("✅  Admin user  (username: admin / password: admin123)")

        # ── Security user ────────────────────────────────────────────────────
        if not User.query.filter_by(username='security').first():
            sec = User(user_id='SEC001', username='security',
                       email='security@ucp.edu.pk', role='security')
            sec.set_password('Security@123')
            db.session.add(sec)
            print("✅  Security user  (username: security / password: Security@123)")

        # ── Demo vehicles (camelCase contact field) ──────────────────────────
        demo_vehicles = [
            dict(plate_number='LHR-1234', owner_name='Ahmed Khan',
                 owner_id='L1F22BSCS0001', vehicle_type='car',
                 department='Computer Science', contact='03001234567', status='active'),
            dict(plate_number='LHR-5678', owner_name='Sara Ali',
                 owner_id='L1F22BSCS0002', vehicle_type='car',
                 department='Electrical Engineering', contact='03111234567', status='active'),
            dict(plate_number='ISB-9999', owner_name='Prof. Irfan',
                 owner_id='FAC001', vehicle_type='car',
                 department='Faculty', contact='03211234567', status='active'),
            dict(plate_number='KHI-0001', owner_name='Usman Raza',
                 owner_id='L1F22BSCS0003', vehicle_type='bike',
                 department='Business Administration', contact='03311234567', status='active'),
        ]
        for vdata in demo_vehicles:
            if not Vehicle.query.filter_by(plate_number=vdata['plate_number']).first():
                db.session.add(Vehicle(**vdata))
        print(f"✅  {len(demo_vehicles)} demo vehicles seeded")

        # ── Parking spots (100 spots, zones A-D) ────────────────────────────
        if ParkingSpot.query.count() == 0:
            for zone in ['A', 'B', 'C', 'D']:
                for i in range(25):
                    db.session.add(ParkingSpot(
                        spot_number=f"{zone}{i+1:02d}",
                        zone=zone,
                    ))
            print("✅  100 parking spots created (zones A–D)")

        # ── Gate status ──────────────────────────────────────────────────────
        if not GateStatus.query.filter_by(gate_name='main').first():
            db.session.add(GateStatus(gate_name='main', is_open=False, emergency_stop=False))
            print("✅  Gate status record created")

        db.session.commit()
        print("\n🎉  Database initialized successfully!")
        print("\nDefault login credentials:")
        print("  Admin    → username: admin     / password: admin123")
        print("  Security → username: security  / password: Security@123")


if __name__ == '__main__':
    init_db()
