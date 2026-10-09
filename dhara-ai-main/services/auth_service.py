import os
import re
import hashlib
import hmac
import sqlite3
from datetime import datetime, timezone

UserStore = dict[str, dict]

# SQLite database path
try:
    # When imported from backend
    from backend.db import DB_PATH, get_conn as backend_get_conn, DATA_DIR
    get_conn = backend_get_conn
except ImportError:
    # When imported from frontend (standalone)
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    DB_PATH = os.path.join(DATA_DIR, "dhara.db")
    
    def get_conn():
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def _normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def validate_username(username: str) -> tuple[bool, str]:
    u = _normalize_username(username)
    if not u:
        return False, "User ID is required."
    if len(u) < 4 or len(u) > 32:
        return False, "User ID must be 4–32 characters."
    if not re.fullmatch(r"[a-z0-9_\.]+", u):
        return False, "Use only lowercase letters, numbers, underscore, or dot."
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    p = password or ""
    if len(p) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", p):
        return False, "Add at least 1 uppercase letter."
    if not re.search(r"[a-z]", p):
        return False, "Add at least 1 lowercase letter."
    if not re.search(r"[0-9]", p):
        return False, "Add at least 1 number."
    if not re.search(r"[^A-Za-z0-9]", p):
        return False, "Add at least 1 special character."
    return True, ""


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)


def init_user_store(store: UserStore | None = None) -> UserStore:
    """
    Initialize. Falls back to in-memory for backward compatibility.
    """
    return store if store is not None else {}


def create_user(
    store: UserStore,
    username: str,
    full_name: str,
    phone: str | None,
    role: str,
    password: str,
) -> tuple[bool, str]:
    """
    Create a new user in SQLite and fallback in-memory store.
    """
    u = _normalize_username(username)
    full_name = (full_name or "").strip()
    phone = (phone or "").strip() or None
    role = (role or "Farmer").strip()

    ok, msg = validate_username(u)
    if not ok:
        return False, msg
    if not full_name:
        return False, "Full name is required."
    ok, msg = validate_password(password)
    if not ok:
        return False, msg

    salt = os.urandom(16)
    pwd_hash = _hash_password(password, salt)

    # Check in-memory store first
    if u in store:
        return False, "That User ID already exists. Choose another."

    # Try to save to SQLite
    try:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO users (username, full_name, phone, role, password_salt, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (u, full_name, phone, role, salt, pwd_hash, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        finally:
            conn.close()
    except sqlite3.IntegrityError:
        return False, "That User ID already exists in the database. Choose another."
    except Exception as e:
        return False, f"Database error: {e}"

    # Also add to in-memory store for session use
    store[u] = {
        "username": u,
        "full_name": full_name,
        "phone": phone,
        "role": role,
        "password_salt": salt,
        "password_hash": pwd_hash,
    }
    return True, "Account created successfully. You can now log in."


def authenticate(store: UserStore, username: str, password: str) -> tuple[bool, dict | None, str]:
    """
    Authenticate against SQLite database (primary) and in-memory store (fallback).
    """
    u = _normalize_username(username)
    if not u or not password:
        return False, None, "Enter both User ID and password."

    # Try SQLite first
    try:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT username, full_name, phone, role, password_salt, password_hash FROM users WHERE username = ?",
                (u,),
            )
            row = cur.fetchone()
        finally:
            conn.close()

        if row:
            salt = row["password_salt"]
            expected = row["password_hash"]
            actual = _hash_password(password, salt)
            if hmac.compare_digest(expected, actual):
                user = {
                    "username": row["username"],
                    "full_name": row["full_name"],
                    "phone": row["phone"],
                    "role": row["role"],
                }
                return True, user, ""
            else:
                return False, None, "Invalid credentials."
    except Exception:
        # Fall through to in-memory store if DB fails
        pass

    # Fallback to in-memory store
    row = store.get(u)
    if row is None:
        return False, None, "Invalid credentials."

    salt = row["password_salt"]
    expected = row["password_hash"]
    actual = _hash_password(password, salt)
    if not hmac.compare_digest(expected, actual):
        return False, None, "Invalid credentials."

    user = {
        "username": row["username"],
        "full_name": row["full_name"],
        "phone": row.get("phone"),
        "role": row["role"],
    }
    return True, user, ""


def get_user_by_username(username: str) -> dict | None:
    """
    Fetch user from SQLite by username. Returns user dict or None.
    """
    u = _normalize_username(username)
    if not u:
        return None

    try:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT username, full_name, phone, role FROM users WHERE username = ?",
                (u,),
            )
            row = cur.fetchone()
        finally:
            conn.close()

        if row:
            d = dict(row)
            return {
                "username": d.get("username"),
                "full_name": d.get("full_name"),
                "phone": d.get("phone"),
                "role": d.get("role"),
            }
    except Exception:
        pass

    return None


def list_all_users() -> list[dict]:
    """
    Fetch all users from SQLite. Returns a list of user dicts with id, username, full_name, phone, role, created_at.
    """
    try:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, username, full_name, phone, role, created_at FROM users ORDER BY created_at DESC")
            rows = cur.fetchall()
        finally:
            conn.close()

        users = []
        for r in rows:
            row = dict(r)
            users.append({
                "id": row.get("id"),
                "username": row.get("username"),
                "full_name": row.get("full_name"),
                "phone": row.get("phone"),
                "role": row.get("role"),
                "created_at": row.get("created_at"),
            })
        return users
    except Exception:
        return []

