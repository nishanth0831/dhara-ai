from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "dhara.db")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        cur = conn.cursor()

        # Users table (for future auth persistence)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                phone TEXT,
                role TEXT NOT NULL,
                password_salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        # Applications table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer_username TEXT,
                farmer_name TEXT,
                farmer_type TEXT,
                district TEXT,
                state TEXT,
                crop_name TEXT,
                season TEXT,
                loan_amount REAL,
                approved_amount REAL,
                trust_score REAL,
                conf_score REAL,
                risk_status TEXT,
                status TEXT,
                applied_at TEXT,
                decided_at TEXT,
                raw_payload_json TEXT
            )
            """
        )

        # Notifications table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                kind TEXT NOT NULL,
                message TEXT NOT NULL,
                app_id INTEGER
            )
            """
        )

        # Score logs table: record each /score request for auditing and analysis
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS score_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                farmer_username TEXT,
                farmer_type TEXT,
                app_id INTEGER,
                cibil_score INTEGER,
                farmer_data_json TEXT,
                trust_score REAL,
                conf_score REAL,
                risk_status TEXT,
                loan_decision TEXT,
                model_available INTEGER
            )
            """
        )
        # Migration: add app_id if missing (existing DBs)
        try:
            cur.execute("ALTER TABLE score_logs ADD COLUMN app_id INTEGER")
        except sqlite3.OperationalError:
            pass  # column already exists

        # Admin audit log: record admin endpoint access for audit trail
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                success INTEGER NOT NULL
            )
            """
        )

        # Report logs table: record each generated PDF
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS report_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                farmer_username TEXT,
                app_id INTEGER,
                pdf_path TEXT,
                trust_score REAL,
                conf_score REAL,
                risk_status TEXT,
                model_available INTEGER
            )
            """
        )

        conn.commit()
    finally:
        conn.close()


def save_application(app: Dict[str, Any]) -> int:
    """
    Inserts a new application row.
    Returns the application id.
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO applications (
                farmer_username, farmer_name, farmer_type,
                district, state, crop_name, season,
                loan_amount, approved_amount,
                trust_score, conf_score, risk_status,
                status, applied_at, decided_at, raw_payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                app.get("farmer_username"),
                app.get("farmer_name"),
                app.get("farmer_type"),
                app.get("district"),
                app.get("state"),
                app.get("crop_name"),
                app.get("season"),
                float(app.get("loan_amount") or 0),
                app.get("approved_amount"),
                float(app.get("trust_score") or 0),
                float(app.get("conf_score") or 0),
                app.get("risk_status"),
                app.get("status") or "Pending",
                app.get("applied_at") or _now_iso(),
                app.get("decided_at"),
                json.dumps(app.get("data") or {}),
            ),
        )
        app_id = cur.lastrowid
        conn.commit()
        return app_id
    finally:
        conn.close()


def list_applications() -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, farmer_username, farmer_name, farmer_type, district, state, crop_name, season, "
            "loan_amount, approved_amount, trust_score, conf_score, risk_status, status, applied_at, decided_at, raw_payload_json "
            "FROM applications ORDER BY applied_at DESC, id DESC"
        )
        rows = cur.fetchall()
        apps: List[Dict[str, Any]] = []
        for r in rows:
            data: Dict[str, Any] = {}
            try:
                data = json.loads(r["raw_payload_json"] or "{}")
            except Exception:
                data = {}
            apps.append(
                {
                    "id": r["id"],
                    "farmer_username": r["farmer_username"],
                    "farmer_name": r["farmer_name"],
                    "farmer_type": r["farmer_type"],
                    "district": r["district"],
                    "state": r["state"],
                    "crop_name": r["crop_name"],
                    "season": r["season"],
                    "loan_amount": r["loan_amount"],
                    "approved_amount": r["approved_amount"],
                    "trust_score": r["trust_score"],
                    "conf_score": r["conf_score"],
                    "risk_status": r["risk_status"],
                    "status": r["status"],
                    "applied_at": r["applied_at"],
                    "decided_at": r["decided_at"],
                    "data": data,
                }
            )
        return apps
    finally:
        conn.close()


def update_decision(app_id: int, status: str, approved_amount: Any) -> None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE applications
            SET status = ?, approved_amount = ?, decided_at = ?
            WHERE id = ?
            """,
            (
                status,
                float(approved_amount) if approved_amount is not None else None,
                _now_iso(),
                app_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def insert_admin_audit_log(endpoint: str, success: bool) -> None:
    """Record admin endpoint access for audit trail."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO admin_audit_log (ts, endpoint, success) VALUES (?, ?, ?)",
            (_now_iso(), endpoint, 1 if success else 0),
        )
        conn.commit()
    finally:
        conn.close()


def list_admin_audit_logs(limit: int = 500) -> List[Dict[str, Any]]:
    """List recent admin endpoint access for audit."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, ts, endpoint, success FROM admin_audit_log ORDER BY ts DESC, id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {
                "id": row["id"],
                "ts": row["ts"],
                "endpoint": row["endpoint"],
                "success": bool(row["success"]),
            }
            for row in (dict(r) for r in rows)
        ]
    finally:
        conn.close()


def insert_notification(kind: str, message: str, app_id: int | None = None) -> None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO notifications (ts, kind, message, app_id) VALUES (?, ?, ?, ?)",
            (_now_iso(), kind, message, app_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_notifications(limit: int = 200) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, ts, kind, message, app_id FROM notifications ORDER BY ts DESC, id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "ts": r["ts"],
                "kind": r["kind"],
                "message": r["message"],
                "app_id": r["app_id"],
            }
            for r in rows
        ]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Logging helpers for score/report events
# ---------------------------------------------------------------------------

def save_score_log(
    farmer_username: str | None,
    farmer_type: str | None,
    cibil_score: int | None,
    farmer_data: dict,
    trust_score: float,
    conf_score: float,
    risk_status: str | None,
    loan_decision: str | None,
    model_available: bool,
    app_id: int | None = None,
) -> int:
    """Store a record of a scoring request for audit or analysis."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO score_logs (
                ts, farmer_username, farmer_type, app_id, cibil_score,
                farmer_data_json, trust_score, conf_score, risk_status,
                loan_decision, model_available
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now_iso(),
                farmer_username,
                farmer_type,
                app_id,
                cibil_score,
                json.dumps(farmer_data or {}),
                trust_score,
                conf_score,
                risk_status,
                loan_decision,
                1 if model_available else 0,
            ),
        )
        log_id = cur.lastrowid
        conn.commit()
        return log_id
    finally:
        conn.close()


def save_report_log(
    farmer_username: str | None,
    app_id: int | None,
    pdf_path: str,
    trust_score: float,
    conf_score: float,
    risk_status: str | None,
    model_available: bool,
) -> int:
    """Record when a PDF report is generated."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO report_logs (
                ts, farmer_username, app_id, pdf_path,
                trust_score, conf_score, risk_status, model_available
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now_iso(),
                farmer_username,
                app_id,
                pdf_path,
                trust_score,
                conf_score,
                risk_status,
                1 if model_available else 0,
            ),
        )
        log_id = cur.lastrowid
        conn.commit()
        return log_id
    finally:
        conn.close()



def link_score_to_application(
    app_id: int,
    farmer_username: str | None,
    farmer_type: str | None,
) -> int:
    """Link the most recent matching score log to an application. Returns rows updated."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        u = farmer_username or ""
        t = farmer_type or ""
        cur.execute(
            """
            UPDATE score_logs
            SET app_id = ?
            WHERE id = (
                SELECT id FROM score_logs
                WHERE COALESCE(farmer_username, '') = ?
                  AND COALESCE(farmer_type, '') = ?
                  AND app_id IS NULL
                ORDER BY ts DESC, id DESC LIMIT 1
            )
            """,
            (app_id, u, t),
        )
        rows = cur.rowcount
        conn.commit()
        return rows
    finally:
        conn.close()


def list_score_logs(limit: int = 200) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, ts, farmer_username, farmer_type, app_id, cibil_score, farmer_data_json, trust_score, conf_score, risk_status, loan_decision, model_available FROM score_logs ORDER BY ts DESC, id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            row = dict(r)
            data = {}
            try:
                data = json.loads(row.get("farmer_data_json") or "{}")
            except Exception:
                data = {}
            out.append({
                "id": row["id"],
                "ts": row["ts"],
                "farmer_username": row["farmer_username"],
                "farmer_type": row["farmer_type"],
                "app_id": row.get("app_id"),
                "cibil_score": row["cibil_score"],
                "farmer_data": data,
                "trust_score": row["trust_score"],
                "conf_score": row["conf_score"],
                "risk_status": row["risk_status"],
                "loan_decision": row["loan_decision"],
                "model_available": bool(row["model_available"]),
            })
        return out
    finally:
        conn.close()


def list_report_logs(limit: int = 200) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, ts, farmer_username, app_id, pdf_path, trust_score, conf_score, risk_status, model_available FROM report_logs ORDER BY ts DESC, id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append({
                "id": r["id"],
                "ts": r["ts"],
                "farmer_username": r["farmer_username"],
                "app_id": r["app_id"],
                "pdf_path": r["pdf_path"],
                "trust_score": r["trust_score"],
                "conf_score": r["conf_score"],
                "risk_status": r["risk_status"],
                "model_available": bool(r["model_available"]),
            })
        return out
    finally:
        conn.close()
