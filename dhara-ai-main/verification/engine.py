def identity_check(data, farmer_type):
    return 0  # Assuming identity verified in onboarding

def land_check(data, farmer_type):
    penalty = 0
    if float(data.get('land_size', 0)) < 1.0:
        penalty += 5
    if farmer_type == "New Farmer":
        penalty += 10 # Higher uncertainty
    elif farmer_type == "Existing Farmer":
        penalty += 5
    return penalty

def crop_history_check(data, farmer_type):
    penalty = 0
    if farmer_type == "New Farmer":
        penalty += 15 # No history available
    elif farmer_type == "Existing Farmer":
        if data.get('crop_failure_history') == 1:
            penalty += 10
    else: # Verified Farmer
        if data.get('yield_consistency_index', 1) < 0.6:
            penalty += 5
    return penalty

def soil_check(data, farmer_type):
    penalty = 0
    soil_health = data.get('soil_health_index', 50)
    if soil_health < 40:
        penalty += 10
    elif soil_health < 60:
        penalty += 5
    return penalty

def weather_check(data, farmer_type):
    penalty = 0
    rainfall_dev = abs(data.get('rainfall_deviation', 0))
    if rainfall_dev > 25:
        penalty += 15
    elif rainfall_dev > 15:
        penalty += 5
    return penalty

def financial_history_check(data, farmer_type):
    penalty = 0
    if farmer_type == "New Farmer":
        penalty += 20
    elif farmer_type == "Existing Farmer":
        penalty += 10
        if data.get('previous_repayment_status') == 0:
            penalty += 15
    else: # Verified Farmer
        if data.get('previous_repayment_status') == 0:
            penalty += 25 # High penalty for known defaults
    return penalty

def behavior_analysis(data, farmer_type):
    # Proxy for app behavior/consistency
    return 5 if farmer_type == "New Farmer" else 0

def fraud_detection(data, farmer_type):
    penalty = 0
    # Simple check on extreme outliers
    if data.get('loan_to_income_ratio', 0) > 0.8:
        penalty += 15
    if data.get('avg_yield_last_3_seasons', 0) > 80: # Unlikely high yield
        penalty += 10
    return penalty

def run_verification(data, farmer_type):
    """Runs all checks and returns final confidence score, risk category, and breakdown."""
    penalties = {
        "Identity": identity_check(data, farmer_type),
        "Land": land_check(data, farmer_type),
        "Crop History": crop_history_check(data, farmer_type),
        "Soil Health": soil_check(data, farmer_type),
        "Weather Impact": weather_check(data, farmer_type),
        "Financial History": financial_history_check(data, farmer_type),
        "Behavior": behavior_analysis(data, farmer_type),
        "Fraud Indicators": fraud_detection(data, farmer_type),
    }
    
    total_penalty = sum(penalties.values())
    confidence_score = max(0, 100 - total_penalty)
    
    if confidence_score >= 85:
        category = "High"
    elif confidence_score >= 60:
        category = "Medium"
    else:
        category = "Low"
        
    return {
        "confidence_score": confidence_score,
        "category": category,
        "penalties_breakdown": penalties
    }
