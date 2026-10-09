# Database & Persistent Storage Setup

## Overview
All user accounts, login credentials, and application data are now stored in **SQLite** (`data/dhara.db`). This ensures data persists across sessions and reboots.

## Database Schema

### Users Table
Stores all user accounts with hashed passwords:
```
users (
  id,
  username (UNIQUE),
  full_name,
  phone,
  role (Farmer | Admin),
  password_salt (binary),
  password_hash (binary),
  created_at (ISO timestamp)
)
```

### Applications Table
Stores farmer loan applications and scoring results:
```
applications (
  id,
  farmer_username,
  farmer_name,
  farmer_type,
  district,
  state,
  crop_name,
  season,
  loan_amount,
  approved_amount,
  trust_score,
  conf_score,
  risk_status,
  status (Pending | Approved | Rejected),
  applied_at,
  decided_at,
  raw_payload_json (all farmer input data; may include `soil_card_id` when
                    a soil card was uploaded via OCR)
)
```

### Notifications Table
Stores system notifications:
```
notifications (
  id,
  ts,
  kind,
  message,
  app_id (foreign key to applications)
)
```

## Authentication Flow

### Registration (Sign Up)
1. User enters: username, full_name, phone, password, role
2. Frontend validates and calls: `POST /auth/register`
3. Backend hashes password with salt and inserts into `users` table
4. Account is immediately available for login

### Login
1. User enters: username, password
2. Frontend calls: `POST /auth/login`
3. Backend looks up user in `users` table, verifies hash, returns user object
4. Session is established in Streamlit `session_state`

### Fetch User Info
- Admin endpoint: `GET /auth/users?admin_key=dhara_admin_demo`
- Single user: `GET /auth/user/<username>`

## API Endpoints (Backend)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/auth/register` | Create new user |
| POST | `/auth/login` | Authenticate user |
| GET | `/auth/user/<username>` | Fetch single user |
| GET | `/auth/users?admin_key=...` | List all users (admin only) |

## Frontend Features

### Soil Card OCR
The application now accepts an uploaded soil card (image or PDF).  Dhāra
uses Tesseract OCR to read the document, extract the organisation name,
card identifier (must start with ``ISAAMW`` and have four trailing digits),
and any N/P/K fertilizer readings.  If the identifier passes a simple
validation (correct prefix and not previously seen in another application)
the form is auto‑filled and the application is submitted on the user's
behalf.


### User Registration & Login
- All sign-ups are saved to SQLite
- Passwords are salted and hashed with PBKDF2-SHA256
- Login validation checks against database

### Admin User Management Page
- Navigate to **Admin → Users** to see all registered users
- Displays: username, full name, role, phone, creation date
- Real-time fetch from database

### Application Persistence
- Every farmer application is stored with full data
- Accessible from **Admin → Applications**
- Can be viewed, decided on, and reported

## Running the System

### Setup & Install
```powershell
cd c:\Hackathons\Dhara
pip install -r requirements.txt
pip install -r backend\requirements.txt
```

### Start Both Services
```powershell
# Terminal 1: Backend API
cd c:\Hackathons\Dhara
python backend\app.py
# Output: Running on http://localhost:8000

# Terminal 2: Frontend App
cd c:\Hackathons\Dhara
streamlit run app.py
```

---

## Complete Data Storage & Retrieval

### What Data Is Stored?

Every interaction in Dhara is automatically persisted to the SQLite database:

#### 1. **User Accounts** (`users` table)
- Username, full name, phone, role (Farmer/Admin)
- Salted + hashed password (PBKDF2-SHA256)
- Creation timestamp

#### 2. **Loan Applications** (`applications` table)
- Farmer info: name, username, type (New/Existing/Verified), location (district/state)
- Loan details: requested amount, approved amount, crop, season
- Scoring results: trust_score, confidence_score, risk_status
- Full farmer input data as JSON: land size, rainfall, soil health, financial history, fertilizer usage, etc.
- Timestamps: applied_at, decided_at
- Status: Pending → Approved/Rejected

#### 3. **Scoring Events** (`score_logs` table)
- Triggered every time the `/score` endpoint is called
- Captures: farmer username, farmer type, CIBIL score, full farmer data (JSON), trust/confidence scores, risk assessment
- Timestamp of when scoring occurred
- Whether the ML model was available
- Loan decision (Approve, Reject, etc.)

#### 4. **Report Generations** (`report_logs` table)
- Recorded when PDF reports are generated
- Links to: farmer username, application_id, PDF file path
- Stores: trust_score, confidence_score, risk_status at time of report
- Whether model was available
- Timestamp

#### 5. **System Notifications** (`notifications` table)
- Event-driven notifications (new application, decision made, etc.)
- Links to application_id for traceability
- Type (application_submitted, approved, rejected, etc.)
- Timestamp and message

### How Data Is Connected

All five tables are linked together for complete audit trails:

```
USERS
  ↓
  ├─→ creates → APPLICATIONS
  │                ↓
  │                ├─→ has → SCORE_LOGS (via farmer_username)
  │                ├─→ has → REPORT_LOGS (via app_id)
  │                └─→ has → NOTIFICATIONS (via app_id)
  │
  └─→ is logged in → Sessions
```

**Example workflow trace:**
1. User "farmer_ramesh" registers → entry in `users` table
2. Farmer submits loan app → entry in `applications` (farmer_username = farmer_ramesh)
3. Score request processed → entry in `score_logs` (farmer_username = farmer_ramesh)
4. Trust score = 75, Confidence = 88 → saved in both `score_logs` and `applications`
5. PDF generated → entry in `report_logs` (app_id linked to application)
6. Application approved → entries in `notifications` (app_id linked)

All timestamps (ISO 8601 format) allow you to reconstruct the exact sequence of events.

### How to View Your Stored Data

#### **Option 1: Data Browser (Easiest)**
1. Login as an **Admin** user
2. Navigate to **Admin → Data Browser**
3. You'll see:
   - **Overview metrics**: Total users, applications, scoring events, reports, notifications
   - **Users tab**: All registered accounts with role and phone
   - **Applications tab**: Each application expanded showing:
     - Loan amount, trust score, status
     - **Linked scoring events** for that farmer
     - **Linked reports** generated for that app
     - **Linked notifications** (approvals, rejections, etc.)
   - **Scoring tab**: Complete audit log of every scorer request
   - **Reports tab**: All generated PDFs with metadata
   - **Notifications tab**: All system messages with app links

#### **Option 2: Backend API (Advanced)**
```bash
# Get all data (requires admin_key)
curl "http://localhost:8000/data-export?admin_key=dhara_admin_demo" | jq

# Get users
curl "http://localhost:8000/auth/users?admin_key=dhara_admin_demo" | jq

# Get applications
curl "http://localhost:8000/applications" | jq

# Get score logs
curl "http://localhost:8000/score-logs" | jq

# Get report logs
curl "http://localhost:8000/report-logs" | jq
```

#### **Option 3: Direct SQL Query (Advanced)**
```python
import sqlite3

db = sqlite3.connect("data/dhara.db")
db.row_factory = sqlite3.Row
cur = db.cursor()

# See all applications
cur.execute("SELECT * FROM applications")
apps = cur.fetchall()
for app in apps:
    print(dict(app))

# See all scores for a farmer
cur.execute("SELECT * FROM score_logs WHERE farmer_username = ?", ("farmer_ramesh",))
scores = cur.fetchall()

# See notifications for an application
cur.execute("SELECT * FROM notifications WHERE app_id = ?", (app_id,))
notifs = cur.fetchall()

db.close()
```

#### **Option 4: Admin Pages**
Navigate through the Admin menu to see individual views:
- **Admin → Applications**: View all applications
- **Admin → Score Logs**: Audit log of all scoring requests
- **Admin → Report Logs**: History of all PDFs generated
- **Admin → Users**: All registered farmer/admin accounts
- **Admin → Notifications**: All system events

### Data Export for External Analysis

The `/data-export` endpoint returns a JSON structure with all data and relationships:

```json
{
  "ok": true,
  "users": [...],
  "applications_with_relations": [
    {
      "app": { ... application record ... },
      "scores": [ ... linked score_logs ... ],
      "reports": [ ... linked report_logs ... ],
      "notifications": [ ... linked notifications ... ]
    }
  ],
  "summary": {
    "total_users": 5,
    "total_applications": 12,
    "total_scores_logged": 45,
    "total_reports_generated": 12,
    "total_notifications": 28
  }
}
```

Use this to export to Excel/CSV or your analytics tool.

### Data Retention & Privacy

- **All data persists** across server restarts (persistent SQLite database)
- **Passwords are hashed** with salt; the original password is never stored
- **Farmer data is stored as JSON** inside the application record for audit and analysis
- **Timestamps are in ISO 8601 format** for easy sorting and filtering
- **Foreign keys** (farmer_username, app_id) enable joining tables for complete traceability

---
streamlit run app.py
# Opens browser at http://localhost:8501
```

### Test the System
1. **Create an account**: Go to Access → Sign up (create a test account)
2. **Admin list users**: Sign in as Admin → Users (should see your account)
3. **Submit application**: Sign in as Farmer → Application (enter loan request)
4. **View in database**: Admin → Applications (see submitted data)
5. **Check PDF reports**: Admin → Reports (download generated PDF)

## Database File Location
```
c:\Hackathons\Dhara\data\dhara.db
```

To reset the database, delete this file and run the backend again.

## Security Notes

- Passwords are hashed with PBKDF2-HMAC-SHA256 + 16-byte salt
- No plaintext passwords stored
- Admin key for user listing is hardcoded as `"dhara_admin_demo"` (change in production)
- Use HTTPS in production
- Never commit `dhara.db` to version control

## Troubleshooting

### "Could not reach backend" error
- Ensure backend is running on terminal 1
- Check: `http://localhost:8000/health` returns `{"ok": true}`

### User can't log in
- Verify account exists: Admin → Users
- Check password requirements (8+ chars, uppercase, lowercase, number, special char)

### Data not saving
- Check that `data/` directory exists
- Verify the `data/` directory exists and is writable (SQLite is included in Python's standard library)
- Check file permissions on `data/dhara.db`

### Score Logs Table
Records every call to `/score` for auditing and analysis:
```
score_logs (
  id,
  ts,
  farmer_username,
  farmer_type,
  cibil_score,
  farmer_data_json,
  trust_score,
  conf_score,
  risk_status,
  loan_decision,
  model_available
)
```

### Report Logs Table
Records each PDF generated via `/report`, links to application if available:
```
report_logs (
  id,
  ts,
  farmer_username,
  app_id,
  pdf_path,
  trust_score,
  conf_score,
  risk_status,
  model_available
)
```

## Admin Interface Enhancements

There are new admin pages accessible after signing in as an **Admin**:
- **Score Logs** – displays recent scoring events from `score_logs`.
- **Report Logs** – shows history of generated reports from `report_logs`.

These are fetched via the backend endpoints `/score-logs` and `/report-logs` which return JSON lists of the rows.

## Persistence Benefits

✅ User accounts survive app restarts  
✅ Applications are permanently stored  
✅ Admin can review history any time  
✅ Multi-user concurrent access  
✅ Audit trail of decisions & timestamps  
✅ Scalable to backend database (PostgreSQL, MySQL)  
