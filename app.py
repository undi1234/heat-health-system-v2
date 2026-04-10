from flask import Flask, render_template, request, redirect, url_for, session, Response, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
import requests
import os
from dotenv import load_dotenv
load_dotenv()  # 🔥 this loads the .env file
from apscheduler.schedulers.background import BackgroundScheduler



API_KEY = os.getenv("OPENWEATHER_API_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret")

# =========================
# DATABASE CONFIG
# =========================
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@localhost/{os.getenv('DB_NAME')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =========================
# DATABASE MODELS
# =========================

class User(db.Model):
    __tablename__ = 'user'   # ✅ ADD THIS

    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))


class Resident(db.Model):
    __tablename__ = 'resident'   # ✅ ADD THIS

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    gender = db.Column(db.String(10))
    address = db.Column(db.String(100))
    contact = db.Column(db.String(20))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class HealthWorker(db.Model):
    __tablename__ = 'health_worker'   # ✅ ADD THIS

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    position = db.Column(db.String(50))
    contact = db.Column(db.String(20))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Temperature(db.Model):
    __tablename__ = 'temperature'   # ✅ ADD THIS

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Float)
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    barangay = db.Column(db.String(50))


class HeatIndex(db.Model):
    __tablename__ = 'heat_index'   # ✅ ADD THIS

    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float)
    heat_index = db.Column(db.Float)
    status = db.Column(db.String(20))
    date = db.Column(db.String(20))

    temperature_id = db.Column(db.Integer, db.ForeignKey('temperature.id'))


class Illness(db.Model):
    __tablename__ = 'illness'   # ✅ ADD THIS

    id = db.Column(db.Integer, primary_key=True)
    symptoms = db.Column(db.String(200))
    status = db.Column(db.String(50))
    date = db.Column(db.String(20))

    resident_id = db.Column(db.Integer, db.ForeignKey('resident.id'))
    healthworker_id = db.Column(db.Integer, db.ForeignKey('health_worker.id'))

    resident = db.relationship('Resident')
    healthworker = db.relationship('HealthWorker')


# =========================
# ROUTES
# =========================

# HOME (LOGIN PAGE)
@app.route('/')
def home():
    return render_template('index.html')


# REGISTER PAGE
@app.route('/register_page')
def register_page():
    return render_template('register.html')


# =========================
# REGISTER
# =========================
@app.route('/register', methods=['POST'])
def register():
    data = request.form

    fullname = data['fullname']
    username = data['username']
    password = data['password']

    # ❌ WEAK PASSWORD CHECK
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

    role = data['role']

    # ❌ ROLE NOT SELECTED
    if not role:
        return render_template('register.html',
            role_error="Please select a role",
            form_data=data
        )

    # ❌ FULLNAME EXISTS
    if User.query.filter_by(fullname=fullname).first():
        return render_template('register.html',
            fullname_error="Full name already registered",
            form_data=data
        )

    # ❌ USERNAME EXISTS
    if User.query.filter_by(username=username).first():
        return render_template('register.html',
            username_error="Username already exists",
            form_data=data
        )

    # 🔐 ✅ PUT VALIDATION HERE (IMPORTANT)
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

    # ✅ NOW CREATE USER (ONLY AFTER ALL VALIDATIONS)
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

    flash("Account created successfully! You can now login 🎉", "success")
    return redirect('/')


# =========================
# LOGIN
# =========================
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    user = User.query.filter_by(username=username).first()

    # ❌ USER NOT FOUND
    if not user:
        return render_template(
            'index.html',
            username_error="Invalid username",
            username=username
        )

    # ❌ WRONG PASSWORD
    if not check_password_hash(user.password, password):
        return render_template(
            'index.html',
            password_error="Incorrect password",
            username=username
        )

    # ✅ SUCCESS LOGIN
    session['user'] = user.username
    session['role'] = user.role
    session['user_id'] = user.id

    flash("Login successful!", "success")

    if user.role == "Resident":
        return redirect('/resident_dashboard')
    else:
        return redirect('/health_worker_dashboard')
    
# =========================
# AUTOMATIC INJECT USERNAME/ROLE
# =========================
@app.context_processor
def inject_user():
    user = None

    if 'user' in session:
        user = User.query.filter_by(username=session['user']).first()

    return dict(
        username=session.get('user'),
        role=session.get('role'),
        fullname=user.fullname if user else None   # ✅ ADD THIS
    )


# =========================
# ACCOUNT INFORMATION
# =========================
@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'user' not in session:
        return redirect('/')

    user = User.query.filter_by(username=session['user']).first()

    # 🔵 RESIDENT
    if user.role == "Resident":
        profile = Resident.query.filter_by(user_id=user.id).first()

        if not profile:
            profile = Resident(
                name=user.fullname,
                gender="N/A",
                address="N/A",
                contact="N/A",
                user_id=user.id
            )
            db.session.add(profile)
            db.session.commit()

    # 🟢 HEALTH WORKER
    else:
        profile = HealthWorker.query.filter_by(user_id=user.id).first()

        if not profile:
            profile = HealthWorker(
                name=user.fullname,
                position="N/A",
                contact="N/A",
                user_id=user.id
            )
            db.session.add(profile)
            db.session.commit()

    # ✅ UPDATE INFO
    if request.method == 'POST':

        if not profile:
            flash("Profile not found!", "error")
            return redirect(url_for('account'))

        user.fullname = request.form['fullname']

        if user.role == "Resident":
            profile.address = request.form['address']
            profile.contact = request.form['contact']
        else:
            profile.position = request.form['position']
            profile.contact = request.form['contact']

        db.session.commit()
        flash("Profile updated successfully!", "success")

        return redirect(url_for('account'))

    return render_template('account.html', user=user, profile=profile)


# =========================
# CHANGE PASSWORD
# =========================
@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user' not in session:
        return redirect('/')

    user = User.query.filter_by(id=session['user_id']).first()

    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    # ✅ Check current password
    if not check_password_hash(user.password, current_password):
        flash("Current password is incorrect!", "error")
        return redirect(request.referrer)

    # ❌ NEW: PASSWORD LENGTH VALIDATION
    if len(new_password) < 8:
        flash("Password must be at least 8 characters!", "error")
        return redirect(request.referrer)

    # ❌ NEW: LETTER + NUMBER CHECK
    if new_password.isdigit() or new_password.isalpha():
        flash("Password must contain both letters and numbers!", "error")
        return redirect(request.referrer)

    # ✅ Check if new passwords match
    if new_password != confirm_password:
        flash("New passwords do not match!", "error")
        return redirect(request.referrer)

    # ✅ Update password
    user.password = generate_password_hash(new_password)
    db.session.commit()

    flash("Password updated successfully!", "success")
    return redirect(request.referrer)

# =========================
# RESIDENT DASHBOARD
# =========================
@app.route('/resident_dashboard')
def resident_dashboard():
    if 'user' not in session or session.get('role') != "Resident":
        return redirect('/')

    user = User.query.filter_by(id=session['user_id']).first()

    # ✅ CHECK USER
    if not user:
        return redirect('/')

    resident = Resident.query.filter_by(user_id=user.id).first()

    # ✅ FIX: CHECK RESIDENT
    if not resident:
        flash("No resident profile found.", "error")
        return redirect('/')

    # 🔥 NOW SAFE
    barangay = resident.address

    # 🔥 FILTER BY BARANGAY
    latest_temp = Temperature.query.filter_by(
        barangay=barangay
    ).order_by(Temperature.id.desc()).first()

    if latest_temp:
        latest = HeatIndex.query.filter_by(
            temperature_id=latest_temp.id
        ).first()
    else:
        latest = None

    if latest:
        temperature = latest.temperature
        heat_index = latest.heat_index
    else:
        temperature = 0
        heat_index = 0

    level_text, level_class, level_icon = get_heat_level(heat_index)
    reminders = get_safety_reminders(level_text)

    return render_template(
        'resident_dashboard.html',
        temperature=temperature,
        heat_index=heat_index,
        level_text=level_text,
        level_class=level_class,
        level_icon=level_icon,
        reminders=reminders,
        barangay=barangay
    )

# =========================
# SAFETY ALERTS
# =========================
@app.route('/safety_alerts')
def safety_alerts():
    if 'user' not in session or session.get('role') != "Resident":
        return redirect('/')

    user = User.query.filter_by(id=session['user_id']).first()
    resident = Resident.query.filter_by(user_id=user.id).first()
    current_time = datetime.now().strftime("%B %d, %Y | %I:%M:%S %p")

    # 🔥 GET LATEST TEMP BASED ON BARANGAY
    latest_temp = Temperature.query.filter_by(
        barangay=resident.address
    ).order_by(Temperature.id.desc()).first()

    if latest_temp:
        latest = HeatIndex.query.filter_by(
            temperature_id=latest_temp.id
        ).first()
    else:
        latest = None

    # DEFAULT
    if latest:
        heat_index = latest.heat_index
        temperature = latest.temperature
    else:
        heat_index = 0
        temperature = 0

    level_text, level_class, level_icon = get_heat_level(heat_index)
    reminders = get_safety_reminders(level_text)

    return render_template(
        'safety_alerts.html',
        heat_index=heat_index,
        temperature=temperature,
        level_text=level_text,
        level_class=level_class,
        level_icon=level_icon,
        reminders=reminders,
        barangay=resident.address,
        current_time=current_time
    )

def get_safety_reminders(level):
    if level == "SAFE":
        return [
            {"en": "Enjoy outdoor activities normally", "bi": "Pwede ra mag outdoor activities sama sa naandan"},
            {"en": "Stay hydrated throughout the day", "bi": "Padayon inom tubig tibuok adlaw"},
            {"en": "Wear light and comfortable clothing", "bi": "Magsul-ob og gaan ug komportable nga sinina"},
            {"en": "Monitor weather updates regularly", "bi": "Sige'g tan-aw sa update sa panahon"}
        ]

    elif level == "CAUTION":
        return [
            {"en": "Drink plenty of water", "bi": "Pag-inom og daghang tubig"},
            {"en": "Avoid prolonged exposure to sunlight", "bi": "Likayi ang dugay nga pagpabilin sa init sa adlaw"},
            {"en": "Wear hats or use umbrellas outdoors", "bi": "Paggamit og kalo o payong kung mogawas"},
            {"en": "Take breaks in shaded areas", "bi": "Magpahuway sa landong nga lugar"},
            {"en": "Check body for early signs of heat stress", "bi": "Bantayi ang lawas kung naay early signs sa heat stress"}
        ]

    elif level == "DANGER":
        return [
            {"en": "Limit outdoor activities as much as possible", "bi": "Limitahi ang gawas nga aktibidad kutob sa mahimo"},
            {"en": "Stay indoors during peak heat hours", "bi": "Magpabilin sa sulod sa balay sa pinakainit nga oras"},
            {"en": "Use fans or air conditioning", "bi": "Paggamit og electric fan o aircon"},
            {"en": "Drink water every 15–20 minutes", "bi": "Mag-inom og tubig kada 15–20 minutos"},
            {"en": "Watch for dizziness or fatigue symptoms", "bi": "Bantayi kung mahilo o kapoy kaayo ang lawas"}
        ]

    elif level == "EXTREME DANGER":
        return [
            {"en": "Avoid going outside unless absolutely necessary", "bi": "Ayaw gawas kung dili gyud kinahanglan"},
            {"en": "Stay in air-conditioned or cool places", "bi": "Magpabilin sa bugnaw nga lugar o naay aircon"},
            {"en": "Drink water frequently even if not thirsty", "bi": "Sige'g inom tubig bisan dili uhaw"},
            {"en": "Check elderly and children regularly", "bi": "Permi bantayi ang tigulang ug mga bata"},
            {"en": "Seek medical help if symptoms appear", "bi": "Pangayo og tabang medikal kung naay sintomas"}
        ]

    else:
        return [{"en": "No reminders available", "bi": "Walay available nga pahimangno"}]
    

# =========================
# REPORT ILLNESS
# =========================
@app.route('/report_illness', methods=['GET', 'POST'])
def report_illness():
    if 'user' not in session or session.get('role') != "Resident":
        return redirect('/')

    user = User.query.filter_by(username=session['user']).first()

    if request.method == 'POST':
        data = request.form

        # 🔥 GET OR CREATE RESIDENT
        resident = Resident.query.filter_by(user_id=user.id).first()

        if not resident:
            resident = Resident(
                name=user.fullname,
                gender="N/A",
                address="N/A",
                contact="N/A",
                user_id=user.id
            )
            db.session.add(resident)
            db.session.commit()

        # ✅ NOW SAFE
        illness = Illness(
            symptoms=data['symptoms'],
            status="Reported",
            date=data['date'],
            resident_id=resident.id
        )

        db.session.add(illness)
        db.session.commit()

        flash("Illness reported successfully!", "success")
        return redirect('/case_status')

    return render_template('report_illness.html', fullname=user.fullname)


# =========================
# MY CASE STATUS
# =========================
@app.route('/case_status')
def case_status():
    if 'user' not in session or session.get('role') != "Resident":
        return redirect('/')
    user_id = session.get('user_id')  # get logged-in user ID
    
    resident = Resident.query.filter_by(user_id=user_id).first()

    if resident is None:
        return render_template('case_status.html', cases=[])

    cases = Illness.query.filter_by(resident_id=resident.id).all()


    return render_template('case_status.html', cases=cases)


# =========================
# RESIDENT CRUD
# =========================
@app.route('/residents')
def residents():
    data = Resident.query.all()
    return jsonify([{
        "id": r.id,
        "name": r.name,
        "gender": r.gender,
        "address": r.address,
        "contact": r.contact
    } for r in data])

# =========================
# ADD RESIDENT 
# =========================
@app.route('/add_resident', methods=['POST'])
def add_resident():
    data = request.form

    r = Resident(
        name=data['name'],
        gender=data['gender'],
        address=data['address'],
        contact=data['contact']
    )

    db.session.add(r)
    db.session.commit()

    flash("Resident added successfully!", "success")
    return redirect(url_for('residents_management'))


# =========================
# DELETE RESIDENT 
# =========================
@app.route('/delete_resident/<int:id>', methods=['POST'])
def delete_resident(id):
    r = Resident.query.get_or_404(id)

    try:
        # ✅ DELETE LINKED USER FIRST
        if r.user_id:
            user = User.query.get(r.user_id)
            if user:
                db.session.delete(user)

        # ✅ DELETE RESIDENT
        db.session.delete(r)
        db.session.commit()

        flash("Resident and account deleted successfully!", "success")

    except IntegrityError:
        db.session.rollback()

        flash(
            "Cannot delete this resident because it is used in illness records.",
            "error"
        )

    return redirect(url_for('residents_management'))

# =========================
# UPDATE RESIDENT INFO
# =========================
@app.route('/update_resident/<int:id>', methods=['POST'])
def update_resident(id):
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    resident = Resident.query.get_or_404(id)

    resident.address = request.form['address']
    resident.contact = request.form['contact']

    db.session.commit()

    flash("Resident updated successfully!", "success")
    return redirect(url_for('residents_management'))


# =========================
# HEALTH WORKER DASHBOARD
# =========================
@app.route('/health_worker_dashboard')
def health_worker_dashboard():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    total_cases = Illness.query.count()
    critical_alerts = Illness.query.filter(
        Illness.status.in_(["Reported", "Under Treatment"])
    ).count()

    return render_template(
        'health_worker_dashboard.html',
        total_cases=total_cases,
        critical_alerts=critical_alerts)


# =========================
# RESIDENTS MANAGEMENT
# =========================
@app.route('/residents_management')
def residents_management():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    residents = Resident.query.order_by(Resident.name.asc()).all()   # ✅ GET ALL RESIDENTS A → Z automatically sorting

    return render_template(
        'residents_management.html',
        residents=residents)           # ✅ SEND TO HTML


# =========================
# HEALTH WORKERS
# =========================
@app.route('/health_workers')
def health_workers():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    workers = HealthWorker.query.order_by(HealthWorker.name.asc()).all()

    # 🔥 ADD CUSTOM DISPLAY ID
    workers_with_code = []
    for i, w in enumerate(workers, start=1):
        workers_with_code.append({
            "code": f"W{i:03d}",   # W001, W002
            "id": w.id,
            "name": w.name,
            "position": w.position,
            "contact": w.contact
        })

    return render_template(
        'health_workers.html',
        workers=workers_with_code
    )      


# =========================
# ADD HEALTH WORKERS
# =========================
@app.route('/add_health_worker', methods=['POST'])
def add_health_worker():
    data = request.form

    worker = HealthWorker(
        name=data['name'],
        position=data['position'],
        contact=data['contact']
    )

    db.session.add(worker)
    db.session.commit()

    flash("Health Worker added successfully!", "success")
    return redirect(url_for('health_workers'))


# =========================
# DELETE HEALTH WORKERS
# =========================
@app.route('/delete_health_worker/<int:id>', methods=['POST'])
def delete_health_worker(id):
    worker = HealthWorker.query.get_or_404(id)

    try:
        # ✅ DELETE LINKED USER
        if hasattr(worker, 'user_id') and worker.user_id:
            user = User.query.get(worker.user_id)
            if user:
                db.session.delete(user)

        # ✅ DELETE WORKER
        db.session.delete(worker)
        db.session.commit()

        flash("Health worker and account deleted successfully!", "success")

    except IntegrityError:
        db.session.rollback()

        flash(
            "Cannot delete this health worker because they are assigned to illness records.",
            "error"
        )

    return redirect(url_for('health_workers'))

# =========================
# UPDATE HEALTH WORKERS
# =========================
@app.route('/update_worker/<int:id>', methods=['POST'])
def update_worker(id):
    worker = HealthWorker.query.get_or_404(id)

    worker.position = request.form['position']
    worker.contact = request.form['contact']

    db.session.commit()

    flash("Worker updated!", "success")
    return redirect(url_for('health_workers'))


# =========================
# API FOR HEALTH WORKERS
# =========================
@app.route('/api/healthworkers')
def api_healthworkers():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return jsonify({"error": "Unauthorized"}), 403
    
    data = HealthWorker.query.all()
    return jsonify([{
        "id": w.id,
        "name": w.name,
        "position": w.position,
        "contact": w.contact
    } for w in data])


# =========================
# TEMPERATURE RECORDS
# =========================
@app.route('/temperature_records')
def temperature_records():
    data = Temperature.query.order_by(Temperature.id.desc()).all()
    current_time = datetime.now().strftime("%I:%M:%S %p")
    barangays = db.session.query(Temperature.barangay).distinct().all()

    return render_template(
        'temperature_records.html',
        temperatures=data,
        current_time=current_time,
        barangays=barangays,
        username=session.get('user'),
        role=session.get('role')
    )
    

def get_online_temperature(city):
    api_key = os.getenv("OPENWEATHER_API_KEY")
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

    try:
        response = requests.get(url)

        # ✅ DEBUG: Print raw response
        print("RAW RESPONSE:", response.text)

        data = response.json()

        # ✅ Check if API returned error
        if response.status_code != 200:
            print("API ERROR:", data)
            return None

        return data['main']['temp']

    except Exception as e:
        print("Request failed:", e)
        return None
    
# =========================
# VIEW TEMPERATURE RECORDS
# =========================
@app.route('/view_temperature/<int:id>')
def view_temperature(id):
    record = Temperature.query.get_or_404(id)
    return render_template('view_temperature.html', record=record)

# =========================
# API FOR TEMPERATURE
# =========================
@app.route('/api/temperature')
def api_temperature():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return jsonify({"error": "Unauthorized"}), 403

    data = Temperature.query.order_by(Temperature.id.desc()).all()
    return jsonify([{
        "value": t.value,
        "date": t.date,
        "time": t.time
    } for t in data])


# =========================
# ADD TEMPERATURE
# =========================
@app.route('/add_temperature', methods=['POST'])
def add_temperature():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return jsonify({"error": "Unauthorized"}), 403
    city = request.form['city']

    # ✅ GET FROM FORM (SELECTED BARANGAY)
    barangay = request.form.get('barangay')

    if not barangay:
        barangay = "Unknown"
        
    # 🌐 GET ONLINE TEMP
    temp_value = get_online_temperature(city)

    if temp_value is None:
        flash("Failed to get temperature. Check city name.", "error")
        return redirect(url_for('temperature_records'))

    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%I:%M:%S %p")

    new_temp = Temperature(
        value=temp_value,
        date=current_date,
        time=current_time,
        barangay=barangay   # ✅ AUTO
    )
    db.session.add(new_temp)
    db.session.flush()

    heat_index_value, status = compute_heat_index(temp_value)

    new_heat = HeatIndex(
        temperature=temp_value,
        heat_index=round(heat_index_value, 2),
        status=status,
        date=current_date,
        temperature_id=new_temp.id
    )

    db.session.add(new_heat)
    db.session.commit()

    flash(f"Temperature saved for {barangay}!", "success")

    return redirect(url_for('temperature_records'))


# =========================
# AUTO FETCH TEMPERATURE
# =========================
def auto_fetch_temperature():
    with app.app_context():

        city = "Clarin,Bohol,PH"
        temp_value = get_online_temperature(city)

        if temp_value is None:
            print("Auto fetch failed")
            return

        barangays = ["Danahao"]

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%I:%M:%S %p")

        for brgy in barangays:
            new_temp = Temperature(
                value=temp_value,
                date=current_date,
                time=current_time,
                barangay=brgy   # 🔥 KEY FIX
            )
            db.session.add(new_temp)
            db.session.flush()

            heat_index_value, status = compute_heat_index(temp_value)

            new_heat = HeatIndex(
                temperature=temp_value,
                heat_index=round(heat_index_value, 2),
                status=status,
                date=current_date,
                temperature_id=new_temp.id
            )

            db.session.add(new_heat)

        db.session.commit()

        print("✅ Auto temperature saved for barangay")


# =========================
# SCHEDULER 
# =========================
#scheduler = BackgroundScheduler()
#job = None  # 🔥 track job

#job = scheduler.add_job(func=auto_fetch_temperature, trigger="interval", minutes=30)

#if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
#    scheduler.start()
scheduler = BackgroundScheduler()
job = None
auto_running = False  # 

# =========================
# STOP AUTO FETCH
# =========================
@app.route('/stop_auto_temp', methods=['POST'])
def stop_auto_temp():
    global job, auto_running

    if job:
        scheduler.remove_job(job.id)
        job = None

    auto_running = False
    print("⛔ Auto fetch STOPPED")

    return jsonify({"status": "stopped"})


# =========================
# START AUTO FETCH
# =========================
@app.route('/start_auto_temp', methods=['POST'])
def start_auto_temp():
    global job, auto_running

    if not auto_running:
        if not scheduler.running:
            scheduler.start()

        job = scheduler.add_job(
            func=auto_fetch_temperature,
            trigger="interval",
            minutes=30
        )

        auto_running = True
        print("▶ Auto fetch STARTED")

    return jsonify({"status": "started"})

    
# =========================
# DELETE TEMPERATURE
# =========================
@app.route('/delete_temperature/<int:id>', methods=['POST'])
def delete_temperature(id):
    temp = Temperature.query.get_or_404(id)

    # 🔥 DELETE RELATED HEAT INDEX FIRST
    HeatIndex.query.filter_by(temperature_id=temp.id).delete()

    db.session.delete(temp)
    db.session.commit()

    flash("Temperature record deleted!", "success")
    return redirect(url_for('temperature_records'))

# =========================
# API FOR SENSOR
# =========================
@app.route('/api/sensor', methods=['POST'])
def sensor_data():
    data = request.json

    temp_value = float(data['temperature'])
    date = data['date']
    time = data['time']

    # SAVE TEMP
    new_temp = Temperature(
        value=temp_value,
        date=date,
        time=time,
        barangay="Sensor Area"
    )
    db.session.add(new_temp)
    db.session.flush()

    # COMPUTE HEAT INDEX
    heat_index_value, status = compute_heat_index(temp_value)

    # SAVE HEAT INDEX
    new_heat = HeatIndex(
        temperature=temp_value,
        heat_index=round(heat_index_value, 2),
        status=status,
        date=date,
        temperature_id=new_temp.id
    )

    db.session.add(new_heat)
    db.session.commit()

    return {"message": "Sensor data saved"}


# =========================
# HEAT INDEX RECORDS
# =========================
@app.route('/heat_index_records')
def heat_index_records():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')
    
    data = HeatIndex.query.all() or []
    return render_template('heat_index_records.html', data=data)


# =========================
# API FOR HEAT INDEX
# =========================
@app.route('/api/heat_index')
def api_heat_index():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return jsonify({"error": "Unauthorized"}), 403
    
    data = HeatIndex.query.all()
    return jsonify([{
        "temperature": h.temperature,
        "heat_index": h.heat_index,
        "status": h.status,
        "date": h.date
    } for h in data])

# =========================
# HEAT INDEX FORMULA
# =========================
def compute_heat_index(temp, humidity=60):
    hi = temp + (0.33 * humidity/100 * temp) - 0.7

    # STATUS CATEGORY
    if hi < 27:
        status = "Normal"
    elif hi < 32:
        status = "Caution"
    elif hi < 41:
        status = "Extreme Caution"
    elif hi < 54:
        status = "Danger"
    else:
        status = "Extreme Danger"

    return hi, status

def get_heat_level(heat_index):
    if heat_index <= 0:
        return "NORMAL", "level-normal", "🟢"

    elif heat_index < 27:
        return "NORMAL", "level-normal", "🟢"

    elif heat_index < 32:
        return "CAUTION", "level-caution", "⚠️"

    elif heat_index < 41:
        return "EXTREME CAUTION", "level-extreme-caution", "🌡️"

    elif heat_index < 54:
        return "DANGER", "level-danger", "🔥"

    else:
        return "EXTREME DANGER", "level-extreme-danger", "🚨"


# =========================
# GENERATE HEAT REPOTS
# =========================
@app.route('/heat-reports')
def heat_reports():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    records = HeatIndex.query.all()

    total_records = len(records)

    avg_temp = db.session.query(func.avg(HeatIndex.temperature)).scalar() or 0
    avg_heat_index = db.session.query(func.avg(HeatIndex.heat_index)).scalar() or 0

    normal = HeatIndex.query.filter_by(status="Normal").count()
    caution = HeatIndex.query.filter_by(status="Caution").count()
    extreme_caution = HeatIndex.query.filter_by(status="Extreme Caution").count()
    danger = HeatIndex.query.filter_by(status="Danger").count()
    extreme_danger = HeatIndex.query.filter_by(status="Extreme Danger").count()

    return render_template(
        'heat_reports.html',
        total_records=total_records,
        avg_temp=round(avg_temp, 2),
        avg_heat_index=round(avg_heat_index, 2),
        normal=normal,
        caution=caution,
        extreme_caution=extreme_caution,
        danger=danger,
        extreme_danger=extreme_danger
    )

# =========================
# ILLNESS RECORDS
# =========================
@app.route('/illness_records')
def illness_records():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    records = Illness.query.order_by(Illness.id.desc()).all()
    workers = HealthWorker.query.all()   # ✅ ADD THIS

    return render_template(
        'illness_records.html',
        records=records,
        workers=workers   # ✅ PASS HERE
    )


# =========================
# API FOR ILLNESS
# =========================
@app.route('/api/illness')
def api_illness():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return jsonify({"error": "Unauthorized"}), 403

    data = Illness.query.all()

    return jsonify([{
        "resident": i.resident.name if i.resident else None,
        "symptoms": i.symptoms,
        "status": i.status,
        "date": i.date,
        "handled_by": i.healthworker.name if i.healthworker else None
    } for i in data])


# =========================
# REPORTS
# =========================
@app.route('/reports')
def reports():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    # =========================
    # 📊 SUMMARY CARDS
    # =========================
    total_cases = Illness.query.count()

    active_cases = Illness.query.filter(
        Illness.status.in_(["Reported", "Under Treatment"])
    ).count()

    recovered_cases = Illness.query.filter_by(status="Recovered").count()

    # =========================
    # 🌡️ CRITICAL DAYS (EXTREME DANGER)
    # =========================
    critical_days = HeatIndex.query.filter_by(status="Extreme Danger").count()

    # =========================
    # 📈 HEAT INDEX TRENDS (LATEST 5)
    # =========================
    heat_trends = HeatIndex.query.order_by(HeatIndex.id.desc()).limit(5).all()

    # =========================
    # 🏥 RECENT ILLNESS CASES (LATEST 5)
    # =========================
    recent_cases = Illness.query.order_by(Illness.id.desc()).limit(5).all()

    return render_template(
        'reports.html',
        total_cases=total_cases,
        critical_days=critical_days,
        active_cases=active_cases,
        recovered_cases=recovered_cases,
        heat_trends=heat_trends,
        recent_cases=recent_cases
    )

def get_heat_data(filter_type=None):

    query = HeatIndex.query
    today = datetime.today()

    # 🔥 FILTER
    if filter_type == "weekly":
        start_date = today - timedelta(days=7)
        query = query.filter(func.date(HeatIndex.date) >= start_date.date())

    elif filter_type == "monthly":
        start_date = today.replace(day=1)
        query = query.filter(func.date(HeatIndex.date) >= start_date.date())

    elif filter_type == "annual":
        start_date = today.replace(month=1, day=1)
        query = query.filter(func.date(HeatIndex.date) >= start_date.date())

    # ✅ DATA
    total_records = query.count()

    avg_temp = query.with_entities(func.avg(HeatIndex.temperature)).scalar() or 0
    avg_heat_index = query.with_entities(func.avg(HeatIndex.heat_index)).scalar() or 0

    normal = query.filter_by(status='Normal').count()
    caution = query.filter_by(status='Caution').count()
    extreme_caution = query.filter_by(status='Extreme Caution').count()
    danger = query.filter_by(status='Danger').count()
    extreme_danger = query.filter_by(status='Extreme Danger').count()

    return dict(
        total_records=total_records,
        avg_temp=round(avg_temp, 2),
        avg_heat_index=round(avg_heat_index, 2),
        normal=normal,
        caution=caution,
        extreme_caution=extreme_caution,
        danger=danger,
        extreme_danger=extreme_danger
    )


@app.route('/report/<type>')
def report(type):
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    today = datetime.today()

    # 🔥 FORMAT DATES
    if type == "weekly":
        start_date = today - timedelta(days=7)
        subtitle = f"{start_date.strftime('%B %d')} - {today.strftime('%B %d, %Y')}"
        title = "Weekly Heat Report"

    elif type == "monthly":
        subtitle = today.strftime("%B %Y")   # e.g. April 2026
        title = "Monthly Heat Report"

    elif type == "annual":
        subtitle = today.strftime("Year %Y")  # e.g. Year 2026
        title = "Annual Heat Report"

    else:
        title = "Heat Report"
        subtitle = ""

    # 🔥 EXISTING SUMMARY DATA
    total_cases = Illness.query.count()

    active_cases = Illness.query.filter(
        Illness.status.in_(["Reported", "Under Treatment"])
    ).count()

    recovered_cases = Illness.query.filter_by(status="Recovered").count()

    critical_days = HeatIndex.query.filter_by(status="Extreme Danger").count()

    heat_trends = HeatIndex.query.order_by(HeatIndex.id.desc()).limit(5).all()
    recent_cases = Illness.query.order_by(Illness.id.desc()).limit(5).all()

    return render_template(
        "heat_summary_report.html",
        title=title,
        subtitle=subtitle,
        filename=f"{type}_report.png",

        # 🔥 HEAT DATA
        **get_heat_data(type),

        # 🔥 DASHBOARD DATA
        total_cases=total_cases,
        active_cases=active_cases,
        recovered_cases=recovered_cases,
        critical_days=critical_days,
        heat_trends=heat_trends,
        recent_cases=recent_cases
    )

# =========================
# ADD CASE (HEALTH WORKER)
# =========================
@app.route('/add_case', methods=['POST'])
def add_case():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    data = request.form

    resident = Resident.query.filter_by(name=data['resident_name']).first()

    if not resident:
        flash("Resident not found!", "error")
        return redirect(url_for('illness_records'))

    worker = HealthWorker.query.filter_by(user_id=session['user_id']).first()

    case = Illness(
        symptoms=data['symptoms'],
        status=data['status'],
        date=data['date'],
        resident_id=resident.id,
        healthworker_id=worker.id
    )

    db.session.add(case)
    db.session.commit()

    flash("Case added successfully!", "success")
    return redirect(url_for('illness_records'))


# =========================
# UPDATE CASE STATUS
# =========================
@app.route('/edit_case/<int:id>', methods=['POST'])
def edit_case(id):
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    case = Illness.query.get_or_404(id)

    # ✅ update fields
    case.symptoms = request.form['symptoms']
    case.status = request.form['status']

    # 🔥 GET SELECTED WORKER
    worker_id = request.form.get('handled_by')

    if worker_id:
        worker = db.session.get(HealthWorker, worker_id)
        if worker_id:
            case.healthworker_id = int(worker_id)

    db.session.commit()

    flash("Case updated successfully!", "success")
    return redirect(url_for('illness_records'))


# =========================
# DELETE CASE
# =========================
@app.route('/delete_case/<int:id>', methods=['POST'])
def delete_case(id):
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    case = Illness.query.get_or_404(id)

    db.session.delete(case)
    db.session.commit()
    flash("Case deleted!", "success")

    return redirect(url_for('illness_records'))

# =========================
# USERS
# =========================
@app.route('/users')
def users():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    all_users = User.query.all()

    return render_template('users.html', users=all_users,
                        username=session.get('user'),
                        role=session.get('role'))


# =========================
# DELETE USERS
# =========================
@app.route('/delete_user/<int:id>', methods=['POST'])
def delete_user(id):
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    user = User.query.get_or_404(id)

    # ❌ prevent self delete
    if user.username == session['user']:
        flash("You cannot delete your own account!", "error")
        return redirect(url_for('users'))

    try:
        # 🔥 DELETE RELATED RESIDENT
        resident = Resident.query.filter_by(user_id=user.id).first()
        if resident:
            db.session.delete(resident)

        # 🔥 DELETE RELATED HEALTH WORKER
        worker = HealthWorker.query.filter_by(user_id=user.id).first()
        if worker:
            db.session.delete(worker)

        # 🔥 DELETE USER
        db.session.delete(user)
        db.session.commit()

        flash("User deleted successfully!", "success")

    except IntegrityError:
        db.session.rollback()

        flash(
            "Cannot delete this user because the resident is still used in illness records. "
            "Deleting this may remove important medical history.",
            "error"
        )

    return redirect(url_for('users'))


# =========================
# LOGOUT
# =========================
@app.before_request
def require_login():
    allowed_routes = ['home', 'login', 'register', 'register_page', 'static']

    if request.endpoint not in allowed_routes and 'user' not in session:
        return redirect('/')
        
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect('/')

# =========================
# RUN APP
# =========================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)