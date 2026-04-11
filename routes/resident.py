from flask import Blueprint, render_template, session, redirect, request, flash, url_for
from datetime import datetime

from models import User, Resident, Temperature, HeatIndex, Illness
from models import db
from utils import get_heat_level

resident_bp = Blueprint('resident', __name__)

# =========================
# GET SAFETY REMINDERS
# =========================
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

    elif level == "EXTREME CAUTION":
        return [
            {"en": "Reduce outdoor activities, especially during midday", "bi": "Likayi ang gawas nga aktibidad labi na sa udto"},
            {"en": "Drink water frequently to stay hydrated", "bi": "Sige'g inom tubig aron dili ma-dehydrate"},
            {"en": "Wear lightweight, light-colored clothing", "bi": "Magsul-ob og gaan ug hayag nga kolor nga sinina"},
            {"en": "Use umbrella or hat when outdoors", "bi": "Paggamit og payong o kalo kung mogawas"},
            {"en": "Watch for signs of heat exhaustion", "bi": "Bantayi ang sintomas sa heat exhaustion"}
        ]

    elif level == "DANGER":
        return [
            {"en": "Limit outdoor activities as much as possible", "bi": "Limitahi ang gawas nga aktibidad"},
            {"en": "Stay indoors during peak heat hours", "bi": "Magpabilin sa sulod sa balay"},
            {"en": "Use fans or air conditioning", "bi": "Paggamit og electric fan o aircon"},
            {"en": "Drink water every 15–20 minutes", "bi": "Mag-inom og tubig kada 15–20 minutos"},
        ]

    elif level == "EXTREME DANGER":
        return [
            {"en": "Avoid going outside unless necessary", "bi": "Ayaw gawas kung dili kinahanglan"},
            {"en": "Stay in cool places", "bi": "Magpabilin sa bugnaw nga lugar"},
            {"en": "Drink water frequently", "bi": "Sige'g inom tubig"},
            {"en": "Check elderly and children", "bi": "Bantayi ang tigulang ug bata"},
        ]

    return [{"en": "No reminders available", "bi": "Walay pahimangno"}]


# =========================
# HELPER FUNCTION (NEW)
# =========================
def get_latest_heat_data(barangay):
    latest_temp = Temperature.query.filter_by(
        barangay=barangay
    ).order_by(Temperature.id.desc()).first()

    if not latest_temp:
        return None

    return HeatIndex.query.filter_by(
        temperature_id=latest_temp.id
    ).first()


# =========================
# RESIDENT DASHBOARD
# =========================
@resident_bp.route('/resident_dashboard')
def resident_dashboard():
    if 'user' not in session or session.get('role') != "Resident":
        return redirect(url_for('auth.home'))

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.home'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.home'))

    resident = Resident.query.filter_by(user_id=user.id).first()
    if not resident:
        flash("Please complete your profile first.", "error")
        return redirect(url_for('account'))

    latest = get_latest_heat_data(resident.address)

    temperature = latest.temperature if latest else 0
    heat_index = latest.heat_index if latest else 0

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
        barangay=resident.address
    )


# =========================
# SAFETY ALERTS
# =========================
@resident_bp.route('/safety_alerts')
def safety_alerts():
    if 'user' not in session or session.get('role') != "Resident":
        return redirect(url_for('auth.home'))

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.home'))

    user = User.query.get(user_id)
    resident = Resident.query.filter_by(user_id=user.id).first()

    if not resident:
        return redirect(url_for('auth.home'))

    current_time = datetime.now().strftime("%B %d, %Y | %I:%M:%S %p")

    latest = get_latest_heat_data(resident.address)

    temperature = latest.temperature if latest else 0
    heat_index = latest.heat_index if latest else 0

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


# =========================
# REPORT ILLNESS
# =========================
@resident_bp.route('/report_illness', methods=['GET', 'POST'])
def report_illness():
    if 'user' not in session or session.get('role') != "Resident":
        return redirect(url_for('auth.home'))

    user = User.query.filter_by(username=session['user']).first()

    if request.method == 'POST':
        data = request.form

        # ✅ VALIDATION (NEW)
        if not data.get('symptoms') or not data.get('date'):
            flash("All fields are required!", "error")
            return redirect(url_for('resident.report_illness'))

        resident = Resident.query.filter_by(user_id=user.id).first()

        # ❌ REMOVE AUTO CREATE (FIXED)
        if not resident:
            flash("Please complete your profile first.", "error")
            return redirect(url_for('account'))

        illness = Illness(
            symptoms=data['symptoms'],
            status="Reported",
            date=data['date'],
            resident_id=resident.id
        )

        db.session.add(illness)
        db.session.commit()

        flash("Illness reported successfully!", "success")
        return redirect(url_for('resident.case_status'))

    return render_template('report_illness.html', fullname=user.fullname)


# =========================
# CASE STATUS
# =========================
@resident_bp.route('/case_status')
def case_status():
    if 'user' not in session or session.get('role') != "Resident":
        return redirect(url_for('auth.home'))

    resident = Resident.query.filter_by(user_id=session.get('user_id')).first()

    if not resident:
        return render_template('case_status.html', cases=[])

    cases = Illness.query.filter_by(resident_id=resident.id).all()

    return render_template('case_status.html', cases=cases)