from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Resident, HealthWorker
import os
import re
from sqlalchemy import func, text
from extensions import limiter
import time
from flask import jsonify

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
# CHECK USERNAME (AJAX)
# =========================
@auth_bp.route('/check-username')
@limiter.limit("20 per minute")
def check_username():
    username = request.args.get('username', '').strip()

    if not username:
        return jsonify({'exists': False})

    exists = User.query.filter(func.lower(User.username) == username.lower()).first() is not None
    return jsonify({'exists': exists})


# =========================
# SUGGEST USERNAMES (AJAX)
# =========================
@auth_bp.route('/suggest-usernames')
def suggest_usernames():
    fullname = request.args.get('fullname', '').strip().lower()

    suggestions = generate_username_suggestions(fullname)

    available = []
    for s in suggestions:
        exists = User.query.filter(func.lower(User.username) == s).first()
        if not exists:
            available.append(s)

    return jsonify({'suggestions': available})

# =========================
# USERNAME SUGGESTION LOGIC
# =========================
def generate_username_suggestions(fullname):
    parts = fullname.lower().split()
    if len(parts) < 2:
        return []

    first = parts[0]
    last = parts[-1]

    # optional nickname logic
    nickname_map = {
        "junrey": "jun",
        "johnathan": "john",
        "michael": "mike"
    }

    nick = nickname_map.get(first, first)

    # dynamic year (optional, you can pass birthyear later)
    year_suffix = str(time.localtime().tm_year)[-2:]

    suggestions = [
        first + last,
        first + last + year_suffix,
        first[0] + last,
        last + first,
        first + "_" + last,
        first + last + str(int(time.time()) % 100),  # random 2 digits
        nick + last
    ]

    # ✅ filter valid usernames
    valid = [
        s for s in suggestions
        if re.match(r"^[a-z][a-z0-9_]{4,14}$", s)
    ]

    return list(dict.fromkeys(valid))  # remove duplicates


# =========================
# FULLNAME FORMATTER
# =========================
def format_fullname(name):
    name = re.sub(r"\s+", " ", name).strip()  # remove extra spaces
    parts = name.split()
    formatted = []

    for word in parts:
        # Initial (D.)
        if re.match(r"^[A-Za-z]\.$", word):
            formatted.append(word.upper())

        elif "'" in word or "-" in word:
            separators = ["'", "-"]
            temp = [word]

            for sep in separators:
                new_temp = []
                for part in temp:
                    new_temp.extend(part.split(sep))
                temp = new_temp

            formatted_word = word
            for part in temp:
                formatted_word = formatted_word.replace(part, part.capitalize())

            formatted.append(formatted_word)

        # Normal words
        else:
            formatted.append(word.capitalize())

    return " ".join(formatted)


# =========================
# GIBBERISH CHECK
# =========================
def is_gibberish(name):
    vowels = "aeiou"
    letters = re.sub(r"[^a-z]", "", name)

    if len(letters) < 4:
        return False  # allow short names like "Ng"

    vowel_ratio = sum(1 for c in letters if c in vowels) / len(letters)

    # less aggressive
    if vowel_ratio < 0.15:
        return True

    # repeated letters spam
    if re.search(r"(.)\1{3,}", name):
        return True

    return False

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
@limiter.limit("3 per hour")
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


    # =========================
    # FULLNAME VALIDATION (CLEAN FLOW)
    # =========================

    # 1. CLEAN INPUT
    fullname = re.sub(r"\s+", " ", fullname).strip()

    # 2. FORMAT NAME
    fullname = format_fullname(fullname)

    # 3. LENGTH CHECK
    if len(fullname) > 50:
        return render_template('register.html',
            fullname_error="Full name is too long",
            form_data=data
        )

    # 4. MINIMUM WORDS
    words = fullname.split()
    if len(words) < 2:
        return render_template('register.html',
            fullname_error="Please enter full name (first and last name)",
            form_data=data
        )

    # prepare lowercase once
    words_lower = [w.lower() for w in words]

    # 5. GIBBERISH CHECK
    if is_gibberish(fullname.lower()):
        return render_template('register.html',
            fullname_error="Please enter a real name",
            form_data=data
        )

    # 6. DUPLICATE WORDS CHECK

    # all same word (juan juan)
    if len(set(words_lower)) == 1:
        return render_template('register.html',
            fullname_error="Invalid full name",
            form_data=data
        )

    # repeated words (juan dela dela cruz)
    if len(words_lower) != len(set(words_lower)):
        return render_template('register.html',
            fullname_error="Repeated names are not allowed",
            form_data=data
        )

    # 7. REGEX VALIDATION
    fullname_pattern = r"^[A-Za-z]+(?:[ '-][A-Za-z]+)*$"
    if not re.match(fullname_pattern, fullname):
        return render_template('register.html',
            fullname_error="Enter a valid full name (e.g., Juan Dela Cruz)",
            form_data=data
        )

    # 8. DATABASE UNIQUENESS
    if User.query.filter(func.lower(User.fullname) == fullname.lower()).first():
        return render_template('register.html',
            fullname_error="Name already registered",
            form_data=data
        )

    
    # STRONG PASSWORD (uppercase, lowercase, number, special char)
    strong_password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$'
    if not re.match(strong_password_pattern, password):
        return render_template('register.html',
            
            password_error="Password must be 8+ chars with uppercase, lowercase, and number",
            form_data=data
        )
    
    if len(password) > 128:
        return render_template('register.html',
            password_error="Password too long",
            form_data=data
        )

    # ROLE
    if not role:
        return render_template('register.html', role_error="Please select a role", form_data=data)

    # USERNAME FORMAT
    if not re.match(r"^[a-z][a-z0-9_]{4,14}$", username):
        return render_template('register.html',
            username_error="5–15 chars, start with letter, no spaces",
            form_data=data
        )

    # 🔥 NEW: CHECK IF USERNAME RELATES TO FULLNAME
    parts = fullname.lower().split()

    first = parts[0]
    last = parts[-1]

    if not (
        first in username or
        last in username or
        (first + last) in username or
        (first[0] + last) in username
    ):
        return render_template('register.html',
            username_error="Username must be related to your name (e.g., juandelacruz)",
            form_data=data
        )

    # USERNAME EXISTS
    if User.query.filter(func.lower(User.username) == username).first():
        return render_template('register.html',
            username_error="Username already exists",
            form_data=data
        )

    # CONTACT VALIDATION
    contact = resident_contact if role == "Resident" else worker_contact
    contact = re.sub(r"[^\d+]", "", contact)

    if not contact:
        return render_template('register.html',
            contact_error="Contact number is required",
            form_data=data
        )

    # NORMALIZE
    if contact.startswith("+639"):
        contact = "0" + contact[3:]

    contact = re.sub(r"\D", "", contact)

    # FORMAT CHECK
    if not re.match(r"^09\d{9}$", contact):
        return render_template('register.html',
            contact_error="Invalid PH contact number",
            form_data=data
        )

    # REPEATING DIGITS
    if re.search(r"(\d)\1{6,}", contact):
        return render_template('register.html',
            contact_error="Invalid contact number",
            form_data=data
        )

    # SEQUENTIAL DIGITS
    if contact[2:] in "0123456789" or contact[2:] in "9876543210":
        return render_template('register.html',
            contact_error="Invalid contact number",
            form_data=data
        )

    # UNIQUENESS
    if Resident.query.filter_by(contact=contact).first() or HealthWorker.query.filter_by(contact=contact).first():
        return render_template('register.html',
            contact_error="Contact already registered",
            form_data=data
        )

    # HEALTH WORKER VALIDATION
    if role == "HealthWorker":
        worker_code = data.get('worker_code', '').strip()
        expected_code = os.getenv("HEALTH_WORKER_CODE", "").strip()
        
        if not worker_code:
            return render_template('register.html', 
                worker_code_error="Health Worker Code is required", 
                form_data=data
            )
        
        if worker_code != expected_code:
            return render_template('register.html', 
                worker_code_error="Invalid Health Worker Code. Please check and try again.", 
                form_data=data
            )

        valid_positions = ["Nurse", "Midwife", "Barangay Health Worker"]
        position = data.get('position', '').strip()

        if not position or position not in valid_positions:
            return render_template('register.html', 
                position_error="Please select a valid position", 
                form_data=data
            )

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
    username = request.form.get('username', '').strip()
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

    user = User.query.filter_by(username=username).first()
    dummy_hash = generate_password_hash("dummy123")

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
