import os

# joblib may not be installed in minimal environments; fall back to pickle
try:
    import joblib
except ImportError:
    import pickle as _pickle

    class _JoblibFallback:
        @staticmethod
        def load(f):
            return _pickle.load(f)

        @staticmethod
        def dump(obj, f):
            return _pickle.dump(obj, f)

    joblib = _JoblibFallback()

try:
    import pandas as pd
except ImportError:
    pd = None
    print("[model_service] pandas is not installed; predictions will not work")

try:
    import numpy as np
except ImportError:
    np = None
    print("[model_service] numpy is not installed; predictions may fail")

_model_cache = None
_features_cache = None

def get_model_and_features():
    global _model_cache, _features_cache
    if _model_cache is None or _features_cache is None:
        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
        model_path = os.path.join(model_dir, 'credit_model.pkl')
        features_path = os.path.join(model_dir, 'model_features.pkl')
        
        if os.path.exists(model_path) and os.path.exists(features_path):
            try:
                _model_cache = joblib.load(model_path)
                _features_cache = joblib.load(features_path)
            except Exception as e:
                print(f"[model_service] Failed to load model or features: {e}")
        else:
            print(f"[model_service] Model files not found at {model_dir}")
    return _model_cache, _features_cache

def normalize_cibil(cibil_score):
    """
    Convert CIBIL (300–900) to 0–1 scale
    """
    if cibil_score < 300:
        cibil_score = 300
    if cibil_score > 900:
        cibil_score = 900
    return (cibil_score - 300) / 600  

def calculate_final_trust_score(model_prob, cibil_score):
    """
    Combine ML probability + CIBIL score
    70% ML Model + 30% CIBIL
    """
    cibil_normalized = normalize_cibil(cibil_score)
    trust_score = (0.7 * model_prob + 0.3 * cibil_normalized) * 100
    return int(trust_score)

def get_risk_label(score):
    if score >= 80:
        return "Very Low Risk (Highly Creditworthy)"
    elif score >= 60:
        return "Low Risk (Creditworthy Farmer)"
    elif score >= 40:
        return "Moderate Risk (Needs Review)"
    else:
        return "High Risk (Loan Risk)"

def loan_decision(score):
    if score >= 75:
        return "Loan Approved"
    elif score >= 50:
        return "Manual Review Required"
    else:
        return "Loan Rejected"

def predict_credit_risk(input_data: dict, cibil_score: int):
    """
    Returns the final trust score, risk level, and loan decision.
    input_data expects keys like: Area, Annual_Rainfall, Fertilizer, Pesticide, Crop, Season, State
    """
    model, features = get_model_and_features()
    
    if not model or not features:
        # Fallback if model missing - propagate flag so frontend/report can note it
        return {
            "trust_score": 50.0,
            "risk_level": "Unknown - Model Missing",
            "loan_decision": "Manual Review Required",
            "model_available": False,
        }

    df = pd.DataFrame([input_data])
    df = pd.get_dummies(df)
    
    # Reindex to ensure all features expected by the model are present (fill with 0)
    df = df.reindex(columns=features, fill_value=0)
    
    # Predict probability of class 1 (Repay)
    try:
        if hasattr(model, 'predict_proba'):
            prob = model.predict_proba(df)[0][1]
        else:
            # fallback for simple models
            prob = float(model.predict(df)[0])
    except Exception as e:
        print(f"[model_service] prediction failed: {e}")
        prob = 0.5
    
    final_trust_score = calculate_final_trust_score(prob, cibil_score)
    risk = get_risk_label(final_trust_score)
    decision = loan_decision(final_trust_score)

    return {
        "trust_score": float(final_trust_score),
        "risk_level": risk,
        "loan_decision": decision,
        "model_available": True,
    }
