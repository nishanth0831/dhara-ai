# Complete Data Storage Guide

## Overview
Dhara AI stores **all data points** in an SQLite database (`data/dhara.db`) for persistence, auditability, and compliance. This guide explains what's stored, how everything is connected, and how you can view/export it.

---

## The 5 Core Data Tables

### 1. **Users** (`users` table)
**What:** Registered farmer and admin accounts

**Stored fields:**
- `id` (primary key)
- `username` (unique)
- `full_name`
- `phone`
- `role` (Farmer or Admin)
- `password_hash` (salted PBKDF2)
- `password_salt`
- `created_at` (ISO timestamp)

**Example record:**
```json
{
  "id": 1,
  "username": "farmer_ramesh",
  "full_name": "Ramesh Kumar",
  "phone": "+919876543210",
  "role": "Farmer",
  "created_at": "2026-02-20T10:30:00+00:00"
}
```

---

### 2. **Applications** (`applications` table)
**What:** Loan applications with farmer data, scoring, and decisions

**Stored fields:**
- `id` (primary key)
- `farmer_username` (links to user)
- `farmer_name`
- `farmer_type` (New/Existing/Verified)
- `district`, `state`
- `crop_name`, `season`
- `loan_amount` (requested)
- `approved_amount` (after decision)
- `trust_score` (ML score)
- `conf_score` (verification confidence)
- `risk_status` (Low/Medium/High Risk)
- `status` (Pending/Approved/Rejected)
- `applied_at`, `decided_at` (ISO timestamps)
- `raw_payload_json` (full farmer input data)

**Raw payload includes:**
```json
{
  "name": "Ramesh Kumar",
  "land_size": 5.5,
  "irrigation_availability": 1,
  "soil_health_index": 72.5,
  "annual_rainfall_mm": 1200,
  "fertilizer_kg": 125,
  "pesticide_kg": 3.5,
  "yield_consistency_index": 0.85,
  "rainfall_deviation": 5.2,
  "previous_repayment_status": 1,
  "cibil_score": 680,
  "weather_temp_c": 28.5,
  "weather_condition": "Clear",
  ...
}
```

---

### 3. **Score Logs** (`score_logs` table)
**What:** Audit trail of every credit risk scoring evaluation

**Stored fields:**
- `id` (primary key)
- `ts` (timestamp scoring was run)
- `farmer_username` (links to user)
- `farmer_type`
- `cibil_score` (input)
- `farmer_data_json` (full input snapshot)
- `trust_score` (output)
- `conf_score` (output)
- `risk_status` (output)
- `loan_decision` (Approve/Reject/etc.)
- `model_available` (boolean - was ML model loaded?)

**Purpose:** Complete record of every `/score` API call

---

### 4. **Report Logs** (`report_logs` table)
**What:** History of generated PDF reports

**Stored fields:**
- `id` (primary key)
- `ts` (when report was generated)
- `farmer_username` (links to user)
- `app_id` (links to application)
- `pdf_path` (where file is stored)
- `trust_score` (score at time of report)
- `conf_score` (confidence at time of report)
- `risk_status` (risk at time of report)
- `model_available` (was model available?)

**Purpose:** Track every PDF generated with metadata for compliance

---

### 5. **Notifications** (`notifications` table)
**What:** System event messages

**Stored fields:**
- `id` (primary key)
- `ts` (when event occurred)
- `kind` (application_submitted, approved, rejected, etc.)
- `message` (human-readable text)
- `app_id` (links to application if relevant)

**Example:**
```json
{
  "id": 15,
  "ts": "2026-02-20T14:30:00+00:00",
  "kind": "application_submitted",
  "message": "New application submitted by Ramesh Kumar (Dharmapuri, TG)",
  "app_id": 5
}
```

---

## How Everything Is Connected

```
┌─────────────────────────────────────────────────────────────┐
│                      USERS (Authentication)                  │
│  farmer_ramesh • full_name • phone • role • password_hash    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           └─→ farmer_username in:
                               ├─ APPLICATIONS
                               ├─ SCORE_LOGS
                               └─ REPORT_LOGS

┌──────────────────────────────────────────────────────────────┐
│            APPLICATIONS (Loan Requests)                        │
│  id • farmer_username • farm_data • trust_score • status      │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           └─→ app_id in:
                               ├─ REPORT_LOGS
                               └─ NOTIFICATIONS

┌──────────────────────────────────────────────────────────────┐
│  SCORE_LOGS (Audit Trail)                                    │
│  id • ts • farmer_username • farmer_data_json • scores       │
│  [Linked by farmer_username to APPLICATIONS & USERS]         │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  REPORT_LOGS (PDF History)                                   │
│  id • ts • farmer_username • app_id • pdf_path • scores      │
│  [Linked by app_id to APPLICATIONS, farmer to USERS]        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  NOTIFICATIONS (Events)                                      │
│  id • ts • kind • message • app_id                           │
│  [Linked by app_id to APPLICATIONS]                          │
└──────────────────────────────────────────────────────────────┘
```

---

## Complete Data Flow Example

### Scenario: A farmer applies for a loan

**Step 1: User Registration**
```sql
INSERT INTO users VALUES (
  NULL, 'farmer_ramesh', 'Ramesh Kumar', '+919876543210', 
  'Farmer', <salt>, <hash>, '2026-02-20T10:30:00+00:00'
);
-- users.id = 1
```

**Step 2: Farmer Fills Form & Submits**
```sql
INSERT INTO applications VALUES (
  NULL, 'farmer_ramesh', 'Ramesh Kumar', 'Existing Farmer', 
  'Dharmapuri', 'TG', 'Rice', 'Kharif', 75000, NULL,
  0, 0, NULL, 'Pending',
  '2026-02-20T11:00:00+00:00', NULL,
  '{"name": "Ramesh Kumar", "land_size": 5.5, ...}'
);
-- applications.id = 5
-- Notification auto-created:
INSERT INTO notifications VALUES (
  NULL, '2026-02-20T11:00:00+00:00', 'application_submitted',
  'New application submitted by Ramesh Kumar...', 5
);
```

**Step 3: System Scores Application**
```sql
-- Backend calls /score endpoint
INSERT INTO score_logs VALUES (
  NULL, '2026-02-20T11:05:00+00:00', 'farmer_ramesh', 
  'Existing Farmer', 680, '{"name": "Ramesh Kumar", ...}',
  72.5, 85, 'Low Risk / High Confidence', 
  'Approve full loan', 1
);
-- score_logs.id = 42

-- Update application with scores
UPDATE applications SET 
  trust_score = 72.5, conf_score = 85, 
  risk_status = 'Low Risk / High Confidence'
WHERE id = 5;
```

**Step 4: Admin Reviews & Approves**
```sql
-- Admin approves in UI
UPDATE applications SET 
  status = 'Approved', approved_amount = 60000,
  decided_at = '2026-02-20T12:00:00+00:00'
WHERE id = 5;

INSERT INTO notifications VALUES (
  NULL, '2026-02-20T12:00:00+00:00', 'approved',
  'Application #5 has been approved', 5
);
```

**Step 5: Report Generated**
```sql
INSERT INTO report_logs VALUES (
  NULL, '2026-02-20T12:30:00+00:00', 'farmer_ramesh', 5,
  'reports/DharaAI_App_5_20260220.pdf', 72.5, 85, 
  'Low Risk / High Confidence', 1
);
```

**Now, to trace farmer_ramesh's complete history, just query by farmer_username:**
```sql
-- Find all records for farmer_ramesh:
SELECT * FROM applications WHERE farmer_username = 'farmer_ramesh';
SELECT * FROM score_logs WHERE farmer_username = 'farmer_ramesh';
SELECT * FROM report_logs WHERE farmer_username = 'farmer_ramesh';
SELECT * FROM notifications WHERE app_id IN (
  SELECT id FROM applications WHERE farmer_username = 'farmer_ramesh'
);
```

---

## 4 Ways to View Your Data

### Method 1: **Admin Data Browser (Easiest)**
1. Open Streamlit UI
2. Login as Admin
3. Click **Admin → Data Browser**
4. See all:
   - Total counts of everything
   - Users list
   - Applications with linked scores/reports/notifications
   - Audit trails
5. Click expandable applications to see relationships

### Method 2: **Individual Admin Pages**
- **Admin → Applications**: View all loan apps
- **Admin → Score Logs**: View scoring audit trail
- **Admin → Report Logs**: View all generated PDFs
- **Admin → Users**: View all registered accounts
- **Admin → Notifications**: View system events

### Method 3: **Backend APIs**
```bash
# Get complete export with relationships
curl "http://localhost:8000/data-export?admin_key=dhara_admin_demo"

# Get specific data
curl "http://localhost:8000/auth/users?admin_key=dhara_admin_demo"
curl "http://localhost:8000/applications"
curl "http://localhost:8000/score-logs"
curl "http://localhost:8000/report-logs"
```

### Method 4: **Direct Database Access**
```python
import sqlite3
import json

db = sqlite3.connect("data/dhara.db")
db.row_factory = sqlite3.Row

# See a farmer's complete history
cur = db.cursor()
cur.execute("SELECT * FROM applications WHERE farmer_username = ?", ("farmer_ramesh",))
app = cur.fetchone()
print("Application:", dict(app))

# Extract and pretty-print the farmer data
farmer_data = json.loads(app["raw_payload_json"])
print("Input data:", json.dumps(farmer_data, indent=2))

# See all scores for this farmer
cur.execute("SELECT * FROM score_logs WHERE farmer_username = ?", ("farmer_ramesh",))
for score in cur.fetchall():
    print("Score:", dict(score))

# See all reports
cur.execute("SELECT * FROM report_logs WHERE app_id = ?", (app["id"],))
for report in cur.fetchall():
    print("Report:", dict(report))

db.close()
```

---

## Data Retention

✅ **Persistent:** All data survives server restart (SQLite file on disk)  
✅ **Auditable:** Every action logged with timestamp  
✅ **Traceable:** Foreign keys connect all tables  
✅ **Secure:** Passwords hashed with salt (PBKDF2-SHA256)  
✅ **Complete:** Full farmer input snapshots stored for compliance

---

## Summary: What's Stored vs. What's Shown

| Data Point | Where It's Stored | When | Accessible Via |
|---|---|---|---|
| User account | `users` table | Registration | Admin → Users |
| Loan application | `applications` table | Form submitted | Admin → Applications / Data Browser |
| Farmer input form | `applications.raw_payload_json` | Form submitted | Data Browser / API export |
| Credit score | `score_logs` table | Scoring requested | Admin → Score Logs / Data Browser |
| Risk assessment | `applications` + `score_logs` | Scoring done | Dashboard / Data Browser |
| PDF report | `report_logs` table | Report generated | Admin → Report Logs / Data Browser |
| System events | `notifications` table | Events triggered | Admin → Notifications / Data Browser |

Every single data point is saved. Nothing is lost. Everything is connected and traceable.

---

## Next Steps

1. **Login as Admin** and navigate to **Data Browser** to see everything stored
2. **Export data** using the `/data-export` API for analysis
3. **Query directly** using Python/SQL for custom exports
4. **Set up backups** of `data/dhara.db` for production use

---
