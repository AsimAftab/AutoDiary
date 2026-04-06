# GEMINI.md

## Project Overview

**VTU Auto Diary Filler** is a sophisticated, industry-grade Python CLI application designed to automate internship diary submissions to the VTU portal. It transitions from a "student-made script" to a robust, distributable system by prioritizing security, safety, and modern software engineering standards.

### Core Technologies
- **Language:** Python 3.8+ (Targeting 3.11 for production builds)
- **Modern Tooling:** [uv](https://github.com/astral-sh/uv) for lightning-fast dependency management and [Hatch](https://hatch.pypa.io/) for build orchestration.
- **Architecture:** "src layout" (`src/autodiary/`) to ensure clean separation between source code and development artifacts.
- **Safety Engine:** Advanced bot-evasion logic featuring randomized human-like delays and realistic browser header impersonation.
- **Security:** AES-128-CBC encryption for local credential storage (moving towards OS-level keyring integration).
- **CI/CD:** Automated GitHub Actions pipeline for linting, formatting (Ruff), and multi-platform distribution.

### Key Features
- **Intelligent Automation:** Batch upload diary entries with automatic date assignment, excluding weekends and public holidays.
- **Stealth Mode:** Mimics human interaction patterns with randomized "jitter" delays (0.1s - 0.8s) and rotating modern User-Agents to avoid portal detection.
- **Robust Error Handling:** Exponential backoff and retry logic for server-side errors (429/503) and network instability.
- **Guided Setup:** Interactive CLI wizard for first-time configuration, ensuring all required fields and holiday settings are validated.
- **Idempotency:** Server-side synchronization to skip already-uploaded entries and prevent duplicates.

---

## Building and Running

### Prerequisites
- Python 3.11+ (Recommended)
- [uv](https://github.com/astral-sh/uv) package manager.

### Local Development Setup
```powershell
# Sync dependencies and create virtual environment
uv sync

# Run the application in development mode
uv run python -m autodiary
```

### Production Build
```powershell
# Build the standalone Windows executable
uv run pyinstaller --clean autodiary.spec
```

### Quality Assurance
Before committing any code, run the following automated checks:
```powershell
# Formatting check (Ruff)
uv run ruff format --check .

# Linting check (Ruff)
uv run ruff check .

# Unit Testing (Pytest)
uv run pytest --basetemp=pytest_temp
```

---

## Testing Suite

The project now includes a comprehensive automated test suite built with **pytest**. These tests ensure the reliability of core components and prevent regressions.

### Test Categories
- **Validators (`tests/test_validators.py`):** Unit tests for all input and format validation functions.
- **Security (`tests/test_crypto.py`):** Tests for encryption, decryption, and key management.
- **Configuration (`tests/test_config.py`):** Validates Pydantic models and the `ConfigManager` lifecycle.
- **Diary Model (`tests/test_entry.py`):** Ensures diary entries meet the required structure and constraints.
- **API Client (`tests/test_client.py`):** Mocks VTU API interactions to verify login and upload flows without network calls.

### Running Tests
To run the full test suite reliably on all platforms (including Windows), use:
```powershell
uv run pytest --basetemp=pytest_temp
```
*Note: The `--basetemp` flag is used to avoid directory permission issues in temporary system folders.*

---

## Development Conventions

### Project Architecture
- **src Layout:** All core logic resides in `src/autodiary/`.
  - `cli/`: Interactive menu systems and terminal rendering.
  - `core/`: Business logic, API clients, and configuration management.
  - `models/`: Pydantic schemas for data integrity.
  - `utils/`: Security (Crypto), validation, and helper modules.
- **Separation of Concerns:** Keep UI/Prompt logic strictly within `cli/` and API/Logic within `core/`.

### Safety & Stealth Standards
- **Bot Detection Evasion:** All API calls *must* use the `VTUApiClient` which implements:
  - Randomized base delays + jitter.
  - Modern Chrome/Windows User-Agent strings.
  - Standard browser headers (Referer, Origin, Accept-Language).
- **Defensive Programming:** Always use `dry_run` mode when testing new features to avoid unintended server-side modifications.

### Security Mandates
- **Credential Protection:** Never store passwords in plain text. Use `CryptoManager` for encryption.
- **Environment Isolation:** Keep `.env` and `.encryption_key` out of source control. Use templates in `src/autodiary/resources/templates/` for local setup.

---

## Technical Integrity
This project follows **Conventional Commits** (e.g., `feat:`, `fix:`, `refactor:`) and requires a manual smoke test for every PR until the automated test suite (`tests/`) is fully implemented. Refer to [AGENTS.md](./AGENTS.md) for detailed workflow instructions.
