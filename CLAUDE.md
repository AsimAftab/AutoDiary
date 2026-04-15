# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VTU Auto Diary Filler is a Python 3.11+ interactive CLI application that automates uploading internship diary entries to the VTU internship portal API. It uses Rich for terminal UI, questionary for interactive prompts, and Pydantic for data validation.

## Setup & Common Commands

Uses `uv` as the package manager. All commands assume you're in the project root.

```powershell
uv sync                              # Install all dependencies (creates .venv automatically)
uv run autodiary                     # Run the application (or: uv run python -m autodiary)
uv run ruff format --check .         # Check formatting
uv run ruff check .                  # Lint
uv run ruff format .                 # Auto-format
uv run pytest                        # Run all tests
uv run pytest tests/test_config.py   # Run a single test file
uv run pyinstaller --clean autodiary.spec  # Build Windows executable → dist/AutoDiary.exe
```

## Architecture

### Package Layout (`src/autodiary/`)

- **`__main__.py`** — Entry point. Bootstraps `~/.autodiary/` directory, sets up file logging, initializes `ConfigManager`, launches `MainMenu`.
- **`cli/`** — Interactive menu system (all terminal UI lives here):
  - `MainMenu` dispatches to `UploadMenu`, `ViewMenu`, `ConfigMenu`
  - `UploadMenu` — Upload workflows: auto-dates, date range, dry run, from file, interactive review
  - `ViewMenu` — View entries, statistics, download JSON, export CSV
  - `ConfigMenu` — Setup wizard, edit credentials/internship/holidays, test connection, reset
  - `utils.py` — Shared Rich formatting helpers (`print_success`, `print_error`, etc.)
- **`core/`** — Business logic (no UI concerns):
  - `VTUApiClient` — API communication via `requests.Session`, credential-based auth with auto re-auth on 401, retry logic with configurable delays
  - `ConfigManager` — Load/save/migrate config, atomic file writes, password encryption/decryption, `is_configured` property
- **`models/`** — Pydantic v2 models:
  - `AppConfig` — Validates all settings (email, internship dates, holidays, retry config)
  - `DiaryEntry` — Validates diary submissions (description, hours, learnings, mood_slider, skill_ids)
- **`utils/`** — Helpers:
  - `CryptoManager` — Fernet symmetric encryption for password storage, key file at `~/.autodiary/.encryption_key`
  - `validators.py` — Input validation functions, first-run detection
- **`resources/`** — Bundled assets: `skills_mapping.json` (VTU skill IDs), config/entry templates, app icon

### Data Flow

1. First run triggers setup wizard (ConfigMenu) → writes `~/.autodiary/config.json` with encrypted password
2. User selects upload workflow from UploadMenu
3. Diary entries loaded from JSON file, validated via `DiaryEntry` Pydantic model
4. `VTUApiClient` authenticates (login → access token cookie), fetches existing dates for idempotency
5. Holiday filter applied (weekday + specific date exclusions), auto-date assignment if enabled
6. Entries uploaded with retry logic, random delays between requests

### Configuration

All config lives at `~/.autodiary/config.json` (created by the app's setup wizard). Passwords are Fernet-encrypted. No `.env` files — credentials are managed through the interactive ConfigMenu.

### CI/CD

- `.github/workflows/ci.yml` — Runs Ruff + pytest on push/PR to main (Windows runner)
- `.github/workflows/release.yml` — Builds `AutoDiary.exe` via PyInstaller on GitHub Release publish

### Style

Ruff handles all linting and formatting. Config in `pyproject.toml`: 100-char line length, double quotes, rules E/W/F/I/C4/B/UP enabled. See `AGENTS.md` for commit conventions and contributor guidelines.
