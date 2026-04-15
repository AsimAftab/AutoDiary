# AutoDiary — Improvement Tracker

Consolidated list of bugs, security concerns, code quality issues, test gaps, UX improvements, and missing features identified across the codebase.

**Legend:** `[ ]` = open, `[x]` = done

---

## Bugs

- [x] **B1 — Stale session cookies on login failure**
  `src/autodiary/core/client.py:98-121`
  Session cookies are not cleared when login fails. Stale auth state from a previous attempt can pollute retries. Fix: call `self.session.cookies.clear()` on auth failure paths.

- [x] **B2 — Pagination infinite loop risk**
  `src/autodiary/core/client.py:194-221`
  `_paginate_diary_list()` has no max page guard. If the API returns a cyclic or always-present `next_page_url`, the loop never terminates. Fix: add a `max_pages` safety limit.

- [x] **B3 — `_fetch_user_internships()` can return `None`**
  `src/autodiary/cli/config_menu.py:537-568`
  Some exit paths return implicit `None` instead of `[]`. Downstream code expects a list and will crash on iteration. Fix: ensure all paths return `[]`.

- [x] **B4 — Reverse date range not caught early**
  `src/autodiary/cli/upload_menu.py:141-168`
  If the user enters end < start, it is not caught until after they confirm the upload. `_generate_working_dates()` silently returns an empty list. Fix: validate immediately after input and show a warning.

- [x] **B5 — CSV export column ordering**
  `src/autodiary/cli/view_menu.py:261`
  Columns are sorted alphabetically instead of logical order (date, description, hours, ...). Fix: define an explicit field order list.

- [x] **B6 — Whitespace-only skill IDs silently dropped**
  `src/autodiary/models/entry.py:34-41`
  `validate_skill_ids()` strips and filters but never raises if all IDs become empty. Fix: raise `ValueError` when stripped list is empty or shorter than input.

---

## Security

- [x] **S1 — Encryption key permissions not verified on read** *(High)*
  `src/autodiary/utils/crypto.py:47-60`
  On load, the existing `.encryption_key` file is read without checking permissions. An attacker could pre-create the file with a known key. Fix: verify file permissions on read (note: limited enforcement on Windows).

- [x] **S2 — Browser-spoofing headers** *(Medium)*
  `src/autodiary/core/client.py:59-69`
  Hardcoded Chrome User-Agent and `sec-ch-ua` headers impersonate a real browser. This may violate the portal's Terms of Service. Fix: replace with an honest `AutoDiary/1.0.0` User-Agent or make configurable.

- [x] **S3 — No input trimming on credentials**
  `src/autodiary/cli/config_menu.py:446,512`
  Email and internship title taken from user input without `.strip()`. Leading/trailing whitespace can cause silent login failures. Fix: trim all user-provided strings.

---

## Code Quality

- [x] **CQ1 — Broad `except Exception` handlers**
  `src/autodiary/core/client.py` (lines 123-130, 232-241, 250-256, 332-334)
  All exceptions are caught uniformly, masking bugs like `TypeError` or `KeyError`. Fix: catch `requests.RequestException`, `json.JSONDecodeError`, etc. separately, and let programming errors propagate.

- [x] **CQ2 — Magic numbers**
  `src/autodiary/core/client.py:50-53,88,271-272`, `src/autodiary/cli/upload_menu.py:436`
  Hardcoded retry delays, jitter ranges, display limits (`[:10]`), and API status codes (`6`). Fix: extract to named constants or config fields.

- [x] **CQ3 — Duplicated date validation logic**
  `src/autodiary/cli/upload_menu.py`, `src/autodiary/cli/view_menu.py`, `src/autodiary/cli/config_menu.py`, `src/autodiary/utils/validators.py`
  `datetime.strptime(val, "%Y-%m-%d")` pattern repeated in 4+ places. Fix: consolidate into a single `parse_date()` helper in `validators.py` and import everywhere.

- [x] **CQ4 — Lazy config loading in getters**
  `src/autodiary/core/config.py:152-162,174-177,186-195,204-213`
  Getter methods like `get_password()` implicitly call `load()`, which can raise `FileNotFoundError` or `ValueError`. Callers don't expect these from a getter. Fix: load config once at init; fail fast.

- [x] **CQ5 — No static type checking configured**
  `pyproject.toml`
  Type hints exist throughout the codebase but no mypy/pyright is configured to validate them. Fix: add `mypy` to dev dependencies and a `[tool.mypy]` section.

- [x] **CQ6 — Inconsistent error handling patterns**
  Multiple CLI files
  Some paths log + return `False`, others log + raise, others swallow silently. Fix: adopt a consistent pattern (e.g., log + `print_error` + return `None`/`False`).

---

## Test Coverage Gaps

- [x] **T1 — No CLI integration tests**
  `main_menu.py`, `upload_menu.py`, `view_menu.py`, `config_menu.py` have zero test coverage. Fix: add tests with mocked `questionary` and `Console` for each menu's core flows.

- [x] **T2 — No upload error-path tests**
  `tests/test_client.py`
  Missing scenarios: partial batch failure, network timeout, HTTP 429 rate limit, auth loss mid-upload. Fix: add parameterized tests with `unittest.mock.patch`.

- [x] **T3 — No date generation edge-case tests**
  Missing tests for: single-day range, leap year boundaries, overlapping holiday weekday + specific date. Fix: add `tests/test_date_logic.py`.

- [x] **T4 — No CSV export tests**
  Missing tests for: column ordering, special characters (commas, quotes, newlines), empty entry list, entries with missing optional fields. Fix: add to `tests/test_view_menu.py`.

- [x] **T5 — No statistics calculation tests**
  Missing tests for: average mood, total hours, skill aggregation, empty input. Fix: add to `tests/test_view_menu.py`.

- [x] **T6 — No coverage reporting configured**
  `pyproject.toml`
  `pytest-cov` is not in dev dependencies and no coverage config exists. Fix: add `pytest-cov` and configure `--cov=src/autodiary`.

---

## UX Improvements

- [x] **UX1 — Show upload/skip counts before confirmation**
  `src/autodiary/cli/upload_menu.py`
  User sees generic "Proceed with upload?" without knowing how many entries will upload vs. skip. Fix: show "Upload 12 entries (skipping 3 existing). Proceed?"

- [x] **UX2 — Spinner for long-running fetches**
  `src/autodiary/cli/config_menu.py:128-176`
  No progress indicator while fetching internships during setup wizard. Fix: wrap API calls in a Rich spinner.

- [x] **UX3 — Actionable error messages**
  `src/autodiary/cli/upload_menu.py:99-102`
  Errors say what failed but not what to do next. Fix: append guidance like "Try Configuration > Test Connection to diagnose."

- [x] **UX4 — Dry-run should preview date assignments**
  `src/autodiary/cli/upload_menu.py`
  Current dry-run only validates entries. Fix: show a table of entry-to-date assignments so the user knows what *would* happen.

- [x] **UX5 — Skill search/filter**
  `src/autodiary/cli/main_menu.py`
  100+ skills displayed with no search. Fix: add a text filter prompt before showing the full list.

- [x] **UX6 — Clarify holiday exclusion prompt**
  `src/autodiary/cli/config_menu.py:316-324`
  "Select weekend days" is ambiguous — user might think they're marking *working* days. Fix: rephrase to "Select days to EXCLUDE from uploads."

- [x] **UX7 — Detailed failed-entry review after upload**
  `src/autodiary/cli/upload_menu.py:434-439`
  Only first 10 failures shown, no detail view. Fix: offer "Review failed entries in detail?" prompt after batch upload.

---

## Missing Features

- [x] **F1 — Resume interrupted uploads**
  No state is saved during batch uploads. If interrupted, the user must start over. Fix: persist upload progress to a temp file; offer to resume on next run.

- [x] **F2 — Entry de-duplication**
  No detection of duplicate entries (same description + date). Fix: hash-check before upload and warn the user.

- [x] **F3 — Internship date cross-validation**
  `src/autodiary/models/config.py:20-23`
  `internship_start_date` and `internship_end_date` are not validated as real dates, and start > end is not caught. Fix: add a Pydantic `model_validator` to parse and compare.

- [x] **F4 — API response schema validation**
  `src/autodiary/core/client.py`
  API responses are consumed as raw dicts. If the schema changes, data is silently lost. Fix: define Pydantic models for API responses.

- [x] **F5 — Connection pooling / retry adapter**
  `src/autodiary/core/client.py:39`
  `requests.Session()` created without `HTTPAdapter` or `urllib3.Retry`. Fix: configure session-level retry strategy.

- [x] **F6 — Config backup and restore**
  No way to back up or restore `~/.autodiary/config.json`. If corrupted, user must reconfigure from scratch. Fix: add backup/restore option in ConfigMenu.
