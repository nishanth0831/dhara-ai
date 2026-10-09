import os
import sys

# ensure repo root in path
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from services.model_service import predict_credit_risk, get_model_and_features


def test_model_loading():
    model, features = get_model_and_features()
    assert model is not None, "Model failed to load; check model files"
    assert isinstance(features, list), "Features should be a list"
    assert len(features) > 0, "Feature list is empty"


def test_prediction_basic():
    sample = {
        "Area": 5,
        "Annual_Rainfall": 1000,
        "Fertilizer": 120,
        "Pesticide": 10,
        "Crop": "Wheat",
        "Season": "Rabi",
        "State": "Uttar Pradesh",
    }
    result = predict_credit_risk(sample, 700)
    assert "trust_score" in result
    assert 0 <= result["trust_score"] <= 100
    assert result.get("risk_level")
    assert result.get("loan_decision")


if __name__ == "__main__":
    print("Running model_service tests")
    test_model_loading()
    test_prediction_basic()
    print("All tests passed.")
