from flask import Flask, render_template, request, redirect, url_for, session, Response, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import time
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
import requests
import os
import re
from dotenv import load_dotenv
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler

# =========================
# LOAD ENV (Lazy - only load once)
# =========================
_env_loaded = False
def _ensure_env_loaded():
    global _env_loaded
    if not _env_loaded:
        load_dotenv()
        _env_loaded = True

# =========================
# SECURITY
# =========================
from extensions import csrf
from extensions import limiter

# =========================
# IMPORT MODELS & DB
# =========================
from models import db, User, Resident, HealthWorker, Temperature, HeatIndex, Illness

# =========================
# IMPORT BLUEPRINTS
# =========================
from routes.auth import auth_bp
from routes.resident import resident_bp
from utils import compute_heat_index, get_heat_level
from routes.healthworker import healthworker_bp
from markupsafe import escape

# =========================
# APP INIT
# =========================
app = Flask(__name__)
csrf.init_app(app)

# Load configuration from environment
_ensure_env_loaded()
from config import DevelopmentConfig, ProductionConfig
app.config.from_object(
    ProductionConfig if os.getenv("FLASK_ENV") == "production" else DevelopmentConfig
)

# Initialize extensions
limiter.init_app(app)
db.init_app(app)
migrate = Migrate(app, db)

# =========================
# DEFERRED DATABASE INITIALIZATION
# =========================
_db_initialized = False

def init_db():
    """Initialize database tables (called on first request or explicitly)"""
    global _db_initialized
    if _db_initialized:
        return
    
    try:
        with app.app_context():
            # Quick connection test
            with db.engine.connect() as conn:
                conn.execute(db.text("SELECT 1"))
            app.logger.info("✅ Database connected")
            
            # Create tables if they don't exist
            db.create_all()
            app.logger.info("✅ Database tables ready")
            _db_initialized = True
    except Exception as e:
        app.logger.error(f"❌ DB init error: {e}")
        _db_initialized = False

# Initialize database on first request (not module import)
@app.before_request
def before_request():
    """Ensure DB is initialized before first request"""
    if not _db_initialized:
        init_db()

# Application factory support
def create_app():
    return app

# =========================
# REGISTER BLUEPRINTS
# =========================
app.register_blueprint(auth_bp)
app.register_blueprint(resident_bp)
app.register_blueprint(healthworker_bp)

# =========================
# AUTOMATIC INJECT USERNAME/ROLE
# =========================
@app.context_processor
def inject_user():
    return dict(
        username=session.get('user'),
        role=session.get('role'),
        fullname=session.get('fullname') 
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
                position="",
                contact="N/A",
                user_id=user.id
            )
            db.session.add(profile)
            db.session.commit()

    # =========================
    # UPDATE INFO
    # =========================
    if request.method == 'POST':

        contact_error = None
        position_error = None

        # 🔹 GET + CLEAN CONTACT
        new_contact = request.form.get('contact', '').strip()
        new_contact = re.sub(r"[^\d+]", "", new_contact)

        # 🔹 NORMALIZE (+639 → 09)
        if new_contact.startswith("+639"):
            new_contact = "0" + new_contact[3:]

        new_contact = re.sub(r"\D", "", new_contact)

        # =========================
        # CONTACT VALIDATION (SAME AS REGISTER)
        # =========================

        # FORMAT
        if not re.match(r"^09\d{9}$", new_contact):
            contact_error = "Invalid PH contact number"

        # REPEATING DIGITS (e.g., 09999999999)
        elif re.search(r"(\d)\1{6,}", new_contact):
            contact_error = "Invalid contact number"

        # SEQUENTIAL (e.g., 09123456789)
        elif new_contact[2:] in "0123456789" or new_contact[2:] in "9876543210":
            contact_error = "Invalid contact number"

        else:
            # UNIQUE CHECK (exclude self)
            existing_resident = Resident.query.filter(
                Resident.contact == new_contact,
                Resident.user_id != user.id
            ).first()

            existing_worker = HealthWorker.query.filter(
                HealthWorker.contact == new_contact,
                HealthWorker.user_id != user.id
            ).first()

            if existing_resident or existing_worker:
                contact_error = "Contact already used"

        # =========================
        # POSITION VALIDATION
        # =========================
        if user.role != "Resident":
            position = request.form.get('position')
            valid_positions = ["Nurse", "Midwife", "Barangay Health Worker"]

            if position not in valid_positions:
                position_error = "Invalid position selected"

        # =========================
        # STOP IF ERROR
        # =========================
        if contact_error or position_error:
            return render_template(
                'account.html',
                user=user,
                profile=profile,
                contact_error=contact_error,
                position_error=position_error
            )

        # =========================
        # SAVE CLEAN DATA
        # =========================
        profile.contact = new_contact

        if user.role == "Resident":
            profile.address = request.form.get('address', '').strip()

        else:
            profile.position = position

        db.session.commit()

        flash("Profile updated successfully!", "success")
        return redirect(url_for('account'))

    return render_template(
        'account.html',
        user=user,
        profile=profile,
        username=user.username,
        role=user.role,
        contact_error=None,
        position_error=None
    )


# =========================
# CHECK CONTACT NUMBER IN USE
# =========================
@app.route('/check-contact')
def check_contact():
    contact = request.args.get('contact')

    if not contact:
        return {"exists": False}

    contact = re.sub(r"[^\d+]", "", contact)

    user = User.query.filter_by(username=session.get('user')).first()
    if not user:
        return jsonify({"exists": False})

    # 🔥 IMPORTANT: exclude current user’s own contact
    resident = Resident.query.filter(
        Resident.contact == contact,
        Resident.user_id != user.id
    ).first()

    worker = HealthWorker.query.filter(
        HealthWorker.contact == contact,
        HealthWorker.user_id != user.id
    ).first()

    return jsonify({"exists": bool(resident or worker)})


# =========================
# CHANGE PASSWORD
# =========================
@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user' not in session:
        return redirect('/')

    user = User.query.get(session.get('user_id'))
    if not user:
        return redirect('/')

    # 🔑 ERRORS
    current_error = None
    new_error = None
    confirm_error = None

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not current_password or not new_password or not confirm_password:
        return redirect(url_for('account'))

    # ❌ VALIDATIONS
    if not check_password_hash(user.password, current_password):
        current_error = "Incorrect current password"

    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$'
    if not re.match(pattern, new_password):
        new_error = "Weak password (8+, A-Z, a-z, number)"

    elif current_password == new_password:
        new_error = "Must be different from current password"

    if new_password != confirm_password:
        confirm_error = "Passwords do not match"

    # 🔥 IF ERROR → STAY (NO REDIRECT)
    if current_error or new_error or confirm_error:
        profile = (Resident.query.filter_by(user_id=user.id).first()
                if user.role == "Resident"
                else HealthWorker.query.filter_by(user_id=user.id).first())

        return render_template(
            'account.html',
            user=user,
            profile=profile,
            current_error=current_error,
            new_error=new_error,
            confirm_error=confirm_error
        )

    # ✅ SAVE
    user.password = generate_password_hash(new_password)
    db.session.commit()

    flash("Password updated successfully!", "success")
    return redirect(url_for('account'))

# =========================
# RESIDENT CRUD
# =========================
@app.route('/residents')
def residents():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = Resident.query.all()
    return jsonify([{
        "id": r.id,
        "name": r.name,
        "gender": r.gender,
        "address": r.address,
        "contact": r.contact
    } for r in data])


# =========================
# DELETE RESIDENT 
# =========================
@app.route('/delete_resident/<int:id>', methods=['POST'])
def delete_resident(id):
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

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

    return redirect(url_for('healthworker.residents_management'))

# =========================
# UPDATE RESIDENT INFO
# =========================
@app.route('/update_resident/<int:id>', methods=['POST'])
def update_resident(id):
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')

    resident = Resident.query.get_or_404(id)

    resident.address = request.form['address']
#    resident.contact = request.form['contact']

    db.session.commit()

    flash("Resident updated successfully!", "success")
    return redirect(url_for('healthworker.residents_management'))

# =========================
# UPDATE HEALTH WORKERS
# =========================
@app.route('/update_worker/<int:id>', methods=['POST'])
def update_worker(id):
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect('/')
    
    worker = HealthWorker.query.get_or_404(id)

    worker.position = request.form['position']
#    worker.contact = request.form['contact']

    db.session.commit()

    flash("Worker updated!", "success")
    return redirect(url_for('healthworker.health_workers'))


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
    if 'user' not in session or session.get('role') != "HealthWorker":
        return jsonify({"error": "Unauthorized"}), 403
    
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

    if not api_key:
        print("❌ API KEY NOT FOUND")
        return None

    if not city:
        return None

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        app.logger.info(data)  # ✅ changed to info

        if response.status_code != 200:
            app.logger.error(f"API Error: {data}")
            return None

        return data.get('main', {}).get('temp')  # ✅ safe access

    except Exception as e:
        print("Request failed:", e)
        return None
    
# =========================
# VIEW TEMPERATURE RECORDS
# =========================
@app.route('/view_temperature/<int:id>')
def view_temperature(id):
    if 'user' not in session or session.get('role') != "HealthWorker":
        return jsonify({"error": "Unauthorized"}), 403
    
    record = Temperature.query.get_or_404(id)

    # 🔥 COMPUTE HEAT INDEX HERE
    hi, status = compute_heat_index(record.value)

    # 🔥 GET LEVEL (color, label, icon)
    level_text, level_class, level_icon = get_heat_level(hi)

    return render_template(
        'view_temperature.html',
        record=record,
        heat_index=round(hi, 2),
        level_text=level_text,
        level_class=level_class,
        level_icon=level_icon
    )

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
        "date": t.date.isoformat() if t.date else None,
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

    current_datetime = datetime.now()

    new_temp = Temperature(
        value=temp_value,
        date=current_datetime,
        time=current_datetime.strftime("%I:%M:%S %p"),
        barangay=barangay   # ✅ AUTO
    )
    db.session.add(new_temp)
    db.session.flush()

    heat_index_value, status = compute_heat_index(temp_value)

    new_heat = HeatIndex(
        temperature=temp_value,
        heat_index=round(heat_index_value, 2),
        status=status,
        date=current_datetime,
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
        try:
            city = os.getenv("DEFAULT_CITY")
            temp_value = get_online_temperature(city)

            if temp_value is None:
                app.logger.warning(f"Failed to fetch temperature for {city}")
                return

            # Save for all barangays in Danahao
            barangays = [
                "Danahao",
                "P1 Manggahan", 
                "P2 Cocoahill",
                "P3 Maligaya", 
                "P4 Camarin",
                "P5 Riverside",
                "P6 Buntod",
                "P7 Tuog"
            ]

            current_datetime = datetime.now()

            for brgy in barangays:
                new_temp = Temperature(
                    value=temp_value,
                    date=current_datetime,
                    time=current_datetime.strftime("%I:%M:%S %p"),
                    barangay=brgy   
                )
                db.session.add(new_temp)
                db.session.flush()

                heat_index_value, status = compute_heat_index(temp_value)

                new_heat = HeatIndex(
                    temperature=temp_value,
                    heat_index=round(heat_index_value, 2),
                    status=status,
                    date=current_datetime,
                    temperature_id=new_temp.id
                )

                db.session.add(new_heat)

            db.session.commit()

            app.logger.info("✅ Auto temperature saved for all barangays")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Auto fetch failed: {e}")


# =========================
# SCHEDULER (Auto-start after first request)
# =========================
scheduler = None
job = None
auto_running = False
_scheduler_initialized = False

def init_scheduler():
    """Initialize scheduler and register auto-fetch job"""
    global scheduler, job, auto_running, _scheduler_initialized
    
    if _scheduler_initialized or scheduler is not None:
        return
    
    try:
        scheduler = BackgroundScheduler()
        scheduler.start()
        
        # Register auto-fetch to run every 1 hour
        job = scheduler.add_job(
            func=auto_fetch_temperature,
            trigger="interval",
            hours=1,
            id="auto_fetch_temp_job"
        )
        
        auto_running = True
        _scheduler_initialized = True
        app.logger.info("✅ Scheduler started - Auto temp fetch scheduled every 1 hour")
    except Exception as e:
        app.logger.error(f"❌ Scheduler init error: {e}")

# Auto-start scheduler on first request
@app.before_request
def auto_start_scheduler():
    """Start scheduler automatically on first request"""
    global scheduler
    if scheduler is None:
        init_scheduler()

# ✅ Health worker can manually control auto-fetch
@app.route('/start_auto_temp', methods=['POST'])
def start_auto_temp():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return jsonify({"error": "Unauthorized"}), 403
    
    global scheduler, auto_running
    
    # Ensure scheduler is initialized
    if scheduler is None:
        init_scheduler()
    
    if scheduler and not auto_running:
        auto_running = True
        app.logger.info("✅ Auto fetch manually enabled")
        print("🟢 Auto fetch STARTED (manual)")

    return jsonify({"status": "running"})

# =========================
# MANUAL TRIGGER AUTO FETCH
# =========================
@app.route('/manual_auto_fetch', methods=['POST'])
def manual_auto_fetch():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        auto_fetch_temperature()
        flash("Manual auto-fetch completed!", "success")
    except Exception as e:
        flash(f"Manual auto-fetch failed: {e}", "error")
    
    return redirect(url_for('temperature_records'))

# =========================
# DELETE TEMPERATURE
# =========================
@app.route('/delete_temperature/<int:id>', methods=['POST'])
def delete_temperature(id):
    if 'user' not in session or session.get('role') != "HealthWorker":
        return jsonify({"error": "Unauthorized"}), 403
    
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
@csrf.exempt
@app.route('/api/sensor', methods=['POST'])
def sensor_data():
    
    API_SECRET = os.getenv("SENSOR_SECRET")

    if request.headers.get("X-API-KEY") != API_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json

    if not data or 'temperature' not in data:
        return jsonify({"error": "Invalid data"}), 400

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
    
    data = HeatIndex.query.order_by(HeatIndex.id.desc()).all()
    return render_template('heat_index_records.html', data=data)


# =========================
# API FOR HEAT INDEX
# =========================
@app.route('/api/heat_index')
def api_heat_index():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return jsonify({"error": "Unauthorized"}), 403
    
    data = HeatIndex.query.order_by(HeatIndex.id.desc()).all()
    return jsonify([{
        "temperature": h.temperature,
        "heat_index": h.heat_index,
        "status": h.status,
        "date": h.date.isoformat() if h.date else None
    } for h in data])



# =========================
# GENERATE HEAT REPORTS
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
        "date": i.date.isoformat() if i.date else None,
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

# =========================
# GENERATE DETAILED REPORTS
# =========================
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

    # ✅ SAFE user_id check
    user_id = session.get('user_id')

    if not user_id:
        return redirect('/')

    worker_id = request.form.get('handled_by')
    worker = HealthWorker.query.get(worker_id)

    if not worker:
        flash("Health worker not found!", "error")
        return redirect(url_for('healthworker.illness_records'))

    data = request.form

    resident_id = data.get('resident_id')
    if not resident_id:
        flash("Please select a registered resident before adding a case.", "error")
        return redirect(url_for('healthworker.illness_records'))

    resident = Resident.query.get(resident_id)
    if not resident:
        flash("Resident not registered. Only registered residents can be added.", "error")
        return redirect(url_for('healthworker.illness_records'))

    symptoms = data.get('symptoms', '').strip()
    case_date = data.get('date')

    if not re.match(r"^[A-Za-z ,.-]{5,}$", symptoms):
        flash("Enter valid symptoms (letters only, min 5 chars).", "error")
        return redirect(url_for('healthworker.illness_records'))

    if not case_date:
        flash("Date is required.", "error")
        return redirect(url_for('healthworker.illness_records'))

    try:
        selected_date = datetime.strptime(case_date, "%Y-%m-%d").date()
        if selected_date != datetime.utcnow().date():
            flash("Date must be today's date.", "error")
            return redirect(url_for('healthworker.illness_records'))
    except ValueError:
        flash("Invalid date format.", "error")
        return redirect(url_for('healthworker.illness_records'))

    status = data.get('status', 'Reported')
    if status not in ["Reported", "Under Treatment", "Recovered"]:
        status = "Reported"

    case = Illness(
        symptoms=symptoms,
        status=status,
        date=selected_date,
        resident_id=resident.id,
        healthworker_id=worker.id
    )

    db.session.add(case)
    db.session.commit()

    flash("Case added successfully!", "success")
    return redirect(url_for('healthworker.illness_records'))

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
        case.healthworker_id = int(worker_id)

    # 🔥 UPDATE DATE
    case_date = request.form.get('date')
    if case_date:
        try:
            case.date = datetime.strptime(case_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format.", "error")
            return redirect(url_for('healthworker.illness_records'))

    db.session.commit()

    flash("Case updated successfully!", "success")
    return redirect(url_for('healthworker.illness_records'))


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

    return redirect(url_for('healthworker.illness_records'))

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
        return redirect(url_for('healthworker.users'))

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

    return redirect(url_for('healthworker.users'))


# =========================
# SESSION SECURITY
# =========================
SESSION_TIMEOUT = 30  # minutes

@app.before_request
def security_middleware():
    if request.endpoint is None:
        return

    allowed_routes = [
        'auth.home',
        'auth.login',
        'auth.register',
        'auth.register_page',
        'auth.check_username',
        'auth.suggest_usernames',
        'static',
        'sensor_data'
    ]

    # =========================
    # 🔒 SESSION TIMEOUT
    # =========================
    session.permanent = True

    if 'last_activity' in session:
        if time.time() - session['last_activity'] > SESSION_TIMEOUT * 60:
            session.clear()
            return redirect(url_for('auth.home'))

    session['last_activity'] = time.time()

    # =========================
    # 🔐 LOGIN REQUIRED
    # =========================
    if request.endpoint not in allowed_routes and 'user' not in session:
        return redirect(url_for('auth.home'))
        
# =========================
# =========================
# ERROR HANDLERS
# =========================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return render_template('500.html'), 500


# RUN APP
# =========================

if __name__ == '__main__':
    with app.app_context():
        if app.config.get('DEBUG'):
            db.create_all()

    app.run(host='0.0.0.0', port=5000, debug=app.config.get('DEBUG', False))