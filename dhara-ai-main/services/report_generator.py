import datetime

def generate_lender_report(farmer_input, cibil_score, prediction_result, model_available: bool = True):
    report = {}

    # Basic Farmer Info
    report["Farmer Details"] = {
        "Crop": farmer_input.get("Crop", "N/A"),
        "State": farmer_input.get("State", "N/A"),
        "Season": farmer_input.get("Season", "N/A"),
        "Land Area (hectares)": farmer_input.get("Area", "N/A")
    }

    # Agricultural Indicators
    report["Agricultural Indicators"] = {
        "Annual Rainfall (mm)": farmer_input.get("Annual_Rainfall", "N/A"),
        "Fertilizer Usage (kg/ha)": farmer_input.get("Fertilizer", "N/A"),
        "Pesticide Usage (kg/ha)": farmer_input.get("Pesticide", "N/A")
    }

    # Financial Profile
    report["Financial Profile"] = {
        "CIBIL Score": cibil_score,
        "CIBIL Rating": get_cibil_rating(cibil_score)
    }

    # AI Risk Assessment
    report["AI Credit Assessment"] = {
        "Trust Score (0-100)": prediction_result.get("trust_score", 0),
        "Risk Level": prediction_result.get("risk_level", "Unknown"),
        "Loan Decision": prediction_result.get("loan_decision", "Unknown")
    }
    if not model_available:
        report["AI Credit Assessment"]["Model Notice"] = "Model file missing – default score used"

    # Risk Justification (VERY IMPORTANT FOR LENDERS)
    report["AI Justification"] = generate_justification(
        farmer_input, cibil_score, prediction_result.get("trust_score", 0)
    )

    # Timestamp
    report["Report Generated On"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return report


def get_cibil_rating(cibil):
    if cibil >= 750:
        return "Excellent"
    elif cibil >= 650:
        return "Good"
    elif cibil >= 550:
        return "Average"
    else:
        return "Poor"


def generate_justification(farmer_input, cibil, trust_score):
    reasons = []

    if cibil >= 750:
        reasons.append("High CIBIL score indicates strong repayment history.")
    elif cibil < 550:
        reasons.append("Low CIBIL score increases financial default risk.")

    rainfall = farmer_input.get("Annual_Rainfall", 0)
    if rainfall > 900:
        reasons.append("Favorable rainfall supports stable crop yield.")
    elif rainfall < 500:
        reasons.append("Low rainfall may affect agricultural productivity.")

    area = farmer_input.get("Area", 0)
    if area >= 5:
        reasons.append("Larger land area suggests better income stability.")
    elif area < 2:
        reasons.append("Small land area indicates limited production capacity.")

    if trust_score >= 75:
        reasons.append("Overall AI assessment shows high creditworthiness.")
    elif trust_score <= 40:
        reasons.append("Multiple risk factors detected, proceeding with caution is advised.")

    return reasons
