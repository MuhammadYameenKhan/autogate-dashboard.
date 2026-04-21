"""
AutoGate Flask Application Factory
"""
from flask import Flask
from flask_cors import CORS
from .extensions import db, jwt, migrate, scheduler
from .config import config


def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Init extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.parking import parking_bp
    from .routes.vehicles import vehicles_bp
    from .routes.logs import logs_bp
    from .routes.forecast import forecast_bp
    from .routes.anomalies import anomalies_bp
    from .routes.ocr import ocr_bp
    from .routes.chatbot import chatbot_bp
    from .routes.gate import gate_bp
    from .routes.camera import camera_bp
    from .routes.timetable import timetable_bp

    app.register_blueprint(auth_bp,       url_prefix='/api/auth')
    app.register_blueprint(dashboard_bp,  url_prefix='/api/dashboard')
    app.register_blueprint(parking_bp,    url_prefix='/api/parking')
    app.register_blueprint(vehicles_bp,   url_prefix='/api/vehicles')
    app.register_blueprint(logs_bp,       url_prefix='/api/logs')
    app.register_blueprint(forecast_bp,   url_prefix='/api/forecast')
    app.register_blueprint(anomalies_bp,  url_prefix='/api/anomalies')
    app.register_blueprint(ocr_bp,        url_prefix='/api/ocr')
    app.register_blueprint(chatbot_bp,    url_prefix='/api/chatbot')
    app.register_blueprint(gate_bp,       url_prefix='/api/gate')
    app.register_blueprint(camera_bp,     url_prefix='/api/camera')
    app.register_blueprint(timetable_bp,  url_prefix='/api/timetable')

    # Start scheduler (APScheduler)
    if not scheduler.running:
        from .tasks import register_tasks
        register_tasks(scheduler, app)
        scheduler.init_app(app)
        scheduler.start()

    return app
