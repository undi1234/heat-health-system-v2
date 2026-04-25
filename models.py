# =========================
# DATABASE MODELS
# =========================
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Resident(db.Model):
    __tablename__ = 'resident'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(100))
    contact = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))


class HealthWorker(db.Model):
    __tablename__ = 'health_worker'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    contact = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))


class Temperature(db.Model):
    __tablename__ = 'temperature'
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    time = db.Column(db.String(20))
    barangay = db.Column(db.String(50), nullable=False)


class HeatIndex(db.Model):
    __tablename__ = 'heat_index'
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float, nullable=False)
    heat_index = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    temperature_id = db.Column(db.Integer, db.ForeignKey('temperature.id', ondelete='CASCADE'))


class Illness(db.Model):
    __tablename__ = 'illness'
    id = db.Column(db.Integer, primary_key=True)
    symptoms = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    resident_id = db.Column(db.Integer, db.ForeignKey('resident.id', ondelete='CASCADE'))
    healthworker_id = db.Column(db.Integer, db.ForeignKey('health_worker.id', ondelete='CASCADE'))

    resident = db.relationship('Resident')
    healthworker = db.relationship('HealthWorker')