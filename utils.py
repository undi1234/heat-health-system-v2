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
    
def get_alert(level_text):
    if level_text == "EXTREME CAUTION":
        return " Extreme caution! Avoid going outside.", "warning", "⚠️"

    elif level_text == "DANGER":
        return " Danger! Stay indoors and hydrate frequently.", "danger", "🚨"

    elif level_text == "EXTREME DANGER":
        return " Extreme danger! Emergency heat conditions.", "extreme", "🔥"

    return "", "", ""