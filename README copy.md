# AutoGate Backend — Complete & Updated

Full backend for the AutoGate AI-powered campus parking system (UCP FYP).
All 27 frontend API calls are implemented and field names match the React frontend exactly.

---

## Quick Start

```bash
cd autogate-dashboard
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # edit DATABASE_URL + secret keys
python migrations/init_db.py   # create tables + seed demo data
python run.py                  # API on http://localhost:5000
```

**Default credentials** (seeded by init_db.py):

| Role     | Username   | Password       |
|----------|------------|----------------|
| Admin    | `admin`    | `Admin@123`    |
| Security | `security` | `Security@123` |

---

## All 27 API Endpoints

### Auth
| Method | Endpoint | Notes |
|--------|----------|-------|
| POST | `/api/auth/login` | returns `{ token, user }` |
| POST | `/api/auth/signup` | sends `{ username, email, password, userId }` |

### Dashboard
| Method | Endpoint |
|--------|----------|
| GET | `/api/dashboard/stats` |

### Parking
| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/api/parking/availability` | |
| GET | `/api/parking/currently-parked` | |
| GET | `/api/parking/slots/available` | `?date=&time=` |
| POST | `/api/parking/book` | |
| GET | `/api/parking/bookings/my` | |
| POST | `/api/parking/bookings/:id/cancel` | |
| GET | `/api/parking/suggested` | smart slot suggestion |
| POST | `/api/parking/event` | called by LPR service |

### Vehicles
| Method | Endpoint |
|--------|----------|
| GET | `/api/vehicles` |
| POST | `/api/vehicles` |
| PUT | `/api/vehicles/:id` |
| DELETE | `/api/vehicles/:id` |

### Logs
| Method | Endpoint |
|--------|----------|
| GET | `/api/logs` |
| GET | `/api/logs/export` |

### Forecast
| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/api/forecast` | `?period=24h\|48h\|72h` |

### Anomalies
| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/api/anomalies` | `?filter=all\|active\|resolved` |
| POST | `/api/anomalies/:id/resolve` | |
| POST | `/api/anomalies/:id/false-positive` | |

### OCR / Offline Import
| Method | Endpoint |
|--------|----------|
| POST | `/api/ocr/offline` |

### Timetable
| Method | Endpoint |
|--------|----------|
| POST | `/api/timetable/extract` |
| POST | `/api/timetable/save` |
| PUT | `/api/timetable/update` |
| GET | `/api/timetable/my` |

### Chatbot
| Method | Endpoint |
|--------|----------|
| POST | `/api/chatbot/message` |

### Gate
| Method | Endpoint |
|--------|----------|
| POST | `/api/gate/emergency-stop` |
| POST | `/api/gate/reset-emergency-stop` |
| GET | `/api/gate/status` |

### Camera
| Method | Endpoint |
|--------|----------|
| GET | `/api/camera/feed` |

---

## Architecture

```
React Dashboard  ──►  Flask API (port 5000)
                            │
           ┌────────────────┼───────────────────┐
           │                │                   │
     PostgreSQL       LPR Service          Rasa Chatbot
                      (port 5001)          (port 5005)
                      YOLOv8+OCR        ► Actions (5055)
                            │
                   Desktop Barrier App
                      (TCP port 9999)
                      PyQt5 GUI + relay
```

## Running All Services

```bash
# Flask API
python run.py

# LPR microservice
cd lpr_service && python lpr_service.py

# Barrier (gate controller) desktop app
cd barrier_app && python barrier_app.py

# Rasa chatbot
cd rasa_chatbot
rasa train
rasa run actions --port 5055       # terminal 1
rasa run --enable-api --port 5005  # terminal 2
```

## Docker (full stack)
```bash
docker-compose up --build
```

## Tests
```bash
pytest tests/ -v
```

## Project Structure

```
autogate-dashboard/
├── run.py
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py          # app factory + blueprint registration
│   ├── config.py
│   ├── extensions.py        # db, jwt, migrate, scheduler
│   ├── models.py            # User, Vehicle, ParkingLog, ParkingSpot,
│   │                        # Anomaly, ForecastCache, GateStatus,
│   │                        # ParkingBooking, Timetable
│   ├── tasks.py             # APScheduler background jobs
│   ├── routes/
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── parking.py       # availability + bookings
│   │   ├── vehicles.py
│   │   ├── logs.py
│   │   ├── forecast.py
│   │   ├── anomalies.py
│   │   ├── ocr.py
│   │   ├── timetable.py     # NEW
│   │   ├── chatbot.py
│   │   ├── gate.py
│   │   └── camera.py
│   └── services/
│       ├── gate_service.py
│       ├── anomaly_service.py
│       └── forecast_service.py
├── lpr_service/
├── barrier_app/
├── rasa_chatbot/
├── migrations/
│   └── init_db.py
└── tests/
    ├── conftest.py
    ├── test_auth.py
    ├── test_dashboard.py
    ├── test_parking.py
    ├── test_vehicles.py
    ├── test_logs.py
    ├── test_anomalies.py
    ├── test_booking.py      # NEW
    └── test_timetable.py    # NEW
```
