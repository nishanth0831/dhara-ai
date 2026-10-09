"""
Test script to verify SQLite persistence and auth system.
Run from project root: python tests/test_database_auth.py
"""
import os
import sys

# Add project root to path
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root not in sys.path:
    sys.path.insert(0, root)

# remove or clear existing database so tests start fresh
try:
    import backend.db as _dbmod
    dbf = _dbmod.DB_PATH
    # create data directory just in case
    os.makedirs(os.path.dirname(dbf), exist_ok=True)
    if os.path.exists(dbf):
        # attempt to delete file; if locked, clear tables instead
        try:
            os.remove(dbf)
        except Exception:
            import sqlite3

            conn = sqlite3.connect(dbf)
            cur = conn.cursor()
            for t in ["users", "score_logs", "report_logs"]:
                try:
                    cur.execute(f"DELETE FROM {t}")
                except Exception:
                    pass
            conn.commit()
            conn.close()
    # ensure tables exist for fresh DB
    try:
        _dbmod.init_db()
    except Exception:
        pass
except Exception:
    pass

from services.auth_service import (
    create_user,
    authenticate,
    get_user_by_username,
    list_all_users,
    init_user_store,
)


def test_user_creation():
    print("✓ Test 1: Creating a new user...")
    store = init_user_store()
    ok, msg = create_user(
        store=store,
        username="test_farmer_001",
        full_name="Test Farmer",
        phone="+919876543210",
        role="Farmer",
        password="TestPass123!",
    )
    assert ok, f"Failed to create user: {msg}"
    print(f"  ✓ User created: {msg}")


def test_user_login():
    print("✓ Test 2: Authenticating user...")
    store = init_user_store()
    ok, user, msg = authenticate(store, "test_farmer_001", "TestPass123!")
    assert ok, f"Failed to authenticate: {msg}"
    assert user["username"] == "test_farmer_001"
    assert user["full_name"] == "Test Farmer"
    assert user["role"] == "Farmer"
    print(f"  ✓ User authenticated: {user}")


def test_invalid_password():
    print("✓ Test 3: Testing invalid password...")
    store = init_user_store()
    ok, user, msg = authenticate(store, "test_farmer_001", "WrongPassword123!")
    assert not ok, "Should have failed with wrong password"
    print(f"  ✓ Correctly rejected: {msg}")


def test_get_user():
    print("✓ Test 4: Fetching user by username...")
    user = get_user_by_username("test_farmer_001")
    assert user is not None, "User not found"
    assert user["username"] == "test_farmer_001"
    print(f"  ✓ User fetched: {user}")


def test_list_users():
    print("✓ Test 5: Listing all users...")
    users = list_all_users()
    assert isinstance(users, list), "Should return a list"
    assert len(users) > 0, "Should have at least one user"
    print(f"  ✓ Found {len(users)} user(s)")
    for u in users:
        print(f"    - {u['username']} ({u['role']}): {u['full_name']}")


def test_duplicate_username():
    print("✓ Test 6: Testing duplicate username prevention...")
    store = init_user_store()
    ok, msg = create_user(
        store=store,
        username="test_farmer_001",
        full_name="Another User",
        phone=None,
        role="Farmer",
        password="AnotherPass123!",
    )
    assert not ok, "Should reject duplicate username"
    print(f"  ✓ Correctly rejected: {msg}")


def test_password_requirements():
    print("✓ Test 7: Testing password requirements...")
    store = init_user_store()
    
    # Test password too short
    ok, msg = create_user(
        store=store,
        username="test_user_weak",
        full_name="Test User",
        phone=None,
        role="Farmer",
        password="Short1!",
    )
    assert not ok, "Should reject weak password"
    print(f"  ✓ Correctly rejected weak password: {msg}")


def test_score_and_report_logs():
    print("✓ Test 8: Logging score and report records...")
    from backend.db import save_score_log, save_report_log

    # simple score log
    log_id = save_score_log(
        farmer_username="tester",
        farmer_type="New Farmer",
        cibil_score=700,
        farmer_data={"Area": 5},
        trust_score=80.0,
        conf_score=90.0,
        risk_status="Low",
        loan_decision="Loan Approved",
        model_available=True,
    )
    assert isinstance(log_id, int)
    print(f"  ✓ Score log saved (id={log_id})")

    rpt_id = save_report_log(
        farmer_username="tester",
        app_id=123,
        pdf_path="/tmp/report.pdf",
        trust_score=80.0,
        conf_score=90.0,
        risk_status="Low",
        model_available=True,
    )
    assert isinstance(rpt_id, int)
    print(f"  ✓ Report log saved (id={rpt_id})")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing SQLite Persistence & Auth System")
    print("="*60 + "\n")
    
    try:
        test_user_creation()
        test_user_login()
        test_invalid_password()
        test_get_user()
        test_list_users()
        test_duplicate_username()
        test_password_requirements()
        test_score_and_report_logs()
        
        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("="*60)
        print("\nDatabase location: c:\\Hackathons\\Dhara\\data\\dhara.db")
        print("Users are now persisted and will survive app restarts.\n")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
