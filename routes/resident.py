from flask import Blueprint, render_template, session, redirect, request, flash, url_for
from datetime import datetime

from models import User, Resident, Temperature, HeatIndex, Illness
from models import db
from utils import get_heat_level, get_alert

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
    if not barangay:
        return None

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

    if resident.address:
        barangay = resident.address.split(" - ")[0]   # 🔥 FIX
    else:
        barangay = None

    latest = get_latest_heat_data(barangay)

    temperature = latest.temperature if latest else 0
    heat_index = latest.heat_index if latest else 0

    level_text, level_class, level_icon = get_heat_level(heat_index)
    reminders = get_safety_reminders(level_text)

    # 🔥 SHOW ONLY FOR DANGEROUS LEVELS + NO REPEAT
    danger_levels = ["EXTREME CAUTION", "DANGER", "EXTREME DANGER"]

    if level_text in danger_levels:

        # Only show if NEW level
        if session.get("last_alert") != level_text:
            alert_message, alert_class, alert_icon = get_alert(level_text)
            session["last_alert"] = level_text
        else:
            alert_message, alert_class, alert_icon = "", "", ""

    else:
        # Reset so next dangerous level can trigger again
        session["last_alert"] = None
        alert_message, alert_class, alert_icon = "", "", ""

    return render_template(
        'resident_dashboard.html',
        temperature=temperature,
        heat_index=heat_index,
        level_text=level_text,
        level_class=level_class,
        level_icon=level_icon,
        reminders=reminders,
        barangay=resident.address,
        alert_message=alert_message,
        alert_class=alert_class,
        alert_icon=alert_icon
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

    if resident.address:
        barangay = resident.address.split(" - ")[0]
    else:
        barangay = None

    latest = get_latest_heat_data(barangay)

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

    if not user:
        return redirect(url_for('auth.home'))

    # ✅ GET RESIDENT PROFILE
    resident = Resident.query.filter_by(user_id=user.id).first()

    if not resident:
        flash("Please complete your profile first.", "error")
        return redirect(url_for('account'))

    if request.method == 'POST':
        symptoms = request.form.get('symptoms', '').strip()
        date = request.form.get('date')

        # =========================
        # ✅ VALIDATION
        # =========================
        if not symptoms or not date:
            flash("All fields are required!", "error")
            return redirect(url_for('resident.report_illness'))

        # ❌ Prevent very short or nonsense input
        if len(symptoms) < 5:
            flash("Please describe your symptoms properly.", "error")
            return redirect(url_for('resident.report_illness'))

        # ❌ Prevent future date
        try:
            selected_date = datetime.strptime(date, "%Y-%m-%d").date()
            today = datetime.today().date()
            if selected_date != today:
                flash("Date must be today's date only!", "error")
                return redirect(url_for('resident.report_illness'))
        except ValueError:
            flash("Invalid date format!", "error")
            return redirect(url_for('resident.report_illness'))

        # =========================
        # ✅ SAVE TO DATABASE
        # =========================
        illness = Illness(
            symptoms=symptoms,
            status="Reported",
            date=selected_date,
            resident_id=resident.id
        )

        db.session.add(illness)
        db.session.commit()

        flash("Illness reported successfully!", "success")
        return redirect(url_for('resident.case_status'))

    return render_template('report_illness.html', fullname=user.fullname, today=datetime.utcnow().date())


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