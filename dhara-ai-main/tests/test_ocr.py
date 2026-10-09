import os
import sys
import pytest

# make sure project root is on path (same trick as other tests)
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

from utils.ocr import parse_soil_card_text, validate_card_id


def test_parse_simple_text():
    text = """
    Organization: Green Fields Co.
    Some other lines...
    Card ID: ISAAMW5678
    N:12 P:8 K:5
    """
    parsed = parse_soil_card_text(text)
    assert parsed["organization"] == "Green Fields Co."
    assert parsed["card_id"] == "ISAAMW5678"
    assert parsed["npk"]["N"] == 12.0
    assert parsed["npk"]["P"] == 8.0
    assert parsed["npk"]["K"] == 5.0


def test_validate_card_id_rules():
    existing = {"1234", "9999"}
    assert validate_card_id("isaamw0001", existing)
    assert not validate_card_id("badprefix0001", existing)
    assert not validate_card_id("ISAAMWXYZ", existing)
    # duplicate last4 should fail
    assert not validate_card_id("ISAAMW9999", existing)
    # missing id
    assert not validate_card_id(None, existing)


# simple sanity check for the application helper

def test_collect_farmer_data_from_state(monkeypatch):
    # import after setting path
    import streamlit as st

    # ensure clean state
    st.session_state.clear()
    # populate a few keys
    st.session_state.update(
        {
            "f_name": "Alice",
            "app_district": "Dharmapuri",
            "f_loan_amount": 12345,
            "f_land_size": 10,
            "f_irrig": "No",
            "f_avg_yield": 25,
            "f_yci": 0.8,
            "f_soil": 70,
            "f_rain_dev": 5,
            "f_repay": "Good",
            "f_lti": 0.4,
            "f_crop_fail": "No",
            "f_dist_yield_dev": -10,
            "f_crop_choice": "Rice",
            "f_crop_name": "",
            "f_crop_year": 2025,
            "f_season": "Kharif",
            "app_state": "TG",
            "f_area_ha": 1.5,
            "f_prod_t": 3.0,
            "f_annual_rain_mm": 1200,
            "f_fert_kg_ha": 100,
            "f_pest_kg_ha": 2,
            "f_yield_t_ha": 2.0,
            "f_cibil": 700,
            "soil_report_id": "ISAAMW1234",
        }
    )
    from app import _collect_farmer_data_from_state

    data = _collect_farmer_data_from_state()
    assert data["name"] == "Alice"
    assert data["district"] == "Dharmapuri"
    assert data["loan_amount"] == 12345
    assert data["fertilizer_kg"] == 100
    assert data["Crop"] == "Rice"
    assert data.get("soil_card_id") == "ISAAMW1234"


if __name__ == "__main__":
    pytest.main([__file__])
