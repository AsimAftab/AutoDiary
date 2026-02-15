# VTU Auto Diary Filler

Python script to upload internship diary entries from a JSON file.

## 1. Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Alternative (uses `setup.py`):

```powershell
pip install .
```

## 2. Configure

```powershell
Copy-Item config\settings.example.json config\settings.json
Copy-Item entries\diary_entries.example.json entries\diary_entries.json
Copy-Item .env.example .env
```

Edit `config/settings.json`:
- keep `auth.mode` as `"login"` for credential login flow
- keep `defaults.internship_id` as your internship ID
- set `defaults.internship_start_date` (example: `2026-02-05`)
- keep `defaults.internship_end_date` as `"today"` to auto-include current date
- set `defaults.holiday_weekdays` (example: `["Sunday"]`)
- optionally set `defaults.holiday_dates` (example: `["2026-01-26"]`)

Edit `.env`:
- set `VTU_EMAIL`
- set `VTU_PASSWORD`
- optional override `HOLIDAY_WEEKDAYS` as comma-separated values (example: `Sunday`)
- optional override `HOLIDAY_DATES` as comma-separated values (example: `2026-01-26,2026-02-14`)

## 3. Run

Dry run:

```powershell
python scripts\upload_diaries.py --dry-run
```

Auto-assign missing dates from internship date range:

```powershell
python scripts\upload_diaries.py --auto-dates --skip-existing
```

Actual upload:

```powershell
python scripts\upload_diaries.py
```

Upload while skipping dates already present on portal:

```powershell
python scripts\upload_diaries.py --skip-existing
```

Holiday behavior:
- Entries that fall on configured holiday weekdays or holiday dates are skipped automatically.
- If an entry has no `date`, the script can auto-assign a valid working date from start to end range.

Token expiry behavior:
- In `auth.mode = "login"`, if server returns token-expired/unauthorized, the script re-logins and retries that request automatically.
- Login is guarded by `max_login_attempts` (default `3`); if all attempts fail, execution stops.

Optional custom `.env` path:

```powershell
python scripts\upload_diaries.py --env-file .env
```

Login only (no diary upload):

```powershell
python scripts\upload_diaries.py --login-only
```

Login and print current access token:

```powershell
python scripts\upload_diaries.py --login-only --show-access-token
```

Print existing diary dates from portal:

```powershell
python scripts\upload_diaries.py --print-existing
```

## Notes

- Do not commit `.env` or any file with live credentials/tokens.
