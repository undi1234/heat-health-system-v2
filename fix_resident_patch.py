from pathlib import Path

resident_file = Path('routes/resident.py')
text = resident_file.read_text(encoding='utf-8')
old = '''# =========================
# HELPER FUNCTION (NEW)
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
# RESIDENT DASHBOARD'''
new = '''# =========================
# HELPER FUNCTIONS (NEW)
def parse_address(address):
    if not address:
        return None, None

    if " - " in address:
        barangay, purok = [part.strip() for part in address.split(" - ", 1)]
        return barangay, purok

    return address.strip(), None


def get_latest_temperature_record(barangay=None, purok=None):
    query = Temperature.query

    if barangay:
        query = query.filter_by(barangay=barangay)

    if purok:
        purok_record = query.filter_by(purok=purok).order_by(Temperature.id.desc()).first()
        if purok_record:
            return purok_record

    return query.order_by(Temperature.id.desc()).first()


def get_latest_heat_data(barangay=None, purok=None):
    latest_temp = get_latest_temperature_record(barangay, purok)
    if not latest_temp:
        return None

    return HeatIndex.query.filter_by(
        temperature_id=latest_temp.id
    ).first()

# =========================
# RESIDENT DASHBOARD'''
if old not in text:
    raise SystemExit('resident helper block not found')
text = text.replace(old, new)

old3 = '''    return render_template(
        'resident_dashboard.html',
        temperature=temperature,
        heat_index=heat_index,
        level_text=level_text,
        level_class=level_class,
        level_icon=level_icon,
        reminders=reminders,
        barangay=resident.address,
        recent_temps=recent_temps,
        alert_message=alert_message,
        alert_class=alert_class,
        alert_icon=alert_icon
    )
'''
new3 = '''    return render_template(
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
'''
if old3 not in text:
    raise SystemExit('render_template block not found')
text = text.replace(old3, new3)
resident_file.write_text(text, encoding='utf-8')

html_file = Path('templates/resident_dashboard.html')
text = html_file.read_text(encoding='utf-8')
old_html = '''    <!-- RECENT TEMPERATURE RECORDS -->
    <div class="records">
        <h3>Recent Temperature Records</h3>
        {% if recent_temps %}
        <table class="record-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Date</th>
                    <th>Time</th>
                    <th>Temperature</th>
                    <th>Barangay</th>
                    <th>Purok</th>
                </tr>
            </thead>
            <tbody>
                {% for r in recent_temps %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ r.date.strftime("%B %d, %Y") }}</td>
                    <td>{{ r.time or r.date.strftime("%I:%M:%S %p") }}</td>
                    <td>{{ r.value }}°C</td>
                    <td>{{ r.barangay }}</td>
                    <td>{{ r.purok }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No recent temperature records available yet.</p>
        {% endif %}
    </div>

    <!-- SAFETY REMINDER -->'''
new_html = '''    <!-- SAFETY REMINDER -->'''
if old_html not in text:
    raise SystemExit('html records section not found')
text = text.replace(old_html, new_html)
html_file.write_text(text, encoding='utf-8')
print('updated')
