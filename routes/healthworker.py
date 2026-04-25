from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, User, Resident, HealthWorker, Illness, Temperature
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from collections import defaultdict


healthworker_bp = Blueprint('healthworker', __name__)

# =========================
# HEALTH WORKER DASHBOARD
# =========================
@healthworker_bp.route('/health_worker_dashboard')
def health_worker_dashboard():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect(url_for('auth.home'))

    total_cases = Illness.query.count()
    critical_alerts = Illness.query.filter(
        Illness.status.in_(["Reported", "Under Treatment"])
    ).count()

    return render_template(
        'health_worker_dashboard.html',
        total_cases=total_cases,
        critical_alerts=critical_alerts
    )

# =========================
# RESIDENTS MANAGEMENT
# =========================
@healthworker_bp.route('/residents_management')
def residents_management():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect(url_for('auth.home'))

    residents = Resident.query.order_by(Resident.name.asc()).all()

    ALL_PUROKS = [
        "P1 Manggahan",
        "P2 Cocoahill",
        "P3 Maligaya",
        "P4 Camarin",
        "P5 Riverside",
        "P6 Buntod",
        "P7 Tuog"
    ]

    grouped_residents = {p: [] for p in ALL_PUROKS}

    # Pre-load all latest temperatures in one query
    latest_temps = db.session.query(
        Temperature.barangay, 
        func.max(Temperature.id).label('id')
    ).group_by(Temperature.barangay).subquery()
    
    temps = db.session.query(Temperature).filter(
        Temperature.id.in_(db.session.query(latest_temps.c.id))
    ).all()
    
    temp_dict = {t.barangay: t.value for t in temps}

    for r in residents:
        purok = r.address.split(" - ")[-1] if r.address else "Unknown"

        # Optimized temperature lookup
        if r.address:
            barangay = r.address.split(" - ")[0]
            r.temperature = temp_dict.get(barangay, "No Data")
        else:
            r.temperature = "N/A"

        # ✅ avoid crash if unknown purok
        if purok in grouped_residents:
            grouped_residents[purok].append(r)
        else:
            grouped_residents.setdefault("Unknown", []).append(r)

    # ✅ SORT PUROK (P1 → P7)
    grouped_residents = dict(sorted(grouped_residents.items()))

    return render_template(
        'residents_management.html',
        grouped_residents=grouped_residents
    )

# =========================
# HEALTH WORKERS
# =========================
@healthworker_bp.route('/health_workers')
def health_workers():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect(url_for('auth.home'))

    workers = HealthWorker.query.order_by(HealthWorker.name.asc()).all()

    ALL_POSITIONS = [
        "Nurse",
        "Midwife",
        "Barangay Health Worker"
    ]

    # ✅ initialize empty groups
    grouped_workers = {p: [] for p in ALL_POSITIONS}

    for w in workers:
        position = w.position if w.position else "Unknown"

        worker_data = {
            "id": w.id,
            "code": f"W{w.id:03d}",
            "name": w.name,
            "position": w.position,
            "contact": w.contact
        }

        if position in grouped_workers:
            grouped_workers[position].append(worker_data)
        else:
            grouped_workers.setdefault("Unknown", []).append(worker_data)

    # ✅ keep order clean
    grouped_workers = dict(sorted(grouped_workers.items()))

    return render_template(
        'health_workers.html',
        grouped_workers=grouped_workers
    )

# =========================
# ADD HEALTH WORKERS
# =========================
@healthworker_bp.route('/add_health_worker', methods=['POST'])
def add_health_worker():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect(url_for('auth.home'))
    
    data = request.form

    # ✅ GET VALUES SAFELY
    name = data.get('name', '').strip()
    position = data.get('position', '').strip()
    contact = data.get('contact', '').strip()

    # ❌ VALIDATION
    if not name or not position or not contact:
        flash("All fields are required!", "error")
        return redirect(url_for('healthworker.health_workers'))

    if not contact.isdigit() or len(contact) < 10:
        flash("Contact must be a valid number!", "error")
        return redirect(url_for('healthworker.health_workers'))

    # 🔒 POSITION VALIDATION
    valid_positions = ["Nurse", "Midwife", "Barangay Health Worker"]
    if position not in valid_positions:
        flash("Invalid position!", "error")
        return redirect(url_for('healthworker.health_workers'))

    # ✅ CREATE WORKER
    worker = HealthWorker(
        name=name,
        position=position,
        contact=contact
    )

    db.session.add(worker)
    db.session.commit()

    flash("Health Worker added successfully!", "success")
    return redirect(url_for('healthworker.health_workers'))

# =========================
# DELETE HEALTH WORKERS
# =========================
@healthworker_bp.route('/delete_health_worker/<int:id>', methods=['POST'])
def delete_health_worker(id):
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect(url_for('auth.home'))

    worker = HealthWorker.query.get_or_404(id)

    if worker.user_id and worker.user_id == session.get('user_id'):
        flash("You cannot delete your own account!", "error")
        return redirect(url_for('healthworker.health_workers'))

    try:
        # ✅ DELETE LINKED USER
        if worker.user_id:
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

    return redirect(url_for('healthworker.health_workers'))

# =========================
# ADD RESIDENTS
# =========================
@healthworker_bp.route('/add_resident', methods=['POST'])
def add_resident():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect(url_for('auth.home'))

    name = request.form.get('name')
    gender = request.form.get('gender')
    address = request.form.get('address')
    contact = request.form.get('contact')

    if not all([name, gender, address, contact]):
        flash("All fields are required!", "error")
        return redirect(url_for('healthworker.residents_management'))

    resident = Resident(
        name=name,
        gender=gender,
        address=address,
        contact=contact
    )

    db.session.add(resident)
    db.session.commit()

    flash("Resident added successfully!", "success")
    return redirect(url_for('healthworker.residents_management'))


# =========================
# ILLNESS RECORDS
# =========================
@healthworker_bp.route('/illness_records')
def illness_records():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect(url_for('auth.home'))

    records = Illness.query.order_by(Illness.id.desc()).all()
    workers = HealthWorker.query.all()  

    return render_template(
        'illness_records.html',
        records=records,
        workers=workers  
    )

# =========================
# USERS
# =========================
@healthworker_bp.route('/users')
def users():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect(url_for('auth.home'))

    all_users = User.query.all()

    return render_template('users.html', users=all_users,
                        username=session.get('user'),
                        role=session.get('role'))
