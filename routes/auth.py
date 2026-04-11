from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Resident, HealthWorker
import os

auth_bp = Blueprint('auth', __name__)

# =========================
# HOME (LOGIN PAGE)
# =========================
@auth_bp.route('/')
def home():
    return render_template('index.html')


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
    username = data.get('username', '').strip()
    password = data.get('password')
    role = data.get('role')

    # ✅ REQUIRED FIELDS
    if not fullname or not username or not password:
        return render_template('register.html',
            general_error="All fields are required",
            form_data=data
        )

    # ❌ PASSWORD VALIDATION
    if len(password) < 8:
        return render_template('register.html',
            password_error="Password must be at least 8 characters long",
            form_data=data
        )

    if password.isdigit() or password.isalpha():
        return render_template('register.html',
            password_error="Password must contain both letters and numbers",
            form_data=data
        )
    

    # ❌ ROLE
    if not role:
        return render_template('register.html',
            role_error="Please select a role",
            form_data=data
        )

    # ❌ USERNAME EXISTS
    if User.query.filter_by(username=username).first():
        return render_template('register.html',
            username_error="Username already exists",
            form_data=data
        )

    # 🔐 HEALTH WORKER CODE
    if role == "HealthWorker":
        worker_code = data.get('worker_code')

        if not worker_code:
            return render_template('register.html',
                worker_code_error="Health Worker Code is required",
                form_data=data
            )

        if worker_code != os.getenv("HEALTH_WORKER_CODE"):
            return render_template('register.html',
                worker_code_error="Invalid Health Worker Code",
                form_data=data
            )

        valid_positions = ["Nurse", "Midwife", "Barangay Health Worker"]

        position = data.get('position')

        if not position:
            return render_template('register.html',
                position_error="Please select a position",
                form_data=data
            )

        if position not in valid_positions:
            return render_template('register.html',
                position_error="Invalid position selected",
                form_data=data
            )
    
    # ✅ CREATE USER
    new_user = User(
        fullname=fullname,
        username=username,
        password=generate_password_hash(password),
        role=role
    )

    db.session.add(new_user)
    db.session.commit()

    # 🔵 RESIDENT
    if role == "Resident":
        new_resident = Resident(
            name=fullname,
            gender=data.get('gender'),
            address=data.get('address'),
            contact=data.get('resident_contact'),
            user_id=new_user.id
        )
        db.session.add(new_resident)

    # 🟢 HEALTH WORKER
    elif role == "HealthWorker":
        new_worker = HealthWorker(
            name=fullname,
            position=data.get('position'),
            contact=data.get('worker_contact'),
            user_id=new_user.id
        )
        db.session.add(new_worker)

    db.session.commit()

    flash("Account created successfully!", "success")
    return redirect(url_for('auth.home'))


# =========================
# LOGIN
# =========================
@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    user = User.query.filter_by(username=username).first()

    if not user:
        return render_template(
            'index.html',
            username_error="Invalid username",
            username=username
        )

    if not check_password_hash(user.password, password):
        return render_template(
            'index.html',
            password_error="Incorrect password",
            username=username
        )

    session['user'] = user.username
    session['role'] = user.role
    session['user_id'] = user.id
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