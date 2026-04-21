"""
AutoGate Configuration
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class BaseConfig:
    SECRET_KEY = os.getenv('SECRET_KEY', 'autogate-secret-key-change-in-prod')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'autogate-jwt-secret-change-in-prod')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # LPR Service
    LPR_SERVICE_URL = os.getenv('LPR_SERVICE_URL', 'http://localhost:5001')

    # Rasa Chatbot
    RASA_SERVER_URL = os.getenv('RASA_SERVER_URL', 'http://localhost:5005')

    # Gate TCP
    GATE_HOST = os.getenv('GATE_HOST', '127.0.0.1')
    GATE_PORT = int(os.getenv('GATE_PORT', 9999))
    GATE_TIMEOUT = 5

    # Parking
    TOTAL_PARKING_SPOTS = int(os.getenv('TOTAL_PARKING_SPOTS', 100))

    # Camera
    CAMERA_FEED_URL = os.getenv('CAMERA_FEED_URL', 'http://localhost:5001/camera/feed')

    # Upload folder
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/tmp/autogate_uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # APScheduler
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = 'Asia/Karachi'


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/autogate_dev'
    )


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
}
