# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VTU Auto Diary Filler is a Python CLI tool that automates uploading internship diary entries to the VTU internship portal API. It handles authentication, date assignment, holiday filtering, and retry logic.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Or using `setup.py`:
```powershell
pip install .
```

## Configuration

Copy example configs and fill in your details:

```powershell
Copy-Item config\settings.example.json config\settings.json
Copy-Item entries\diary_entries.example.json entries\diary_entries.json
Copy-Item .env.example .env
```

**Required in `.env`:**
- `VTU_EMAIL` - Your VTU portal email
- `VTU_PASSWORD` - Your VTU portal password

**Required in `config/settings.json`:**
- `defaults.internship_id` - Your internship ID
- `defaults.internship_start_date` - Format: `YYYY-MM-DD`
- `defaults.holiday_weekdays` - Example: `["Sunday"]`

## Common Commands

### Dry Run (validate entries without uploading)
```powershell
python scripts\upload_diaries.py --dry-run
```

### Upload with auto-date assignment and skip existing
```powershell
python scripts\upload_diaries.py --auto-dates --skip-existing
```

### Upload all entries
```powershell
python scripts\upload_diaries.py
```

### Test login only
```powershell
python scripts\upload_diaries.py --login-only
```

### Print existing diary dates from portal
```powershell
python scripts\upload_diaries.py --print-existing
```

### Fetch all existing entries from portal
```powershell
python scripts\fetch_previous_entries.py
```
Saves to `previous_entries/all_entries.json`.

## Architecture

### Core Components

**AutoDiaryClient (`scripts/upload_diaries.py`)**
- Main client class handling API communication
- Supports three auth modes: `login` (credential-based), `bearer` (token), `cookie`
- Implements retry logic with configurable delays and max attempts
- Automatic re-authentication on token expiry (login mode)

**Entry Processing Pipeline:**
1. Load entries from `entries/diary_entries.json`
2. Validate required keys: `description`, `hours`, `links`, `blockers`, `learnings`, `mood_slider`, `skill_ids`
3. Optionally fetch existing dates from API for idempotency
4. Apply holiday filters (weekdays + specific dates)
5. Auto-assign missing dates from internship date range if enabled
6. Upload entries with retry logic

**Configuration Files:**
- `config/settings.json` - API endpoints, timeouts, retry config, defaults
- `.env` - Credentials (VTU_EMAIL, VTU_PASSWORD) and holiday overrides
- `entries/diary_entries.json` - Array of diary entry objects

**Holiday Behavior:**
- Entries falling on configured holiday weekdays or dates are automatically skipped
- Environment variables can override settings: `HOLIDAY_WEEKDAYS`, `HOLIDAY_DATES`

### Authentication Modes

**login mode (recommended):**
- Uses credentials to obtain access token cookie
- Auto re-authenticates on 401/token-expired responses
- Guarded by `max_login_attempts` setting

**bearer mode:**
- Requires `auth.access_token` in settings
- Sets `Authorization: Bearer <token>` header

**cookie mode:**
- Requires `auth.cookie` or `auth.access_token` in settings
- Sets `Cookie` header with access_token

### Key Methods in AutoDiaryClient

- `login_with_guard()` - Performs login with retry attempts
- `request_with_reauth()` - Wraps requests with auto re-authentication
- `fetch_existing_dates()` - Paginated fetch of all diary dates
- `build_working_dates()` - Generates list of valid working days
- `assign_missing_dates()` - Auto-assigns dates to entries missing them
- `submit_with_retries()` - Uploads single entry with retry logic

## Required Entry Keys

Each diary entry must contain:
```json
{
  "description": "...",
  "hours": 8,
  "links": "",
  "blockers": "",
  "learnings": "...",
  "mood_slider": 5,
  "skill_ids": ["44", "16", "20"]
}
```

Optional: `"date": "YYYY-MM-DD"` - If omitted, can be auto-assigned.

## CLI Structure

Uses Typer for CLI with both legacy options and subcommands:

**Legacy style (options on root):**
```powershell
python scripts\upload_diaries.py --dry-run --auto-dates --skip-existing
```

**Subcommands style:**
```powershell
python scripts\upload_diaries.py run --dry-run --auto-dates
python scripts\upload_diaries.py login --show-access-token
python scripts\upload_diaries.py existing
python scripts\upload_diaries.py interactive
```

Both styles are equivalent. The `interactive` subcommand prompts for options.

## Security Notes

- `.env` and `config/settings.json` are gitignored
- Never commit credentials or access tokens
- Access tokens are stored in session cookies only (login mode)
