# CampusBridge AI — working local reference build

This is a new, standalone application built using the linked public repository as a visual/reference starting point. It does not modify that GitHub repository. It uses a refreshed navy/teal responsive UI, Flask and SQLite; no npm/Node installation is required.

## Windows PowerShell
Open PowerShell in the extracted folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --timeout 120 --retries 5 -r requirements.txt
py app.py
```

Then open http://127.0.0.1:5000

## Demo administrator
Email: `admin@campusbridge.demo`  
Password: `CampusAdmin@123`

If the DB already exists and the password has changed, delete `campusbridge.db` only if you are okay resetting local demo data, then restart `py app.py`.

## Student account
Use Create a student account. Password must be at least 12 characters, e.g. `Student@12345`.

## Implemented
- Separate Admin and Student login with server-side sessions and hashed passwords.
- Public registration creates students only.
- Admin dashboard metrics, student directory, job create/archive, notification log and audit log.
- Student profile, skills-based match score and missing-skill hints, opportunities, application tracker, in-app message inbox and read/unread.
- Job creation creates in-app alerts for students with alerts enabled and matching graduation year.
- SQLite persistence and backend authorization checks.

## Important limitations
- This local demo sends in-app notifications only; it does not send actual SMTP emails.
- Matching is rule-based skill overlap, not a trained ML model.
- Jobs are sample data; live job discovery is not configured.
- Before public deployment, configure a strong `CAMPUSBRIDGE_SECRET`, HTTPS/secure cookies, CSRF protection, rate limiting, migrations and an actual email provider.
