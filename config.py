import os
import secrets
from datetime import timedelta

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv("SESSION_TIMEOUT", 30)))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Clarin,Bohol,PH")

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///development.db"

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    # Get database URL from environment and fix PostgreSQL URL format
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if DATABASE_URL:
        # Fix Render postgres URL format (postgres:// -> postgresql+psycopg2://)
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
        elif DATABASE_URL.startswith("postgresql://"):
            DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Fallback to MySQL if DATABASE_URL not set
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{os.getenv('DB_USER','root')}:{os.getenv('DB_PASSWORD','')}@localhost/{os.getenv('DB_NAME','heat_health_db')}"
    
    # Connection pooling settings for reliability
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 10,
        "max_overflow": 20
    }

