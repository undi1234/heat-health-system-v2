# =========================
# DATABASE MODELS
# =========================
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))


class Resident(db.Model):
    __tablename__ = 'resident'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    gender = db.Column(db.String(10))
    address = db.Column(db.String(100))
    contact = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class HealthWorker(db.Model):
    __tablename__ = 'health_worker'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    position = db.Column(db.String(50))
    contact = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Temperature(db.Model):
    __tablename__ = 'temperature'
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Float)
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    barangay = db.Column(db.String(50))


class HeatIndex(db.Model):
    __tablename__ = 'heat_index'
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float)
    heat_index = db.Column(db.Float)
    status = db.Column(db.String(20))
    date = db.Column(db.String(20))
    temperature_id = db.Column(db.Integer, db.ForeignKey('temperature.id'))


class Illness(db.Model):
    __tablename__ = 'illness'
    id = db.Column(db.Integer, primary_key=True)
    symptoms = db.Column(db.String(200))
    status = db.Column(db.String(50))
    date = db.Column(db.String(20))
    resident_id = db.Column(db.Integer, db.ForeignKey('resident.id'))
    healthworker_id = db.Column(db.Integer, db.ForeignKey('health_worker.id'))

    resident = db.relationship('Resident')
    healthworker = db.relationship('HealthWorker')