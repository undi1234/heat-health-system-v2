from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, User, Resident, HealthWorker, Illness
from sqlalchemy.exc import IntegrityError

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

    return render_template('residents_management.html', residents=residents)

# =========================
# HEALTH WORKERS
# =========================
@healthworker_bp.route('/health_workers')
def health_workers():
    if 'user' not in session or session.get('role') != "HealthWorker":
        return redirect(url_for('auth.home'))

    workers = HealthWorker.query.order_by(HealthWorker.name.asc()).all()

    workers_with_code = []
    for i, w in enumerate(workers, start=1):
        workers_with_code.append({
            "code": f"W{i:03d}",
            "id": w.id,
            "name": w.name,
            "position": w.position,
            "contact": w.contact
        })

    return render_template('health_workers.html', workers=workers_with_code)

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
