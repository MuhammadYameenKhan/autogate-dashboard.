# AutoGate Admin Dashboard

A modern React-based admin dashboard for the AutoGate AI-powered campus parking management system.

## Features

- **User Authentication**: Secure login and signup system with role-based access control
- **Real-time Dashboard**: Live monitoring of parking availability, currently parked vehicles, and system statistics
- **Live Camera Feed**: Real-time video feed from gate camera with license plate detection
- **Admin Chatbot**: Interactive chatbot on dashboard for admins to query system information
- **Public Chatbot**: Standalone chatbot page accessible to all users for parking queries
- **Emergency Stop**: Immediate gate control button for safety
- **Parking Management**: View parking availability and currently parked vehicles
- **Logs Viewer**: Filter and view historical entry/exit logs
- **Vehicle Management**: Register, update, and manage campus vehicles
- **Forecasting**: Predictive analytics for future parking availability using Prophet
- **Anomaly Detection**: Monitor and manage suspicious parking behaviors
- **Offline Log Import**: Upload images for manual license plate recognition

## Tech Stack

- **React 18** with TypeScript
- **Vite** for build tooling
- **React Router** for navigation
- **Recharts** for data visualization
- **Axios** for API communication
- **Lucide React** for icons

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file in the root directory:
```env
VITE_API_BASE_URL=http://localhost:5000/api
VITE_CAMERA_FEED_URL=http://localhost:5000/api/camera/feed
```

3. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`

### Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Project Structure

```
autogate-dashboard/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── DashboardLayout.tsx
│   │   │   └── DashboardLayout.css
│   │   └── ProtectedRoute.tsx
│   ├── context/
│   │   └── AuthContext.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── ParkingAvailability.tsx
│   │   ├── CurrentlyParked.tsx
│   │   ├── LogsViewer.tsx
│   │   ├── VehicleManagement.tsx
│   │   ├── Forecasting.tsx
│   │   ├── AnomalyDetection.tsx
│   │   ├── OfflineLogImport.tsx
│   │   ├── Login.tsx
│   │   ├── Signup.tsx
│   │   ├── Chatbot.tsx
│   │   ├── Auth.css
│   │   └── Chatbot.css
│   ├── services/
│   │   └── api.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## API Integration

The dashboard expects a Flask backend API running on `http://localhost:5000/api` (configurable via environment variables).

### Required API Endpoints

- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/parking/availability` - Parking availability data
- `GET /api/parking/currently-parked` - Currently parked vehicles
- `GET /api/parking/slots/available?date=&time=` - Available slots for booking
- `GET /api/parking/suggested?date=&time=` - Suggested slot from timetable
- `POST /api/parking/book` - Create slot booking
- `GET /api/parking/bookings/my` - Current user bookings
- `POST /api/parking/bookings/:id/cancel` - Cancel booking
- `GET /api/logs` - Entry/exit logs with filtering
- `GET /api/vehicles` - Vehicle list
- `POST /api/vehicles` - Create vehicle
- `PUT /api/vehicles/:id` - Update vehicle
- `DELETE /api/vehicles/:id` - Delete vehicle
- `GET /api/forecast` - Parking forecast data
- `GET /api/anomalies` - Anomaly list
- `POST /api/anomalies/:id/resolve` - Resolve anomaly
- `POST /api/anomalies/:id/false-positive` - Mark as false positive
- `POST /api/ocr/offline` - Upload offline image for OCR
- `POST /api/chatbot/message` - Send message to chatbot (returns `responses[]` and `message`)
- `POST /api/gate/emergency-stop` - Activate emergency stop
- `POST /api/gate/reset-emergency-stop` - Reset emergency stop
- `GET /api/camera/feed` - Get live camera feed (image stream)
- `POST /api/auth/login` - User login
- `POST /api/auth/signup` - User registration
- `POST /api/timetable/extract` - Extract classes from timetable image
- `POST /api/timetable/save` - Save extracted timetable
- `PUT /api/timetable/update` - Update saved timetable
- `GET /api/timetable/my` - Get current user timetable

## Features Overview

### Authentication
- **Login Page**: Secure login with username/ID and password
- **Signup Page**: User registration with User ID, username, email, and password
- **Role-based Access**: Different access levels for admin, security, and general users
- **Protected Routes**: All dashboard routes require authentication
- **Session Management**: Token-based authentication with localStorage

### Dashboard
- Real-time statistics cards
- **Live Camera Feed**: Real-time video feed from gate camera showing license plate detection
- **Admin Chatbot Interface**: Interactive chatbot for admins to query system information
- **Emergency Stop Button**: Immediate gate control for safety
- Quick action buttons
- Auto-refresh every 2 seconds

### Public Chatbot
- **Standalone Chatbot Page**: Accessible at `/chatbot` route (no authentication required)
- **User-friendly Interface**: Clean, modern design for general campus users
- **Parking Queries**: Users can ask about:
  - Parking availability
  - Vehicle entry/exit information
  - Daily/weekly summaries
  - General parking questions

### Parking Availability
- Live occupancy percentage
- Visual occupancy bar
- Trend indicators

### Currently Parked
- Real-time vehicle list
- Search functionality
- Entry time and duration

### Logs Viewer
- Advanced filtering (date range, event type, status)
- Search by plate number
- Export functionality

### Vehicle Management
- CRUD operations for vehicles
- Modal forms for add/edit
- Status management

### Forecasting
- Interactive charts using Recharts
- 24h/48h/72h forecast periods
- Model accuracy metrics

### Anomaly Detection
- Real-time anomaly alerts
- Severity classification
- Resolve/false positive actions

### Offline Log Import
- Image upload with preview
- OCR processing
- Manual log creation

## Development

### Code Style

- TypeScript strict mode enabled
- ESLint configured for React best practices
- CSS modules for component styling

### Adding New Pages

1. Create a new component in `src/pages/`
2. Add route in `src/App.tsx`
3. Add navigation item in `DashboardLayout.tsx`

## License

This project is part of the AutoGate system developed for University of Central Punjab.

