from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Resident, HealthWorker
import os
import re
from sqlalchemy import func
from extensions import limiter
import time

auth_bp = Blueprint('auth', __name__)

# =========================
# SECURITY CONFIG (SET IN APP.PY ALSO)
# =========================
SESSION_TIMEOUT = 30  # minutes
MAX_LOGIN_ATTEMPTS = 15


# =========================
# HOME (LOGIN PAGE)
# =========================
@auth_bp.route('/')
def home():
    return render_template('index.html',
        username=session.pop('username', ''),
        username_error=session.pop('username_error', None),
        password_error=session.pop('password_error', None),
        general_error=session.pop('general_error', None)
    )


# =========================
# REGISTER PAGE
# =========================
@auth_bp.route('/register_page')
def register_page():
    return render_template('register.html')


# =========================
# REGISTER
# =========================
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.form

    fullname = data.get('fullname', '').strip()
    username = data.get('username', '').strip().lower()
    password = data.get('password')
    role = data.get('role')

    resident_contact = data.get('resident_contact', '').strip()
    worker_contact = data.get('worker_contact', '').strip()

    # REQUIRED FIELDS
    if not fullname or not username or not password:
        return render_template('register.html', general_error="All fields are required", form_data=data)

    # STRONG PASSWORD (uppercase, lowercase, number, special char)
    strong_password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$'
    if not re.match(strong_password_pattern, password):
        return render_template('register.html',
            
            password_error="Password must be 8+ chars with uppercase, lowercase, and number",
            form_data=data
        )

    # ROLE
    if not role:
        return render_template('register.html', role_error="Please select a role", form_data=data)

    # USERNAME VALIDATION
    if not re.match("^[a-z][a-z0-9_]{4,14}$", username):
        return render_template('register.html',
            username_error="Username must start with a letter (5–15 chars)",
            form_data=data
        )

    # USERNAME EXISTS
    if User.query.filter(func.lower(User.username) == username).first():
        return render_template('register.html', username_error="Username already exists", form_data=data)

    # CONTACT VALIDATION
    ph_pattern = r"^(09\d{9}|\+639\d{9})$"

    contact = resident_contact if role == "Resident" else worker_contact

    if not contact:
        return render_template('register.html', contact_error="Contact number is required", form_data=data)

    if not re.match(ph_pattern, contact):
        return render_template('register.html', contact_error="Invalid PH contact number", form_data=data)

    # CHECK CONTACT UNIQUENESS
    if Resident.query.filter_by(contact=contact).first() or HealthWorker.query.filter_by(contact=contact).first():
        return render_template('register.html', contact_error="Contact already registered", form_data=data)

    # HEALTH WORKER VALIDATION
    if role == "HealthWorker":
        worker_code = data.get('worker_code')
        if not worker_code or worker_code != os.getenv("HEALTH_WORKER_CODE"):
            return render_template('register.html', worker_code_error="Invalid Health Worker Code", form_data=data)

        valid_positions = ["Nurse", "Midwife", "Barangay Health Worker"]
        position = data.get('position')

        if position not in valid_positions:
            return render_template('register.html', position_error="Invalid position", form_data=data)

    # CREATE USER
    new_user = User(
        fullname=fullname,
        username=username,
        password=generate_password_hash(password),
        role=role
    )

    db.session.add(new_user)
    db.session.commit()

    if role == "Resident":
        db.session.add(Resident(
            name=fullname,
            gender=data.get('gender'),
            address=data.get('address'),
            contact=contact,
            user_id=new_user.id
        ))

    elif role == "HealthWorker":
        db.session.add(HealthWorker(
            name=fullname,
            position=data.get('position'),
            contact=contact,
            user_id=new_user.id
        ))

    db.session.commit()

    flash("Account created successfully!", "success")
    return redirect(url_for('auth.home'))


# =========================
# LOGIN (WITH PROTECTION)
# =========================
@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '').strip()

    # ❗ STOP EMPTY
    if not username or not password:
        return render_template('index.html',
            general_error="Please enter username and password"
        )


    # Get attempts FIRST
    attempts = session.get('login_attempts', 0)

    # Reset if username changed
    if session.get('last_username') != username:
        attempts = 0
        session['login_attempts'] = 0

    # Save current username
    session['last_username'] = username

    lock_time = session.get('lock_time')

    # 🔒 CHECK LOCK
    if lock_time:
        if (time.time() - lock_time) < 300:
            session['general_error'] = "Too many attempts. Try again in 5 minutes."
            return redirect(url_for('auth.home'))
        else:
            session.pop('lock_time', None)
            session['login_attempts'] = 0
            attempts = 0

    # ✅ GET USER
    user = User.query.filter(func.lower(User.username) == username).first()

    # ❌ USER NOT FOUND
    if not user:
        attempts += 1
        session['login_attempts'] = attempts

        if attempts >= MAX_LOGIN_ATTEMPTS:
            session['lock_time'] = time.time()
            return render_template('index.html',
                general_error="Too many attempts. Account locked for 5 minutes.",
                username=username
            )

        session['username'] = username
        session['username_error'] = "Username not found"
        return redirect(url_for('auth.home'))

    # ❌ WRONG PASSWORD
    if not check_password_hash(user.password, password):
        attempts += 1
        session['login_attempts'] = attempts

        if attempts >= MAX_LOGIN_ATTEMPTS:
            session['lock_time'] = time.time()
            return render_template('index.html',
                general_error="Too many attempts. Account locked for 5 minutes.",
                username=username
            )

        session['username'] = username
        session['password_error'] = "Incorrect password"
        return redirect(url_for('auth.home'))

    # ✅ SUCCESS LOGIN
    session.pop('login_attempts', None)
    session.pop('lock_time', None)

    session['user'] = user.username
    session['role'] = user.role
    session['user_id'] = user.id
    session['fullname'] = user.fullname
    session.permanent = True

    flash("Login successful!", "success")

    if user.role == "Resident":
        return redirect(url_for('resident.resident_dashboard'))
    else:
        return redirect(url_for('healthworker.health_worker_dashboard'))


# =========================
# LOGOUT
# =========================
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for('auth.home'))
