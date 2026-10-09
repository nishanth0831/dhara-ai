import sqlite3

conn = sqlite3.connect("data/dhara.db")
cur = conn.cursor()

for table in ["users", "applications", "notifications", "score_logs", "report_logs", "admin_audit_log"]:
    print(f"\n=== {table} ===")
    cur.execute(f"SELECT * FROM {table} LIMIT 5")
    rows = cur.fetchall()
    for r in rows:
        print(dict(zip([d[0] for d in cur.description], r)))

conn.close()