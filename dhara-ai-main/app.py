import os

import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone

from streamlit_option_menu import option_menu

from utils.styles import apply_custom_css, THEME
from utils.ui import hero_section, feature_cards, process_steps, section_divider, landing_fullscreen_header
from services.auth_service import init_user_store
from utils.ocr import (
    extract_text_from_file_bytes,
    parse_soil_card_text,
    validate_card_id,
)


BACKEND_BASE_URL = os.getenv("DHARA_BACKEND_URL", "http://localhost:8000")


st.set_page_config(
    page_title="Dhara AI — Agricultural Credit Scoring",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"Get help": None, "Report a bug": None, "About": None},
)
apply_custom_css()


def _init_state() -> None:
    st.session_state.setdefault("user_store", init_user_store())

    st.session_state.setdefault("auth_user", None)  # dict or None
    st.session_state.setdefault("logged_in", False)

    st.session_state.setdefault("farmer_type", None)
    st.session_state.setdefault("farmer_data", {})
    st.session_state.setdefault("applications", [])
    st.session_state.setdefault("notifications", [])
    st.session_state.setdefault("weather_analysis", None)
    st.session_state.setdefault("_last_weather_loc", None)
    st.session_state.setdefault("_last_crop_selected", None)
    st.session_state.setdefault("public_view", "landing")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _push_notification(kind: str, message: str, app_id: int | None = None) -> None:
    st.session_state["notifications"].append(
        {"ts": _now_iso(), "kind": kind, "message": message, "app_id": app_id}
    )
    # Immediate feedback
    icon = "✅" if kind == "approved" else "⚠️" if kind == "rejected" else "ℹ️"
    st.toast(message, icon=icon)


def _logout() -> None:
    st.session_state["auth_user"] = None
    st.session_state["logged_in"] = False
    st.session_state["farmer_type"] = None
    st.session_state["farmer_data"] = {}
    st.rerun()


def _backend_get_weather(district: str, state: str):
    try:
        resp = requests.get(
            f"{BACKEND_BASE_URL}/weather",
            params={"district": district, "state": state},
            timeout=8,
        )
        if resp.status_code != 200:
            return False, None, f"Backend weather error: HTTP {resp.status_code}"
        payload = resp.json()
        if not payload.get("ok"):
            return False, None, payload.get("error", "Unknown backend error")
        return True, payload.get("data"), ""
    except requests.exceptions.ConnectionError:
        return False, None, "Could not connect to backend service. Check if server is running."
    except requests.exceptions.Timeout:
        return False, None, "Backend weather service timed out."
    except Exception as e:
        return False, None, f"Backend weather call failed: {e}"


def _backend_post_score(farmer_data: dict, farmer_type: str, cibil_score: int = 650):
    payload = {"farmer_data": farmer_data, "farmer_type": farmer_type, "cibil_score": cibil_score}
    # include username if available for logging
    if st.session_state.get("auth_user"):
        payload["username"] = st.session_state["auth_user"].get("username")
    try:
        resp = requests.post(
            f"{BACKEND_BASE_URL}/score",
            json=payload,
            timeout=10,
        )
        if resp.status_code != 200:
            return False, None, f"Backend score error: HTTP {resp.status_code}"
        payload = resp.json()
        if not payload.get("ok"):
            return False, None, payload.get("error", "Unknown backend error")
        return True, payload, ""
    except Exception as e:
        return False, None, f"Backend score call failed: {e}"


def _backend_post_report(farmer_data: dict, farmer_type: str, cibil_score: int = 650):
    payload = {"farmer_data": farmer_data, "farmer_type": farmer_type, "cibil_score": cibil_score}
    if st.session_state.get("auth_user"):
        payload["username"] = st.session_state["auth_user"].get("username")
    # if an application record is in session, include its id for audit
    if st.session_state.get("current_app_id"):
        payload["app_id"] = st.session_state.get("current_app_id")
    try:
        resp = requests.post(
            f"{BACKEND_BASE_URL}/report",
            json=payload,
            timeout=25,
        )
        if resp.status_code != 200:
            return False, None, None, f"Backend report error: HTTP {resp.status_code}"
        filename = resp.headers.get("Content-Disposition", "DharaAI_Report.pdf")
        # crude extraction of filename if present
        if "filename=" in filename:
            filename = filename.split("filename=")[-1].strip('"; ')
        return True, resp.content, filename, ""
    except Exception as e:
        return False, None, None, f"Backend report call failed: {e}"


# ---------------------------------------------------------------------------
# helpers that build / submit application payload from session state
# ---------------------------------------------------------------------------

def _collect_farmer_data_from_state() -> dict:
    """Gather values previously stored in `st.session_state` forms.
    This mirrors the logic that was previously inline under the "Save &
    continue" button so we can invoke it from multiple places (e.g. after
    OCR auto‑fill).
    """
    return {
        "name": st.session_state.get("f_name", ""),
        "district": st.session_state.get("app_district", ""),
        # include soil card identifier if available
        "soil_card_id": st.session_state.get("soil_report_id"),
        "loan_amount": st.session_state.get("f_loan_amount", 0),
        "land_size": st.session_state.get("f_land_size", 0),
        "irrigation_availability": 1 if st.session_state.get("f_irrig", "Yes") == "Yes" else 0,
        "avg_yield_last_3_seasons": st.session_state.get("f_avg_yield", 0),
        "yield_consistency_index": st.session_state.get("f_yci", 0),
        "soil_health_index": st.session_state.get("f_soil", 0),
        "rainfall_deviation": st.session_state.get("f_rain_dev", 0),
        "previous_repayment_status": 1 if st.session_state.get("f_repay", "Good") == "Good" else 0,
        "loan_to_income_ratio": st.session_state.get("f_lti", 0),
        "crop_failure_history": 1 if st.session_state.get("f_crop_fail", "No") == "Yes" else 0,
        "district_average_yield_deviation": st.session_state.get("f_dist_yield_dev", 0),
        "crop_name": st.session_state.get("f_crop_choice", "" ) if st.session_state.get("f_crop_choice") != "Other" else st.session_state.get("f_crop_name", ""),
        "crop_year": int(st.session_state.get("f_crop_year", 0)),
        "season": st.session_state.get("f_season", ""),
        "state": st.session_state.get("app_state", ""),
        "area_hectares": st.session_state.get("f_area_ha", 0),
        "production_tons": st.session_state.get("f_prod_t", 0),
        "annual_rainfall_mm": st.session_state.get("f_annual_rain_mm", 0),
        "fertilizer_kg": st.session_state.get("f_fert_kg_ha", 0),
        "pesticide_kg": st.session_state.get("f_pest_kg_ha", 0),
        "yield_value": st.session_state.get("f_yield_t_ha", 0),

        # the model also expects some upper-case keys
        "Area": st.session_state.get("f_area_ha", 0),
        "Annual_Rainfall": st.session_state.get("f_annual_rain_mm", 0),
        "Fertilizer": st.session_state.get("f_fert_kg_ha", 0),
        "Pesticide": st.session_state.get("f_pest_kg_ha", 0),
        "Crop": st.session_state.get("f_crop_choice", "") if st.session_state.get("f_crop_choice") != "Other" else st.session_state.get("f_crop_name", ""),
        "Season": st.session_state.get("f_season", ""),
        "State": st.session_state.get("app_state", ""),
    }


def _submit_application_from_state():
    """Run the exact same workflow that the "Save & continue" button used to
    execute.  This includes calling the /score endpoint and saving to
    /applications in the backend.  It also sets `st.session_state` values like
    `current_app_id` for later reporting.
    """
    farmer_data = _collect_farmer_data_from_state()
    cibil_score = st.session_state.get("f_cibil", 650)
    st.session_state["farmer_data"] = farmer_data
    st.session_state["cibil_score"] = cibil_score

    username = (st.session_state.get("auth_user") or {}).get("username", "anonymous")

    ok, score_payload, err = _backend_post_score(farmer_data, st.session_state["farmer_type"], cibil_score)
    if not ok or not score_payload:
        st.error(f"Could not score application via backend: {err}")
        return

    if score_payload.get("warning"):
        st.warning(score_payload["warning"])

    conf_score = float(score_payload.get("confidence_score", 0))
    trust_score = float(score_payload.get("trust_score", 0))

    base_record = {
        "farmer_username": username,
        "farmer_name": st.session_state.get("f_name", ""),
        "farmer_type": st.session_state["farmer_type"],
        "district": st.session_state.get("app_district", ""),
        "state": st.session_state.get("app_state", ""),
        "loan_amount": float(st.session_state.get("f_loan_amount", 0)),
        "approved_amount": None,
        "crop_name": st.session_state.get("f_crop_choice", "") if st.session_state.get("f_crop_choice") != "Other" else st.session_state.get("f_crop_name", ""),
        "season": st.session_state.get("f_season", ""),
        "trust_score": float(trust_score),
        "conf_score": float(conf_score),
        "risk_status": "Low"
        if trust_score > 70 and conf_score >= 85
        else "Medium"
        if trust_score > 40 and conf_score >= 60
        else "High",
        "status": "Pending",
        "applied_at": _now_iso(),
        "decided_at": None,
        "data": farmer_data,
    }

    try:
        resp = requests.post(
            f"{BACKEND_BASE_URL}/applications",
            json={"application": base_record},
            timeout=10,
        )
        if resp.status_code != 200:
            st.error(f"Backend application save failed (HTTP {resp.status_code})")
        else:
            payload = resp.json()
            if not payload.get("ok"):
                st.error(payload.get("error", "Backend save error"))
            else:
                st.success("Application saved to Dhāra backend. Open Dashboard for scoring outputs.")
                try:
                    app_id = payload.get("id")
                    if app_id:
                        st.session_state["current_app_id"] = app_id
                except Exception:
                    pass
    except Exception as e:
        st.error(f"Could not reach backend to save application: {e}")


def _backend_post_portfolio_report(applications: list[dict]):
    try:
        resp = requests.post(
            f"{BACKEND_BASE_URL}/portfolio-report",
            json={"applications": applications},
            timeout=30,
        )
        if resp.status_code != 200:
            return False, None, None, f"Backend portfolio report error: HTTP {resp.status_code}"
        filename = resp.headers.get("Content-Disposition", "DharaAI_Portfolio_Report.pdf")
        if "filename=" in filename:
            filename = filename.split("filename=")[-1].strip('"; ')
        return True, resp.content, filename, ""
    except Exception as e:
        return False, None, None, f"Backend portfolio report call failed: {e}"


def _top_nav(items: list[str], icons: list[str], default_index: int = 0) -> str:
    st.markdown('<div class="dhara-nav">', unsafe_allow_html=True)
    selected = option_menu(
        None,
        items,
        icons=icons,
        orientation="horizontal",
        default_index=default_index,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": THEME["brand"], "font-size": "16px"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "center",
                "margin": "0px 4px",
                "padding": "8px 12px",
                "border-radius": "8px",
                "color": THEME["text"],
            },
            "nav-link-selected": {"background-color": THEME["brand_bg_alpha"], "color": "#93c5fd"},
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return selected


def page_overview() -> None:
    hero_section()
    section_divider()
    feature_cards()
    section_divider()
    process_steps()
    section_divider()

    st.markdown("### Live status")
    u = st.session_state.get("auth_user")
    if not u:
        st.info("Sign in to start a new assessment and access the underwriting workflow.")
        return

    c1, c2, c3 = st.columns([1.3, 1.2, 1])
    with c1:
        st.success(f"Signed in as **{u['full_name']}** (`{u['username']}`)")
        st.caption(f"Role: {u['role']}")
    with c2:
        if st.session_state.get("farmer_type"):
            st.info(f"Active profile: **{st.session_state['farmer_type']}**")
        else:
            st.warning("No active farmer profile yet. Go to Application.")
    with c3:
        if st.button("Log out", type="secondary", use_container_width=True):
            _logout()


def page_auth() -> None:
    st.markdown("### Access")
    login_role = st.radio("Login as", ["Farmer", "Admin"], horizontal=True, key="login_role")
    t1, t2 = st.tabs(["Login", "Sign up"])

    with t1:
        st.markdown("#### Login")
        username = st.text_input("User ID", placeholder="e.g. dhara_agent01", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Sign in", type="primary", use_container_width=True):
                try:
                    resp = requests.post(
                        f"{BACKEND_BASE_URL}/auth/login",
                        json={"username": username, "password": password},
                        timeout=8,
                    )
                    if resp.status_code == 200:
                        payload = resp.json()
                        if payload.get("ok"):
                            user = payload.get("user", {})
                            # Enforce role from toggle
                            if login_role == "Admin" and user.get("role") != "Admin":
                                st.error("This account is not an Admin. Switch to Farmer or use an Admin ID.")
                                return
                            if login_role == "Farmer" and user.get("role") == "Admin":
                                st.error("This account is Admin-only. Switch Login as → Admin.")
                                return
                            st.session_state["auth_user"] = user
                            st.session_state["logged_in"] = True
                            st.success("Signed in successfully.")
                            st.rerun()
                        else:
                            st.error(payload.get("error", "Login failed."))
                    else:
                        st.error(f"Login failed (HTTP {resp.status_code}). Backend may be offline.")
                except Exception as e:
                    st.error(f"Could not reach backend: {e}")
        with c2:
            st.caption("Tip: Use the Sign up tab if you don't have an account yet.")

    with t2:
        st.markdown("#### Create account")
        st.caption(
            "Requirements: 4–32 char User ID (lowercase letters/numbers/`_`/`.`), password ≥ 8 chars with uppercase, lowercase, number, special character."
        )
        full_name = st.text_input("Full name", placeholder="Your legal name", key="su_name")
        phone = st.text_input("Phone (optional)", placeholder="+91...", key="su_phone")
        # Role comes from login_role toggle for simplicity
        role = "Admin" if login_role == "Admin" else "Farmer"
        st.text_input("Account type", value=role, key="su_role_display", disabled=True)
        username = st.text_input("Create User ID", placeholder="e.g. farmer_ramesh01", key="su_user")
        password = st.text_input("Create password", type="password", key="su_pass")
        password2 = st.text_input("Confirm password", type="password", key="su_pass2")

        if st.button("Create account", type="primary", use_container_width=True):
            if password != password2:
                st.error("Passwords do not match.")
            else:
                try:
                    resp = requests.post(
                        f"{BACKEND_BASE_URL}/auth/register",
                        json={
                            "username": username,
                            "full_name": full_name,
                            "phone": phone,
                            "role": role,
                            "password": password,
                        },
                        timeout=8,
                    )
                    if resp.status_code == 200:
                        payload = resp.json()
                        if payload.get("ok"):
                            st.success(payload.get("message", "Account created successfully!"))
                        else:
                            st.error(payload.get("error", "Account creation failed."))
                    else:
                        try:
                            err = resp.json().get("error", "")
                            st.error(err or f"Account creation failed (HTTP {resp.status_code}).")
                        except Exception:
                            st.error(f"Account creation failed (HTTP {resp.status_code}). Is the backend running?")
                except Exception as e:
                    st.error(f"Could not reach backend: {e}")


def page_application() -> None:
    st.markdown("### Underwriting application")
    st.caption("Complete the profile and inputs. Then view scoring outputs in Dashboard.")

    st.markdown("#### Applicant location (auto weather fetch)")
    loc1, loc2, loc3 = st.columns([1.2, 1.2, 1.6])
    
    # Initialize session state for these keys if we have farmer_data
    if "app_district" not in st.session_state:
        st.session_state["app_district"] = st.session_state.get("farmer_data", {}).get("district", "")
    if "app_state" not in st.session_state:
        st.session_state["app_state"] = st.session_state.get("farmer_data", {}).get("state", "")

    with loc1:
        district = st.text_input(
            "District / location",
            key="app_district",
        )
    with loc2:
        state = st.text_input(
            "State",
            key="app_state",
        )
    with loc3:
        st.caption("As you type district/state, Dhara AI fetches live weather + 5‑day rainfall outlook.")

    loc_key = (district or "").strip().lower() + "|" + (state or "").strip().lower()
    if district.strip() and state.strip() and st.session_state.get("_last_weather_loc") != loc_key:
        with st.spinner("Fetching live weather & rainfall outlook..."):
            ok, data, msg = _backend_get_weather(district, state)
        st.session_state["_last_weather_loc"] = loc_key
        st.session_state["weather_analysis"] = data if ok else None
        st.session_state["weather_error"] = msg if not ok else ""

    wx = st.session_state.get("weather_analysis")
    wx_err = st.session_state.get("weather_error", "")
    if wx_err:
        st.error(wx_err)
    elif wx:
        st.success(f"{wx['location']} — {wx['condition']}")
        cwx1, cwx2, cwx3, cwx4 = st.columns(4)
        cwx1.metric("Temp (°C)", f"{wx['temp_c']:.1f}" if wx.get("temp_c") is not None else "N/A")
        cwx2.metric("Humidity (%)", f"{wx['humidity']}" if wx.get("humidity") is not None else "N/A")
        rain_recent = f"{wx['rain_mm_3h']:.1f} mm (recent)" if wx.get("rain_mm_3h") is not None else "N/A"
        cwx3.metric("Recent rain", rain_recent)
        rain_next = f"{wx['rain_next_5d_mm']:.1f} mm" if wx.get("rain_next_5d_mm") is not None else "N/A"
        cwx4.metric("Rain (next 5 days)", rain_next)
        if wx.get("temp_max_5d_c") is not None:
            st.caption(f"5‑day temperature range: {wx.get('temp_min_5d_c', 'N/A')}°C → {wx.get('temp_max_5d_c', 'N/A')}°C")
    section_divider()

    tabs = st.tabs(["1) Farmer profile", "2) Input form"])
    with tabs[0]:
        st.markdown("#### Identify farmer type")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="dhara-card"><h4>🌱 New farmer</h4><p>First time applying with minimal history.</p></div>', unsafe_allow_html=True)
            if st.button("Select New Farmer", use_container_width=True):
                st.session_state["farmer_type"] = "New Farmer"
        with c2:
            st.markdown('<div class="dhara-card"><h4>🟡 Existing farmer</h4><p>Experienced farmer, new to Dhara AI.</p></div>', unsafe_allow_html=True)
            if st.button("Select Existing Farmer", use_container_width=True):
                st.session_state["farmer_type"] = "Existing Farmer"
        with c3:
            st.markdown('<div class="dhara-card"><h4>🔵 Verified farmer</h4><p>Historical performance available in system.</p></div>', unsafe_allow_html=True)
            if st.button("Select Verified Farmer", use_container_width=True):
                st.session_state["farmer_type"] = "Verified Farmer"

        if st.session_state.get("farmer_type"):
            st.success(f"Selected: **{st.session_state['farmer_type']}**")

    with tabs[1]:
        if not st.session_state.get("farmer_type"):
            st.warning("Select a farmer type first.")
            return

        st.markdown("#### Capture application inputs")

        # OCR upload: allow the agent to drop a soil card image/pdf and extract
        # basic metadata.  This is the new feature the user requested.
        upload = st.file_uploader(
            "Upload soil card (image or PDF)", type=["png", "jpg", "jpeg", "pdf"], key="soil_card_upload"
        )
        if upload is not None:
            data = upload.read()
            try:
                text = extract_text_from_file_bytes(data, upload.name or "")
                parsed = parse_soil_card_text(text)
                populated = False

                # Populate form fields from parsed values
                if parsed.get("card_id"):
                    st.session_state["soil_report_id"] = parsed["card_id"]
                    populated = True
                if parsed.get("organization"):
                    st.session_state["f_name"] = parsed["organization"]
                    populated = True
                npk = parsed.get("npk") or {}
                if npk:
                    total = sum(npk.values())
                    if total > 0:
                        st.session_state["f_fert_kg_ha"] = round(total, 1)
                        populated = True
                    # Derive soil health index from NPK (rough: 50 + total/5, capped at 100)
                    soil_from_npk = min(100, 50 + total / 5)
                    st.session_state["f_soil"] = round(soil_from_npk, 1)
                    populated = True

                if populated:
                    st.success("Extracted data from image. Form inputs below have been updated.")
                    with st.expander("OCR results", expanded=False):
                        st.json(parsed)

                # Check uniqueness; auto-submit if card valid & unique
                existing_last4 = set()
                try:
                    resp = requests.get(f"{BACKEND_BASE_URL}/applications", timeout=10)
                    if resp.status_code == 200:
                        pl = resp.json()
                        for a in pl.get("applications", []):
                            d = (a.get("data") or {})
                            sid = str(d.get("soil_card_id") or "")
                            if len(sid) >= 4:
                                existing_last4.add(sid[-4:])
                except Exception:
                    pass
                if validate_card_id(parsed.get("card_id"), existing_last4) and populated:
                    if st.button("Auto-submit from soil card", type="primary", key="ocr_autosubmit"):
                        _submit_application_from_state()
            except Exception as e:
                st.error(f"OCR/parse failure: {e}")

        # Crop defaults (fast autofill, user can override anytime)
        CROP_DEFAULTS = {
            "Rice": {"yield_t_ha": 3.2, "fert_kg_ha": 120.0, "pest_kg_ha": 3.0, "rain_mm_year": 1200.0, "season": "Kharif"},
            "Wheat": {"yield_t_ha": 3.4, "fert_kg_ha": 110.0, "pest_kg_ha": 2.0, "rain_mm_year": 600.0, "season": "Rabi"},
            "Cotton": {"yield_t_ha": 1.6, "fert_kg_ha": 90.0, "pest_kg_ha": 4.0, "rain_mm_year": 800.0, "season": "Kharif"},
            "Sugarcane": {"yield_t_ha": 70.0, "fert_kg_ha": 200.0, "pest_kg_ha": 4.0, "rain_mm_year": 1100.0, "season": "Whole Year"},
            "Maize": {"yield_t_ha": 3.0, "fert_kg_ha": 100.0, "pest_kg_ha": 2.5, "rain_mm_year": 700.0, "season": "Kharif"},
            "Pulses": {"yield_t_ha": 1.0, "fert_kg_ha": 30.0, "pest_kg_ha": 1.5, "rain_mm_year": 500.0, "season": "Rabi"},
            "Groundnut": {"yield_t_ha": 1.5, "fert_kg_ha": 40.0, "pest_kg_ha": 2.0, "rain_mm_year": 650.0, "season": "Kharif"},
        }

        # Inputs (no st.form) so weather + crop autofill can update instantly
        colA, colB = st.columns(2)
        with colA:
            name = st.text_input("Full Name", key="f_name")
            land_size = st.number_input("Land Size (Acres)", min_value=0.1, max_value=1000.0, value=float(st.session_state.get("f_land_size", 2.0)), key="f_land_size")
        with colB:
            loan_amount = st.number_input("Requested Loan Amount (₹)", min_value=1000, value=int(st.session_state.get("f_loan_amount", 50000)), key="f_loan_amount")
            loan_to_income = st.slider("Estimated Loan-to-Income Ratio", 0.0, 1.0, float(st.session_state.get("f_lti", 0.4)), key="f_lti")
            irrigation = st.selectbox("Irrigation Availability", ["Yes", "No"], index=0 if st.session_state.get("f_irrig", "Yes") == "Yes" else 1, key="f_irrig")

        st.markdown("#### Agronomic indicators")
        a1, a2 = st.columns(2)
        with a1:
            avg_yield = st.number_input("Average Yield (Quintals/Acre)", value=float(st.session_state.get("f_avg_yield", 20.0)), key="f_avg_yield")
            yield_consistency = st.slider("Yield Consistency Index", 0.0, 1.0, float(st.session_state.get("f_yci", 0.7)), key="f_yci")
        with a2:
            soil_health = st.slider("Soil Health Index (0-100)", 0.0, 100.0, float(st.session_state.get("f_soil", 65.0)), key="f_soil")
            crop_failure = st.selectbox("Previous Crop Failure History", ["No", "Yes"], index=0 if st.session_state.get("f_crop_fail", "No") == "No" else 1, key="f_crop_fail")

        st.markdown("#### Environmental & proxy indicators")
        wx = st.session_state.get("weather_analysis") or {}
        auto_rain_dev = st.checkbox("Auto-set Rainfall Deviation from live forecast", value=True, key="f_auto_rain_dev")
        computed_dev = None
        try:
            rain_next_5d = wx.get("rain_next_5d_mm")
            annual_mm = float(st.session_state.get("f_annual_rain_mm", 0.0))
            if isinstance(rain_next_5d, (int, float)) and annual_mm > 0:
                expected_5d = annual_mm / 73.0  # 365/5 ≈ 73 five-day windows
                if expected_5d > 0:
                    computed_dev = ((float(rain_next_5d) - expected_5d) / expected_5d) * 100.0
                    computed_dev = max(-80.0, min(80.0, computed_dev))
        except Exception:
            computed_dev = None

        if auto_rain_dev and computed_dev is not None:
            st.session_state["f_rain_dev"] = float(computed_dev)

        e1, e2 = st.columns(2)
        with e1:
            rainfall_dev = st.number_input(
                "Rainfall Deviation (%)",
                value=float(st.session_state.get("f_rain_dev", 0.0)),
                key="f_rain_dev",
                disabled=bool(auto_rain_dev and computed_dev is not None),
            )
            if auto_rain_dev and computed_dev is None:
                st.caption("Enter district/state + annual rainfall to auto-compute deviation.")
            elif auto_rain_dev and computed_dev is not None:
                st.caption(f"Auto: based on forecast next 5 days vs expected (from annual rainfall).")
        with e2:
            district_yield_dev = st.number_input(
                "District Avg Yield Deviation (%)",
                value=float(st.session_state.get("f_dist_yield_dev", 0.0)),
                key="f_dist_yield_dev",
            )

        st.markdown("#### Crop inputs (auto-fill)")
        cf1, cf2, cf3 = st.columns([1.2, 1, 1])
        with cf1:
            crop_choice = st.selectbox("Crop", ["Rice", "Wheat", "Cotton", "Sugarcane", "Maize", "Pulses", "Groundnut", "Other"], key="f_crop_choice")
            crop_name = st.text_input("Crop (name)", value="" if crop_choice != "Other" else st.session_state.get("f_crop_name", ""), key="f_crop_name")
        with cf2:
            crop_year = st.number_input("Crop year", min_value=2000, max_value=2100, value=int(st.session_state.get("f_crop_year", 2024)), key="f_crop_year")
            season = st.selectbox("Season", ["Kharif", "Rabi", "Summer", "Whole Year"], key="f_season")
        with cf3:
            auto_fill = st.checkbox("Auto-fill crop data", value=True, key="f_autofill")

        # Apply crop defaults when crop selection changes
        selected_crop = crop_choice if crop_choice != "Other" else (crop_name.strip() or "Other")
        if auto_fill and st.session_state.get("_last_crop_selected") != selected_crop and crop_choice != "Other":
            d = CROP_DEFAULTS.get(crop_choice)
            if d:
                st.session_state["f_yield_t_ha"] = float(d["yield_t_ha"])
                st.session_state["f_fert_kg_ha"] = float(d["fert_kg_ha"])
                st.session_state["f_pest_kg_ha"] = float(d["pest_kg_ha"])
                st.session_state["f_annual_rain_mm"] = float(d["rain_mm_year"])
                if not st.session_state.get("f_season"):
                    st.session_state["f_season"] = d["season"]
            st.session_state["_last_crop_selected"] = selected_crop

        c6, c7 = st.columns(2)
        with c6:
            area = st.number_input("Area (hectares)", min_value=0.1, value=float(st.session_state.get("f_area_ha", 1.0)), key="f_area_ha")
            yield_t_ha = st.number_input("Expected yield (tons/hectare)", min_value=0.0, value=float(st.session_state.get("f_yield_t_ha", 1.0)), key="f_yield_t_ha")
            production = st.number_input(
                "Production (metric tons)",
                min_value=0.0,
                value=float(st.session_state.get("f_prod_t", round(float(area) * float(yield_t_ha), 2))),
                key="f_prod_t",
            )
        with c7:
            annual_rainfall = st.number_input("Annual rainfall (mm)", min_value=0.0, value=float(st.session_state.get("f_annual_rain_mm", 800.0)), key="f_annual_rain_mm")
            fertilizer = st.number_input("Fertilizer used (kg/ha)", min_value=0.0, value=float(st.session_state.get("f_fert_kg_ha", 50.0)), key="f_fert_kg_ha")
            pesticide = st.number_input("Pesticide used (kg/ha)", min_value=0.0, value=float(st.session_state.get("f_pest_kg_ha", 5.0)), key="f_pest_kg_ha")

        # Suggestions (lightweight, instant)
        suggestions = {
            "Kharif": ["Rice", "Maize", "Cotton", "Groundnut"],
            "Rabi": ["Wheat", "Pulses"],
            "Summer": ["Maize"],
            "Whole Year": ["Sugarcane"],
        }
        st.caption(f"Suggested crops for {season}: " + ", ".join(suggestions.get(season, [])))

        st.markdown("#### Financial history")
        fin1, fin2 = st.columns(2)
        with fin1:
            repayment_status = st.selectbox("Previous Repayment Status", ["Good", "Bad", "No History"], key="f_repay")
        with fin2:
            cibil_score = st.number_input("CIBIL Score", min_value=300, max_value=900, value=int(st.session_state.get("f_cibil", 650)), key="f_cibil")

        st.markdown("#### Soil health report validation (lab registry)")
        vcol1, vcol2 = st.columns([1.4, 2])
        with vcol1:
            report_id = st.text_input("Soil report ID (SHC-...)", key="soil_report_id")
        with vcol2:
            if st.button("Verify soil report", type="secondary", use_container_width=True, key="btn_verify_soil"):
                try:
                    resp = requests.get(
                        f"{BACKEND_BASE_URL}/verify_soil_report",
                        params={"report_id": report_id},
                        timeout=8,
                    )
                    if resp.status_code != 200:
                        st.error(f"Backend soil verification error (HTTP {resp.status_code})")
                    else:
                        payload = resp.json()
                        if not payload.get("ok", False):
                            st.error(payload.get("error", "Soil report validation failed."))
                        else:
                            st.json(payload)
                except Exception as e:
                    st.error(f"Could not reach backend soil verification API: {e}")

        save = st.button("Save & continue", type="primary", use_container_width=True)
        if save:
            farmer_data = {
                "name": name,
                "district": district,
                "loan_amount": loan_amount,
                "land_size": land_size,
                "irrigation_availability": 1 if irrigation == "Yes" else 0,
                "avg_yield_last_3_seasons": avg_yield,
                "yield_consistency_index": yield_consistency,
                "soil_health_index": soil_health,
                "rainfall_deviation": rainfall_dev,
                "previous_repayment_status": 1 if repayment_status == "Good" else 0,
                "loan_to_income_ratio": loan_to_income,
                "crop_failure_history": 1 if crop_failure == "Yes" else 0,
                "district_average_yield_deviation": district_yield_dev,
                "crop_name": crop_choice if crop_choice != "Other" else crop_name,
                "crop_year": int(crop_year),
                "season": season,
                "state": state,
                "area_hectares": area,
                "production_tons": production,
                "annual_rainfall_mm": annual_rainfall,
                "fertilizer_kg": fertilizer,
                "pesticide_kg": pesticide,
                "yield_value": yield_t_ha,
                
                # Model specifically expects these keys with title case depending on usage:
                "Area": area,
                "Annual_Rainfall": annual_rainfall,
                "Fertilizer": fertilizer,
                "Pesticide": pesticide,
                "Crop": crop_choice if crop_choice != "Other" else crop_name,
                "Season": season,
                "State": state
            }
            wx = st.session_state.get("weather_analysis") or {}
            farmer_data["weather_rain_next_5d_mm"] = wx.get("rain_next_5d_mm")
            farmer_data["weather_temp_c"] = wx.get("temp_c")
            farmer_data["weather_condition"] = wx.get("condition")
            st.session_state["farmer_data"] = farmer_data
            st.session_state["cibil_score"] = cibil_score

            current_user = st.session_state.get("auth_user") or {}
            username = current_user.get("username", "anonymous")

            ok, score_payload, err = _backend_post_score(farmer_data, st.session_state["farmer_type"], cibil_score)
            if not ok or not score_payload:
                st.error(f"Could not score application via backend: {err}")
                return

            # show any warning coming from backend (e.g., model missing)
            if score_payload.get("warning"):
                st.warning(score_payload["warning"])

            conf_score = float(score_payload["confidence_score"])
            trust_score = float(score_payload["trust_score"])

            base_record = {
                "farmer_username": username,
                "farmer_name": name,
                "farmer_type": st.session_state["farmer_type"],
                "district": district,
                "state": state,
                "loan_amount": float(loan_amount),
                "approved_amount": None,
                "crop_name": (crop_choice if crop_choice != "Other" else crop_name),
                "season": season,
                "trust_score": float(trust_score),
                "conf_score": float(conf_score),
                "risk_status": "Low"
                if trust_score > 70 and conf_score >= 85
                else "Medium"
                if trust_score > 40 and conf_score >= 60
                else "High",
                "status": "Pending",
                "applied_at": _now_iso(),
                "decided_at": None,
                "data": farmer_data,
            }

            try:
                resp = requests.post(
                    f"{BACKEND_BASE_URL}/applications",
                    json={"application": base_record},
                    timeout=10,
                )
                if resp.status_code != 200:
                    st.error(f"Backend application save failed (HTTP {resp.status_code})")
                else:
                    payload = resp.json()
                    if not payload.get("ok"):
                        st.error(payload.get("error", "Backend save error"))
                    else:
                        st.success("Application saved to Dhāra backend. Open Dashboard for scoring outputs.")
                        # record id for later report/logging
                        try:
                            app_id = payload.get("id")
                            if app_id:
                                st.session_state["current_app_id"] = app_id
                        except Exception:
                            pass
            except Exception as e:
                st.error(f"Could not reach backend to save application: {e}")


def _require_farmer_data() -> dict | None:
    data = st.session_state.get("farmer_data") or {}
    if not data:
        st.warning("No application data found. Complete Application first.")
        return None
    if not st.session_state.get("farmer_type"):
        st.warning("No farmer type selected. Complete Application first.")
        return None
    return data


def page_dashboard() -> None:
    st.markdown("### Dashboard")
    farmer_data = _require_farmer_data()
    if farmer_data is None:
        return

    farmer_type = st.session_state["farmer_type"]
    cibil_score = st.session_state.get("cibil_score", 650)
    st.caption(f"Mode: {farmer_type}")

    ok, payload, err = _backend_post_score(farmer_data, farmer_type, cibil_score)
    if not ok or not payload:
        st.error(f"Could not fetch scores from backend: {err}")
        return

    if payload.get("warning"):
        st.warning(payload["warning"])

    conf_score = float(payload["confidence_score"])
    trust_score = float(payload["trust_score"])

    if trust_score > 70 and conf_score >= 85:
        risk_cat_display = "Low Risk / High Confidence"
        rec = "Approve full loan"
        color = "#16a34a"
    elif trust_score > 40 and conf_score >= 60:
        risk_cat_display = "Medium Risk / Moderate Confidence"
        rec = "Approve partial loan / require collateral"
        color = "#f59e0b"
    else:
        risk_cat_display = "High Risk / Low Confidence"
        rec = "Reject / manual field verification required"
        color = "#dc2626"

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Trust Score (ML)", value=f"{trust_score:.1f}/100")
    with col2:
        st.metric(label="Verification Confidence", value=f"{conf_score:.1f}/100")
    with col3:
        st.markdown(
            f"**Actionable risk status**<br/><span style='color:{color}; font-size: 20px; font-weight: 800;'>{risk_cat_display}</span>",
            unsafe_allow_html=True,
        )

    st.markdown("#### Recommendation")
    st.success(f"**{rec}**")

    # AI scoring narrative (lender-style)
    st.markdown("#### AI scoring narrative")
    narrative_list = payload.get("ai_justification", []) if isinstance(payload, dict) else []
    narrative = "\n".join(narrative_list)
    if not narrative:
        narrative = "AI narrative unavailable."
    st.code(narrative, language="text")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Profile radar")
        categories = ["Land Size", "Yield Consistency", "Soil Health", "Financial History", "Weather Resilience"]
        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=[
                    min(100, float(farmer_data["land_size"]) * 5),
                    float(farmer_data["yield_consistency_index"]) * 100,
                    float(farmer_data["soil_health_index"]),
                    80 if int(farmer_data["previous_repayment_status"]) == 1 else 20,
                    100 - abs(float(farmer_data["rainfall_deviation"])),
                ],
                theta=categories,
                fill="toself",
                name="Farmer profile",
            )
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e5e7eb"),
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(148,163,184,0.25)", tickfont=dict(color="#94a3b8")),
                angularaxis=dict(gridcolor="rgba(148,163,184,0.18)", tickfont=dict(color="#e5e7eb")),
            ),
            showlegend=False,
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("#### Profile summary")
        df_summary = pd.DataFrame(
            [
                {"Metric": "Name", "Value": farmer_data.get("name", "")},
                {"Metric": "District", "Value": farmer_data.get("district", "")},
                {"Metric": "Loan Amount", "Value": f"₹{farmer_data.get('loan_amount', '')}"},
                {"Metric": "Soil Health Index", "Value": f"{float(farmer_data.get('soil_health_index', 0)):.1f}"},
                {"Metric": "Crop", "Value": farmer_data.get("crop_name", "")},
                {"Metric": "Season", "Value": farmer_data.get("season", "")},
                {"Metric": "State", "Value": farmer_data.get("state", "")},
                {"Metric": "Crop Failures (history flag)", "Value": int(farmer_data.get("crop_failure_history", 0))},
            ]
        )
        st.table(df_summary)

        st.markdown("#### Reports")
        if st.button("Generate lender PDF report", type="primary", use_container_width=True):
            with st.spinner("Requesting report from backend..."):
                ok_rep, pdf_bytes, filename, err_rep = _backend_post_report(farmer_data, farmer_type, cibil_score)
            if not ok_rep or not pdf_bytes:
                st.error(f"Report generation failed via backend: {err_rep}")
            else:
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=filename or "DharaAI_Report.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                )


def page_simulation() -> None:
    st.markdown("### What‑If simulation")
    base_data = _require_farmer_data()
    if base_data is None:
        return

    st.caption("Adjust sliders to see how the Trust Score and Confidence Score change under stress.")
    base = dict(base_data)

    col1, col2 = st.columns(2)
    with col1:
        sim_rainfall = st.slider("Rainfall Deviation (%)", -50.0, 50.0, float(base["rainfall_deviation"]))
        sim_yield = st.slider("Yield Consistency Index", 0.0, 1.0, float(base["yield_consistency_index"]))
    with col2:
        sim_loan = st.number_input("Loan Amount (₹)", value=int(base["loan_amount"]), step=5000)
        sim_soil = st.slider("Soil Health Index", 0.0, 100.0, float(base["soil_health_index"]))

    def simulate(rf: float, yld: float, loan: float, soil: float) -> tuple[float, float]:
        sim_data = dict(base)
        sim_data["rainfall_deviation"] = rf
        sim_data["yield_consistency_index"] = yld
        sim_data["loan_amount"] = loan
        sim_data["soil_health_index"] = soil

        original_loan = float(base["loan_amount"]) if float(base["loan_amount"]) > 0 else 1.0
        sim_data["loan_to_income_ratio"] = float(base["loan_to_income_ratio"]) * (float(loan) / original_loan)

        ok, payload, err = _backend_post_score(sim_data, st.session_state["farmer_type"])
        if not ok or not payload:
            st.error(f"Simulation scoring failed via backend: {err}")
            return float("nan"), float("nan")
        if payload.get("warning"):
            st.warning(payload["warning"])
        return float(payload["trust_score"]), float(payload["confidence_score"])

    new_trust, new_conf = simulate(sim_rainfall, sim_yield, sim_loan, sim_soil)
    ok_base, base_payload, err_base = _backend_post_score(base, st.session_state["farmer_type"])
    if not ok_base or not base_payload:
        st.error(f"Base scoring failed via backend: {err_base}")
        return
    if base_payload.get("warning"):
        st.warning(base_payload["warning"])
    base_trust = float(base_payload["trust_score"])
    base_conf = float(base_payload["confidence_score"])

    c1, c2 = st.columns(2)
    c1.metric("Simulated Trust Score", f"{new_trust:.1f}", delta=f"{new_trust - base_trust:+.1f} vs base")
    c2.metric("Simulated Confidence Score", f"{new_conf:.1f}", delta=f"{new_conf - base_conf:+.1f} vs base")

    if sim_rainfall < -20:
        st.warning("High drought risk detected. Consider recommending crop insurance bundle.")
    elif sim_rainfall > 30:
        st.warning("High flood risk detected. Check historical flood exposure for the district.")


def page_model() -> None:
    st.markdown("### Model performance")
    st.caption("A compact summary of the synthetic training performance and feature importance.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Accuracy", "82.4%")
    col2.metric("Precision", "80.1%")
    col3.metric("Recall", "85.6%")

    st.markdown("---")
    st.markdown("#### Global feature importance")
    import plotly.express as px

    features = [
        "loan_to_income_ratio",
        "yield_consistency_index",
        "previous_repayment_status",
        "soil_health_index",
        "crop_failure_history",
        "district_average_yield_deviation",
        "irrigation_availability",
        "land_size",
        "avg_yield_last_3_seasons",
        "rainfall_deviation",
    ]
    importances = [0.22, 0.18, 0.15, 0.12, 0.10, 0.08, 0.06, 0.05, 0.03, 0.01]
    df_imp = pd.DataFrame({"Feature": features, "Importance": importances}).sort_values("Importance", ascending=True)
    fig = px.bar(
        df_imp,
        x="Importance",
        y="Feature",
        orientation="h",
        title="Feature Importance in Predicting Repayment",
        template="plotly_dark",
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e5e7eb"),
        xaxis=dict(gridcolor="rgba(148,163,184,0.18)", zerolinecolor="rgba(148,163,184,0.18)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.12)"),
        title_font=dict(color="#e5e7eb"),
        margin=dict(l=20, r=20, t=60, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def _apps_sorted_latest(apps: list[dict]) -> list[dict]:
    def key(a: dict):
        return a.get("applied_at") or ""

    return sorted(apps, key=key, reverse=True)


def page_admin_applications() -> None:
    st.markdown("### 📥 Applications")
    try:
        resp = requests.get(f"{BACKEND_BASE_URL}/applications", timeout=10)
        if resp.status_code != 200:
            st.error(f"Backend applications fetch failed (HTTP {resp.status_code})")
            return
        payload = resp.json()
        if not payload.get("ok"):
            st.error(payload.get("error", "Backend applications error"))
            return
        apps = payload.get("applications") or []
    except Exception as e:
        st.error(f"Could not reach backend for applications: {e}")
        return

    if not apps:
        st.info("No applications yet.")
        return

    def _status_icon(s: str) -> str:
        return "✓ Approved" if s == "Approved" else "✗ Rejected" if s == "Rejected" else "○ Pending"

    # Summary metrics
    pending = sum(1 for a in apps if (a.get("status") or "Pending") == "Pending")
    approved = sum(1 for a in apps if a.get("status") == "Approved")
    rejected = sum(1 for a in apps if a.get("status") == "Rejected")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total", len(apps))
    m2.metric("○ Pending", pending)
    m3.metric("✓ Approved", approved)
    m4.metric("✗ Rejected", rejected)
    st.markdown("---")

    st.markdown("#### Applications (latest first)")
    df = pd.DataFrame(
        [
            {
                "ID": a.get("id"),
                "Farmer": a.get("farmer_name"),
                "District": a.get("district"),
                "Loan (₹)": f"{int(a.get('loan_amount') or 0):,}",
                "Trust": round(float(a.get("trust_score", 0)), 1),
                "Risk": a.get("risk_status"),
                "Status": _status_icon(a.get("status") or "Pending"),
            }
            for a in apps
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### Review & Decide")
    for app in apps:
        status = app.get("status") or "Pending"
        icon = _status_icon(status)
        with st.expander(
            f"**#{app.get('id')}** {app.get('farmer_name')} · ₹{int(app.get('loan_amount') or 0):,} · {icon}",
            expanded=False,
        ):
            left, right = st.columns([1.5, 1])
            with left:
                st.markdown(f"**{app.get('district')}** / {app.get('state')} · {app.get('crop_name')} ({app.get('season')})")
                st.caption(f"Applied {(app.get('applied_at') or '')[:16]} · Trust {float(app.get('trust_score', 0)):.1f} / Conf {float(app.get('conf_score', 0)):.1f}")
                data = app.get("data") or {}
                if data:
                    st.caption(f"Area {data.get('area_hectares')} ha · Yield {data.get('yield_value')} t/ha · Rainfall {data.get('annual_rainfall_mm')} mm")

            with right:
                st.markdown("**Decision tools**")
                req_amt = float(app.get("loan_amount") or 0)
                approved_amt = st.number_input(
                    "Approved amount (₹)",
                    min_value=0.0,
                    max_value=req_amt,
                    value=float(app.get("approved_amount") or req_amt),
                    step=5000.0,
                    key=f"approved_amt_{app.get('id')}",
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Approve", type="primary", use_container_width=True, key=f"approve_{app.get('id')}"):
                        try:
                            resp = requests.post(
                                f"{BACKEND_BASE_URL}/applications/{app.get('id')}/decision",
                                json={"status": "Approved", "approved_amount": float(approved_amt)},
                                timeout=10,
                            )
                            if resp.status_code != 200:
                                st.error(f"Backend decision failed (HTTP {resp.status_code})")
                            else:
                                payload = resp.json()
                                if not payload.get("ok"):
                                    st.error(payload.get("error", "Backend decision error"))
                                else:
                                    st.success("Approved via Dhāra backend.")
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Could not reach backend to approve: {e}")
                with c2:
                    if st.button("Reject", type="secondary", use_container_width=True, key=f"reject_{app.get('id')}"):
                        try:
                            resp = requests.post(
                                f"{BACKEND_BASE_URL}/applications/{app.get('id')}/decision",
                                json={"status": "Rejected", "approved_amount": 0.0},
                                timeout=10,
                            )
                            if resp.status_code != 200:
                                st.error(f"Backend decision failed (HTTP {resp.status_code})")
                            else:
                                payload = resp.json()
                                if not payload.get("ok"):
                                    st.error(payload.get("error", "Backend decision error"))
                                else:
                                    st.warning("Rejected via Dhāra backend.")
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Could not reach backend to reject: {e}")


def page_admin_notifications() -> None:
    st.markdown("### Admin — Notifications")
    try:
        resp = requests.get(f"{BACKEND_BASE_URL}/notifications", timeout=10)
        if resp.status_code != 200:
            st.error(f"Backend notifications fetch failed (HTTP {resp.status_code})")
            return
        payload = resp.json()
        if not payload.get("ok"):
            st.error(payload.get("error", "Backend notifications error"))
            return
        notifs = payload.get("notifications") or []
    except Exception as e:
        st.error(f"Could not reach backend for notifications: {e}")
        return

    if not notifs:
        st.info("No notifications yet.")
        return

    for n in notifs:
        ts = (n.get("ts") or "")[:19]
        kind = n.get("kind") or "event"
        msg = n.get("message") or ""
        st.markdown(f"**{ts} UTC** — `{kind}`  \n{msg}")


def page_admin_reports() -> None:
    st.markdown("### 📄 Reports")
    try:
        resp = requests.get(f"{BACKEND_BASE_URL}/applications", timeout=10)
        if resp.status_code != 200:
            st.error(f"Backend applications fetch failed (HTTP {resp.status_code})")
            return
        payload = resp.json()
        if not payload.get("ok"):
            st.error(payload.get("error", "Backend applications error"))
            return
        apps = payload.get("applications") or []
    except Exception as e:
        st.error(f"Could not reach backend for applications: {e}")
        return

    if not apps:
        st.info("No applications to report yet.")
        return

    st.markdown("#### Portfolio exports")
    df = pd.DataFrame(apps)
    st.download_button(
        "Download portfolio CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="dhara_portfolio.csv",
        mime="text/csv",
        use_container_width=True,
    )

    if st.button("Generate portfolio PDF (lender)", type="primary", use_container_width=True):
        with st.spinner("Requesting portfolio report from backend..."):
            ok, pdf_bytes, filename, err = _backend_post_portfolio_report(apps)
        if not ok or not pdf_bytes:
            st.error(f"Portfolio report failed: {err}")
        else:
            st.download_button(
                "Download portfolio PDF",
                data=pdf_bytes,
                file_name=filename or "DharaAI_Portfolio_Report.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

    st.markdown("---")
    st.markdown("#### Individual farmer dossier PDFs")
    apps = _apps_sorted_latest(apps)
    for a in apps:
        with st.expander(f"[{a.get('id')}] {a.get('farmer_name')} — {a.get('district')} ({a.get('status')})", expanded=False):
            if st.button("Generate PDF", key=f"pdf_{a.get('id')}", use_container_width=True):
                with st.spinner("Generating PDF via backend..."):
                    ok_rep, pdf_bytes, filename, err_rep = _backend_post_report(a.get("data") or {}, a.get("farmer_type") or "New Farmer")
                if not ok_rep or not pdf_bytes:
                    st.error(err_rep)
                else:
                    st.download_button(
                        "Download PDF",
                        data=pdf_bytes,
                        file_name=filename or f"DharaAI_Report_{a.get('id')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )


def _check_backend() -> bool:
    """Return True if backend is reachable."""
    try:
        r = requests.get(f"{BACKEND_BASE_URL}/health", timeout=3)
        return r.status_code == 200 and (r.json() or {}).get("ok")
    except Exception:
        return False


def page_admin_users() -> None:
    st.markdown("### 👤 User Management")
    st.caption("All registered users in the system.")
    if not _check_backend():
        st.warning(f"⚠️ Backend not reachable at {BACKEND_BASE_URL}. Start it: `python backend\\app.py`")

    try:
        resp = requests.get(
            f"{BACKEND_BASE_URL}/auth/users",
            params={"admin_key": "dhara_admin_demo"},
            timeout=8,
        )
        if resp.status_code == 200:
            payload = resp.json()
            if payload.get("ok"):
                users = payload.get("users", [])
                count = payload.get("count", 0)
                
                st.metric("Total Registered Users", count)
                
                if users:
                    st.markdown("---")
                    st.markdown("#### User List")
                    
                    # Create a readable table
                    user_data = []
                    for user in users:
                        user_data.append({
                            "Username": user.get("username"),
                            "Full Name": user.get("full_name"),
                            "Role": user.get("role"),
                            "Phone": user.get("phone") or "—",
                            "Created": (user.get("created_at") or "")[:10],
                        })
                    
                    df_users = pd.DataFrame(user_data)
                    st.dataframe(df_users, use_container_width=True, hide_index=True)
                else:
                    st.info("No users registered yet. Create accounts from the Sign up tab on the login page.")
            else:
                st.error(payload.get("error", "Could not fetch users."))
        else:
            try:
                err = resp.json().get("error", "")
                st.error(err or f"Backend error (HTTP {resp.status_code}). Ensure backend is running.")
            except Exception:
                st.error(f"Backend error (HTTP {resp.status_code}). Is backend running at {BACKEND_BASE_URL}?")
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot reach backend at {BACKEND_BASE_URL}. Start it with: python backend\\app.py")
    except Exception as e:
        st.error(f"Could not reach backend: {e}")


def page_admin_logs() -> None:
    """Combined page: Score Logs, Report Logs, Notifications."""
    st.markdown("### 📋 Logs & Notifications")
    t1, t2, t3 = st.tabs(["Score Logs", "Report Logs", "Notifications"])
    with t1:
        st.caption("Credit scoring requests.")
        try:
            resp = requests.get(f"{BACKEND_BASE_URL}/score-logs", timeout=10)
            if resp.status_code == 200:
                logs = resp.json().get("logs", [])
                if logs:
                    st.dataframe(pd.DataFrame(logs), use_container_width=True)
                else:
                    st.info("No score logs yet.")
            else:
                st.error(f"Error (HTTP {resp.status_code})")
        except Exception as e:
            st.error(str(e))
    with t2:
        st.caption("PDF report generation history.")
        try:
            resp = requests.get(f"{BACKEND_BASE_URL}/report-logs", timeout=10)
            if resp.status_code == 200:
                logs = resp.json().get("logs", [])
                if logs:
                    st.dataframe(pd.DataFrame(logs), use_container_width=True)
                else:
                    st.info("No report logs yet.")
            else:
                st.error(f"Error (HTTP {resp.status_code})")
        except Exception as e:
            st.error(str(e))
    with t3:
        st.caption("System event notifications.")
        try:
            resp = requests.get(f"{BACKEND_BASE_URL}/notifications", timeout=10)
            if resp.status_code == 200:
                notifs = resp.json().get("notifications", [])
                if notifs:
                    for n in notifs:
                        ts = (n.get("ts") or "")[:19]
                        st.markdown(f"**{ts}** — `{n.get('kind', '')}` {n.get('message', '')}")
                else:
                    st.info("No notifications yet.")
            else:
                st.error(f"Error (HTTP {resp.status_code})")
        except Exception as e:
            st.error(str(e))


def page_admin_data_browser() -> None:
    """Comprehensive view of all stored database records with relationships."""
    st.markdown("### 🗄️ Data Browser")
    st.caption(
        "View all users, applications, scoring logs, reports, and notifications stored in the database. "
        "All data points are connected and traceable."
    )
    if not _check_backend():
        st.warning(f"⚠️ Backend not reachable at {BACKEND_BASE_URL}. Start it: `python backend\\app.py`")

    try:
        resp = requests.get(
            f"{BACKEND_BASE_URL}/data-export",
            params={"admin_key": "dhara_admin_demo"},
            timeout=15,
        )
        if resp.status_code != 200:
            try:
                err = resp.json().get("error", "")
                st.error(err or f"Backend error (HTTP {resp.status_code}). Ensure backend is running.")
            except Exception:
                st.error(f"Backend error (HTTP {resp.status_code}). Is backend at {BACKEND_BASE_URL}? Run: python backend\\app.py")
            return

        payload = resp.json()
        if not payload.get("ok"):
            st.error(payload.get("error", "Could not fetch data"))
            return

        summary = payload.get("summary", {})

        # overview metrics
        st.markdown("#### 📊 Database Overview")
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        mc1.metric("Total Users", summary.get("total_users", 0))
        mc2.metric("Applications", summary.get("total_applications", 0))
        mc3.metric("Scoring Events", summary.get("total_scores_logged", 0))
        mc4.metric("Reports Generated", summary.get("total_reports_generated", 0))
        mc5.metric("Notifications", summary.get("total_notifications", 0))

        st.markdown("---")

        # tabs for each data category
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            ["Users", "Applications", "Scoring", "Reports", "Notifications", "Analytics"]
        )

        # 1. Users
        with tab1:
            st.markdown("#### Registered Users")
            users = payload.get("users", [])
            if users:
                user_data = []
                for u in users:
                    user_data.append({
                        "ID": u.get("id"),
                        "Username": u.get("username"),
                        "Name": u.get("full_name"),
                        "Role": u.get("role"),
                        "Phone": u.get("phone") or "—",
                        "Joined": (u.get("created_at") or "")[:10],
                    })
                df_users = pd.DataFrame(user_data)
                st.dataframe(df_users, use_container_width=True, hide_index=True)
            else:
                st.info("No users registered. Create accounts from the Sign up tab on the login page.")

        # 2. Applications
        with tab2:
            st.markdown("#### Loan Applications with Linked Data")
            apps = payload.get("applications_with_relations", [])
            if apps:
                for app_rec in apps:
                    app = app_rec.get("app", {})
                    scores = app_rec.get("scores", [])
                    reports = app_rec.get("reports", [])
                    notifs = app_rec.get("notifications", [])

                    with st.expander(
                        f"**App #{app.get('id')}** — {app.get('farmer_name')} ({app.get('district')})",
                        expanded=False,
                    ):
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Loan Requested", f"₹{app.get('loan_amount', 0):.0f}")
                        col2.metric("Trust Score", f"{app.get('trust_score', 0):.1f}")
                        col3.metric("Status", app.get("status", "?"))

                        st.markdown("**Application Details**")
                        app_detail = {
                            "Farmer": app.get("farmer_name"),
                            "Type": app.get("farmer_type"),
                            "Crop": app.get("crop_name"),
                            "Season": app.get("season"),
                            "State": app.get("state"),
                            "Applied": (app.get("applied_at") or "")[:10],
                            "Risk": app.get("risk_status"),
                            "Conf. Score": f"{app.get('conf_score', 0):.1f}",
                        }
                        st.json(app_detail)

                        if scores:
                            st.markdown("**Linked Scoring Events**")
                            score_data = []
                            for s in scores:
                                score_data.append({
                                    "ID": s.get("id"),
                                    "Timestamp": (s.get("ts") or "")[:19],
                                    "CIBIL": s.get("cibil_score"),
                                    "Trust": f"{s.get('trust_score', 0):.1f}",
                                    "Confidence": f"{s.get('conf_score', 0):.1f}",
                                    "Decision": s.get("loan_decision", "—"),
                                })
                            df_scores = pd.DataFrame(score_data)
                            st.dataframe(df_scores, use_container_width=True, hide_index=True)

                        if reports:
                            st.markdown("**Linked Report Generations**")
                            report_data = []
                            for r in reports:
                                report_data.append({
                                    "ID": r.get("id"),
                                    "Generated": (r.get("ts") or "")[:19],
                                    "PDF": r.get("pdf_path", "—"),
                                    "Trust": f"{r.get('trust_score', 0):.1f}",
                                    "Risk": r.get("risk_status", "—"),
                                })
                            df_reports = pd.DataFrame(report_data)
                            st.dataframe(df_reports, use_container_width=True, hide_index=True)

                        if notifs:
                            st.markdown("**Notifications**")
                            for n in notifs:
                                st.info(f"*{(n.get('ts') or '')[:19]}* — {n.get('message')}")
            else:
                st.info("No applications submitted yet.")

        # 3. Scoring Events
        with tab3:
            st.markdown("#### All Scoring Events (Audit Log)")
            scores = payload.get("score_logs_count", 0)
            st.caption(f"Total scoring requests: {scores}")

            try:
                resp2 = requests.get(f"{BACKEND_BASE_URL}/score-logs", timeout=10)
                if resp2.status_code == 200:
                    pl = resp2.json()
                    logs = pl.get("logs", [])
                    if logs:
                        df_scores = pd.DataFrame(logs)
                        # simplify display
                        display_cols = ["id", "ts", "farmer_username", "farmer_type", "trust_score", "conf_score", "risk_status"]
                        cols_to_show = [c for c in display_cols if c in df_scores.columns]
                        st.dataframe(df_scores[cols_to_show], use_container_width=True, hide_index=True)
                    else:
                        st.info("No scoring logs.")
            except Exception as e:
                st.error(f"Could not fetch scoring details: {e}")

        # 4. Reports
        with tab4:
            st.markdown("#### Generated Reports")
            reports_count = payload.get("report_logs_count", 0)
            st.caption(f"Total reports generated: {reports_count}")

            try:
                resp3 = requests.get(f"{BACKEND_BASE_URL}/report-logs", timeout=10)
                if resp3.status_code == 200:
                    pl = resp3.json()
                    logs = pl.get("logs", [])
                    if logs:
                        df_reports = pd.DataFrame(logs)
                        display_cols = ["id", "ts", "farmer_username", "pdf_path", "trust_score", "risk_status"]
                        cols_to_show = [c for c in display_cols if c in df_reports.columns]
                        st.dataframe(df_reports[cols_to_show], use_container_width=True, hide_index=True)
                    else:
                        st.info("No report logs.")
            except Exception as e:
                st.error(f"Could not fetch report details: {e}")

        # 5. Notifications
        with tab5:
            st.markdown("#### System Notifications")
            notifs_count = payload.get("notifications_count", 0)
            st.caption(f"Total notifications: {notifs_count}")

            try:
                app_ids = [a.get("id") for a in payload.get("applications_with_relations", [])]
                all_notifs = []
                for app_rec in payload.get("applications_with_relations", []):
                    all_notifs.extend(app_rec.get("notifications", []))

                if all_notifs:
                    notif_data = []
                    for n in all_notifs:
                        notif_data.append({
                            "ID": n.get("id"),
                            "Timestamp": (n.get("ts") or "")[:19],
                            "Type": n.get("kind"),
                            "Message": n.get("message"),
                            "App": n.get("app_id", "—"),
                        })
                    df_notifs = pd.DataFrame(notif_data)
                    st.dataframe(df_notifs, use_container_width=True, hide_index=True)
                else:
                    st.info("No notifications.")
            except Exception as e:
                st.error(f"Could not fetch notifications: {e}")

        # 6. Analytics
        with tab6:
            st.markdown("#### Analytics")
            apps_list = [r.get("app", {}) for r in payload.get("applications_with_relations", [])]
            if apps_list:
                import plotly.express as px
                df = pd.DataFrame([{
                    "id": a.get("id"), "applied_at": (a.get("applied_at") or "")[:10],
                    "status": a.get("status"), "risk": a.get("risk_status"),
                    "loan_amount": float(a.get("loan_amount") or 0),
                    "approved_amount": float(a.get("approved_amount") or 0),
                    "trust": float(a.get("trust_score") or 0), "confidence": float(a.get("conf_score") or 0),
                } for a in apps_list])
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Applications", len(df))
                c2.metric("Approval rate", f"{(df['status'] == 'Approved').mean() * 100:.1f}%")
                c3.metric("Total requested", f"₹{int(df['loan_amount'].sum()):,}")
                c4.metric("Total approved", f"₹{int(df.loc[df['status'] == 'Approved', 'approved_amount'].sum()):,}")
                g1, g2 = st.columns(2)
                with g1:
                    fig = px.pie(df, names="status", title="Status", template="plotly_dark")
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)
                with g2:
                    fig2 = px.bar(df.groupby("risk", as_index=False).size(), x="risk", y="size", title="Risk", template="plotly_dark")
                    fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No applications yet. Submit applications to see analytics.")

        st.markdown("---")
        st.markdown("#### Data Relationships")
        st.markdown("""
        **How data points are connected:**
        
        1. **Users** — Registered farmer or admin accounts with secure login
        2. **Applications** — Loan requests submitted by farmers; each has farmer_username link
        3. **Scoring Events** — Triggered each time `/score` is called; linked by farmer_username
        4. **Reports** — PDF files generated for each application; linked by app_id
        5. **Notifications** — System messages triggered by application events; linked by app_id
        
        **Data flow:**
        - User registers → User created in `users` table
        - Farmer submits application → Application saved with user info + full farmer data JSON
        - Scoring requested → Score logged with farmer details + scores + risk assessment
        - Report generated → Report logged with app_id + PDF path + scores
        - Notification triggered → Notification created and linked to application
        
        All timestamps (ISO format) allow tracking of when each event occurred.
        """)

    except requests.exceptions.ConnectionError:
        st.error(f"Cannot reach backend at {BACKEND_BASE_URL}. Start it: python backend\\app.py")
    except Exception as e:
        st.error(f"Error loading data browser: {e}")


_init_state()

if not st.session_state.get("logged_in"):
    # Premium full-page landing before login
    landing_fullscreen_header()
    hero_section()

    cta1, cta2, cta3 = st.columns([1.2, 1.2, 1.6])
    with cta1:
        if st.button("Continue to secure login", type="primary", use_container_width=True):
            st.session_state["public_view"] = "auth"
            st.rerun()
    with cta2:
        if st.button("Create account", type="secondary", use_container_width=True):
            st.session_state["public_view"] = "auth"
            st.rerun()
    with cta3:
        st.caption("No database login. Session-only accounts for demo and hackathon use.")

    if st.session_state.get("public_view") == "auth":
        section_divider()
        page_auth()
else:
    u = st.session_state["auth_user"]
    if u and u.get("role") == "Admin":
        items = ["Home", "Apps", "Users", "Data", "Logs", "Reports", "Model", "Logout"]
        icons = ["house", "inboxes", "people", "database", "journal-text", "file-earmark-pdf", "cpu", "box-arrow-right"]
    else:
        items = ["Overview", "Application", "Dashboard", "Simulation", "Model", "Logout"]
        icons = ["house", "clipboard-check", "bar-chart", "activity", "cpu", "box-arrow-right"]
    nav = _top_nav(items, icons, default_index=0)
    if u and u.get("role") == "Admin":
        if nav == "Home":
            page_overview()
        elif nav == "Apps":
            page_admin_applications()
        elif nav == "Users":
            page_admin_users()
        elif nav == "Data":
            page_admin_data_browser()
        elif nav == "Logs":
            page_admin_logs()
        elif nav == "Reports":
            page_admin_reports()
        elif nav == "Model":
            page_model()
        else:
            _logout()
    else:
        if nav == "Overview":
            page_overview()
        elif nav == "Application":
            page_application()
        elif nav == "Dashboard":
            page_dashboard()
        elif nav == "Simulation":
            page_simulation()
        elif nav == "Model":
            page_model()
        else:
            _logout()
