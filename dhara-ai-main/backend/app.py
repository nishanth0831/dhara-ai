from __future__ import annotations

import os
import sys
from typing import Any, Dict

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import csv


# Allow importing your existing project modules from repo root
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.db import (  # noqa: E402
    init_db,
    insert_admin_audit_log,
    insert_notification,
    link_score_to_application,
    list_applications,
    list_notifications,
    save_application,
    update_decision,
)
from services.auth_service import create_user, authenticate, get_user_by_username, list_all_users, init_user_store  # noqa: E402
from verification.engine import run_verification  # noqa: E402
from services.model_service import predict_credit_risk  # noqa: E402
from services.weather_service import fetch_weather_analysis  # noqa: E402
from services.report_generator import generate_lender_report # noqa: E402
from reports.pdf_generator import generate_pdf_report  # noqa: E402
from reports.portfolio_report import generate_portfolio_report  # noqa: E402


app = Flask(__name__)
CORS(app)
init_db()


def _risk_and_reco(trust_score: float, conf_score: float) -> Dict[str, Any]:
    if trust_score > 70 and conf_score >= 85:
        return {
            "risk_status": "Low Risk / High Confidence",
            "recommendation": "Approve full loan",
        }
    if trust_score > 40 and conf_score >= 60:
        return {
            "risk_status": "Medium Risk / Moderate Confidence",
            "recommendation": "Approve partial loan / require collateral",
        }
    return {
        "risk_status": "High Risk / Low Confidence",
        "recommendation": "Reject / manual field verification required",
    }


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "dhara-backend"})


@app.post("/auth/register")
def register():
    """Register a new user in the database."""
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "").strip()
    full_name = payload.get("full_name", "").strip()
    phone = payload.get("phone", "").strip()
    role = payload.get("role", "Farmer").strip()
    password = payload.get("password", "")

    if not username or not full_name or not password:
        return jsonify({"ok": False, "error": "username, full_name, and password are required"}), 400

    # Create user in database (store is just for fallback)
    store = init_user_store()
    ok, msg = create_user(store, username, full_name, phone, role, password)
    
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400

    return jsonify({"ok": True, "message": msg})


@app.post("/auth/login")
def login():
    """Authenticate a user and return user info."""
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "").strip()
    password = payload.get("password", "")

    if not username or not password:
        return jsonify({"ok": False, "error": "username and password are required"}), 400

    store = init_user_store()
    ok, user, msg = authenticate(store, username, password)
    
    if not ok:
        return jsonify({"ok": False, "error": msg}), 401

    return jsonify({
        "ok": True,
        "user": user
    })


@app.get("/auth/user/<username>")
def get_user(username: str):
    """Fetch user info by username."""
    user = get_user_by_username(username)
    if not user:
        return jsonify({"ok": False, "error": "User not found"}), 404

    return jsonify({"ok": True, "user": user})


@app.get("/auth/users")
def list_users():
    """List all users (admin endpoint)."""
    admin_key = request.args.get("admin_key", "")
    # SECURITY NOTE: In production, use proper auth. For demo, use a simple key.
    if admin_key != "dhara_admin_demo":
        try:
            insert_admin_audit_log("/auth/users", success=False)
        except Exception:
            pass
        return jsonify({"ok": False, "error": "Unauthorized"}), 403

    try:
        insert_admin_audit_log("/auth/users", success=True)
    except Exception:
        pass
    users = list_all_users()
    return jsonify({"ok": True, "users": users, "count": len(users)})


@app.get("/weather")
def weather():
    district = (request.args.get("district") or "").strip()
    state = (request.args.get("state") or "").strip()
    if not district or not state:
        return jsonify({"ok": False, "error": "district and state are required"}), 400

    ok, data, msg = fetch_weather_analysis(district, state)
    if not ok:
        return jsonify({"ok": False, "error": msg}), 502
    return jsonify({"ok": True, "data": data})


@app.post("/score")
def score():
    payload = request.get_json(silent=True) or {}
    farmer_data = payload.get("farmer_data") or {}
    farmer_type = payload.get("farmer_type") or "New Farmer"
    cibil_score = int(payload.get("cibil_score", 650)) # Default to 650 if missing
    
    if not isinstance(farmer_data, dict):
        return jsonify({"ok": False, "error": "farmer_data must be an object"}), 400

    ver = run_verification(farmer_data, farmer_type)
    conf_score = float(ver["confidence_score"])
    
    # New ML Prediction Logic
    prediction = predict_credit_risk(farmer_data, cibil_score)
    trust_score = float(prediction.get("trust_score", 0))
    model_available = bool(prediction.get("model_available", False))
    
    # Generate the AI Justification summary for the dashboard
    from services.report_generator import generate_justification
    justification = generate_justification(farmer_data, cibil_score, trust_score)

    resp = {
            "ok": True,
            "trust_score": trust_score,
            "confidence_score": conf_score,
            "risk_status": prediction.get("risk_level"),
            "recommendation": prediction.get("loan_decision"),
            "penalties_breakdown": ver.get("penalties_breakdown", {}),
            "ai_justification": justification,
        }
    if not model_available:
        resp["warning"] = "Model file not available; using default fallback score."

    # log the scoring request
    try:
        from backend.db import save_score_log
        # optionally include user if provided in payload
        usr = payload.get("username") or None
        app_id = payload.get("app_id")
        save_score_log(
            farmer_username=usr,
            farmer_type=farmer_type,
            app_id=app_id,
            cibil_score=cibil_score,
            farmer_data=farmer_data,
            trust_score=trust_score,
            conf_score=conf_score,
            risk_status=prediction.get("risk_level"),
            loan_decision=prediction.get("loan_decision"),
            model_available=model_available,
        )
    except Exception:
        pass

    return jsonify(resp)


@app.post("/report")
def report():
    payload = request.get_json(silent=True) or {}
    farmer_data = payload.get("farmer_data") or {}
    farmer_type = payload.get("farmer_type") or "New Farmer"
    cibil_score = int(payload.get("cibil_score", 650))
    if not isinstance(farmer_data, dict):
        return jsonify({"ok": False, "error": "farmer_data must be an object"}), 400

    ver = run_verification(farmer_data, farmer_type)
    conf_score = float(ver["confidence_score"])
    
    prediction = predict_credit_risk(farmer_data, cibil_score)
    trust_score = float(prediction.get("trust_score", 0))
    model_available = bool(prediction.get("model_available", False))

    pdf_path = generate_pdf_report(
        farmer_data=farmer_data,
        trust_score=trust_score,
        confidence_score=conf_score,
        risk_status=prediction.get("risk_level"),
        penalties_breakdown=ver.get("penalties_breakdown", {}),
        model_available=model_available,
    )
    # log the report generation
    try:
        from backend.db import save_report_log
        usr = payload.get("username") or None
        # try to extract app_id if passed
        app_id = payload.get("app_id")
        save_report_log(
            farmer_username=usr,
            app_id=app_id,
            pdf_path=pdf_path,
            trust_score=trust_score,
            conf_score=conf_score,
            risk_status=prediction.get("risk_level"),
            model_available=model_available,
        )
    except Exception:
        pass

    return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path), mimetype="application/pdf")


@app.post("/portfolio-report")
def portfolio_report():
    payload = request.get_json(silent=True) or {}
    applications = payload.get("applications") or []
    if not isinstance(applications, list):
        return jsonify({"ok": False, "error": "applications must be a list"}), 400

    pdf_path = generate_portfolio_report(applications)
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=os.path.basename(pdf_path),
        mimetype="application/pdf",
    )


@app.get("/score-logs")
def get_score_logs():
    """Return recent score log entries (admin)."""
    logs = []
    try:
        from backend.db import list_score_logs
        logs = list_score_logs(limit=500)
    except Exception:
        pass
    return jsonify({"ok": True, "logs": logs})


@app.get("/report-logs")
def get_report_logs():
    """Return recent report generation log entries (admin)."""
    logs = []
    try:
        from backend.db import list_report_logs
        logs = list_report_logs(limit=500)
    except Exception:
        pass
    return jsonify({"ok": True, "logs": logs})


@app.post("/applications")
def create_application():
    payload = request.get_json(silent=True) or {}
    app_dict = payload.get("application") or {}
    if not isinstance(app_dict, dict):
        return jsonify({"ok": False, "error": "application must be an object"}), 400

    app_id = save_application(app_dict)
    # Link the most recent score log for this farmer to this application (from submit flow)
    link_score_to_application(
        app_id,
        app_dict.get("farmer_username"),
        app_dict.get("farmer_type"),
    )
    insert_notification(
        "application_submitted",
        f"New application submitted by {app_dict.get('farmer_name')} ({app_dict.get('district')}, {app_dict.get('state')}).",
        app_id=app_id,
    )
    return jsonify({"ok": True, "id": app_id})


@app.get("/applications")
def get_applications():
    apps = list_applications()
    return jsonify({"ok": True, "applications": apps})


@app.post("/applications/<int:app_id>/decision")
def decide_application(app_id: int):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    approved_amount = data.get("approved_amount")
    if status not in {"Approved", "Rejected", "Pending"}:
        return jsonify({"ok": False, "error": "status must be Approved/Rejected/Pending"}), 400

    update_decision(app_id, status, approved_amount)

    if status == "Approved":
        msg = f"Approved application #{app_id} (₹{int(float(approved_amount or 0)):,})."
        kind = "approved"
    elif status == "Rejected":
        msg = f"Rejected application #{app_id}."
        kind = "rejected"
    else:
        msg = f"Application #{app_id} updated."
        kind = "application_updated"

    insert_notification(kind, msg, app_id=app_id)
    return jsonify({"ok": True})


@app.get("/notifications")
def get_notifications():
    notifs = list_notifications()
    return jsonify({"ok": True, "notifications": notifs})


def _load_csv_rows(path: str) -> list[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(r) for r in reader]


@app.get("/verify_soil_report")
def verify_soil_report():
    """
    Verifies a soil report against:
    - soil_report_registry.csv
    - approved_labs.csv

    CSV structure (from Dhāra AI soil registry):
      soil_report_registry.csv:
        Report_ID,Lab_ID,Farmer_ID,Issue_Date,Soil_pH,Nitrogen_kg_per_ha,Phosphorus_kg_per_ha,Potassium_kg_per_ha
      approved_labs.csv:
        Lab_ID,Lab_Name,State_Code,District_Code,Accreditation_Status
    """
    report_id = (request.args.get("report_id") or "").strip()
    if not report_id:
        return jsonify({"ok": False, "error": "report_id is required"}), 400

    data_dir = os.path.join(PROJECT_ROOT, "data")
    labs_path = os.path.join(data_dir, "approved_labs.csv")
    reports_path = os.path.join(data_dir, "soil_report_registry.csv")

    soil_reports = _load_csv_rows(reports_path)
    labs = _load_csv_rows(labs_path)

    # 1) Check if Report_ID exists
    report_row = next((r for r in soil_reports if (r.get("Report_ID") or "").strip() == report_id), None)
    if not report_row:
        return jsonify(
            {
                "ok": True,
                "report_status": "Invalid",
                "lab_verified": "No",
                "district_match": "No",
                "confidence_level": "Low",
                "details": {"reason": "Report ID not found in registry."},
            }
        )

    rep_lab_id = (report_row.get("Lab_ID") or "").strip()

    # Extract state/district codes from Report_ID (SHC-<STATE>-<DIST>-YYYY-XXXXXX)
    parts = report_id.split("-")
    rep_state_code = parts[1] if len(parts) >= 3 else ""
    rep_district_code = parts[2] if len(parts) >= 3 else ""

    # 2) Check associated Lab_ID
    lab_row = next((l for l in labs if (l.get("Lab_ID") or "").strip() == rep_lab_id), None)
    if not lab_row:
        return jsonify(
            {
                "ok": True,
                "report_status": "Valid",
                "lab_verified": "No",
                "district_match": "Unknown",
                "confidence_level": "Medium",
                "details": {
                    "reason": "Report exists, but lab is not in approved labs registry.",
                    "report": report_row,
                },
            }
        )

    lab_state_code = (lab_row.get("State_Code") or "").strip()
    lab_district_code = (lab_row.get("District_Code") or "").strip()
    accreditation = (lab_row.get("Accreditation_Status") or "").strip().lower()

    state_match = lab_state_code == rep_state_code != ""
    district_match_bool = lab_district_code == rep_district_code != ""
    district_match = "Yes" if state_match and district_match_bool else "Mismatch"

    lab_verified = "Yes" if accreditation == "active" else "No"
    # Confidence is high only if lab is active and codes match
    confidence_level = "High" if (lab_verified == "Yes" and district_match == "Yes") else "Medium"

    details = {
        "report": report_row,
        "lab": lab_row,
        "soil_metrics": {
            "Soil_pH": report_row.get("Soil_pH"),
            "Nitrogen_kg_per_ha": report_row.get("Nitrogen_kg_per_ha"),
            "Phosphorus_kg_per_ha": report_row.get("Phosphorus_kg_per_ha"),
            "Potassium_kg_per_ha": report_row.get("Potassium_kg_per_ha"),
        },
    }

    return jsonify(
        {
            "ok": True,
            "report_status": "Valid",
            "lab_verified": lab_verified,
            "district_match": district_match,
            "confidence_level": confidence_level,
            "details": details,
        }
    )


@app.get("/data-export")
def data_export():
    """Export all database records for admin view/analysis.
    Returns: users, applications (with related scores/reports), notifications.
    """
    admin_key = request.args.get("admin_key", "")
    if admin_key != "dhara_admin_demo":
        try:
            insert_admin_audit_log("/data-export", success=False)
        except Exception:
            pass
        return jsonify({"ok": False, "error": "Unauthorized"}), 403

    try:
        insert_admin_audit_log("/data-export", success=True)
    except Exception:
        pass

    try:
        from backend.db import (
            list_admin_audit_logs,
            list_applications,
            list_notifications,
            list_report_logs,
            list_score_logs,
        )
    except ImportError:
        from db import (
            list_admin_audit_logs,
            list_applications,
            list_notifications,
            list_report_logs,
            list_score_logs,
        )

    # list_all_users comes from auth_service (already imported at top)
    users = list_all_users()
    apps = list_applications()
    notifs = list_notifications(limit=1000)
    scores = list_score_logs(limit=1000)
    reports = list_report_logs(limit=1000)

    # build relationship map: app_id -> scores and reports
    app_map = {}
    for app in apps:
        app_id = app.get("id")
        app_map[app_id] = {
            "app": app,
            "scores": [],
            "reports": [],
            "notifications": [],
        }

    # link scores to apps: by app_id when present, else by farmer_username + farmer_type
    for score in scores:
        sid = score.get("app_id")
        if sid and sid in app_map:
            app_map[sid]["scores"].append(score)
        else:
            for app in apps:
                if (score.get("farmer_username") == app.get("farmer_username")
                    and score.get("farmer_type") == app.get("farmer_type")):
                    aid = app.get("id")
                    if aid in app_map:
                        app_map[aid]["scores"].append(score)
                    break

    # link reports to apps
    for report in reports:
        app_id = report.get("app_id")
        if app_id and app_id in app_map:
            app_map[app_id]["reports"].append(report)

    # link notifications to apps
    for notif in notifs:
        app_id = notif.get("app_id")
        if app_id and app_id in app_map:
            app_map[app_id]["notifications"].append(notif)

    admin_logs = list_admin_audit_logs(limit=500)

    return jsonify({
        "ok": True,
        "users": users,
        "admin_audit_logs": admin_logs,
        "applications_count": len(apps),
        "applications_with_relations": list(app_map.values()),
        "score_logs_count": len(scores),
        "report_logs_count": len(reports),
        "notifications_count": len(notifs),
        "summary": {
            "total_users": len(users),
            "total_applications": len(apps),
            "total_scores_logged": len(scores),
            "total_reports_generated": len(reports),
            "total_notifications": len(notifs),
            "admin_audit_entries": len(admin_logs),
        },
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)

