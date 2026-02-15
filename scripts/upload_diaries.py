#!/usr/bin/env python3
import json
import logging
import os
import random
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from dotenv import load_dotenv
import typer


REQUIRED_ENTRY_KEYS = [
    "description",
    "hours",
    "links",
    "blockers",
    "learnings",
    "mood_slider",
    "skill_ids",
]

WEEKDAY_NAME_TO_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

LOGGER = logging.getLogger("autodiary")
app = typer.Typer(add_completion=False, help="VTU AutoDiary CLI")


def setup_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_csv_env(name: str) -> List[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def parse_date_value(raw: str) -> date:
    value = str(raw).strip().lower()
    if value == "today":
        return date.today()
    return datetime.strptime(str(raw).strip(), "%Y-%m-%d").date()


class AutoDiaryClient:
    def __init__(self, settings_path: Path, entries_path: Path, env_path: Path) -> None:
        LOGGER.info("Loading settings from %s", settings_path)
        self.settings = load_json(settings_path)
        LOGGER.info("Loading entries from %s", entries_path)
        self.entries = load_json(entries_path)
        if not isinstance(self.entries, list):
            raise ValueError("Entries file must contain a JSON array")

        self.env_path = env_path
        load_dotenv(dotenv_path=env_path if env_path.exists() else None)

        self.api = self.settings["api"]
        self.defaults = self.settings["defaults"]
        self.auth_mode = self.settings["auth"].get("mode", "cookie").lower()
        self.headers = self._build_headers(self.settings)
        self.session = requests.Session()

        self.base_url = self.api["base_url"].rstrip("/")
        self.store_url = f"{self.base_url}{self.api['diary_store_path']}"
        self.timeout = int(self.api.get("timeout_seconds", 30))

        self.delay_min = float(self.api.get("request_delay_min_seconds", 0.8))
        self.delay_max = float(self.api.get("request_delay_max_seconds", 1.5))
        self.max_retries = int(self.api.get("max_retries", 3))
        self.retry_delay = float(self.api.get("retry_delay_seconds", 2.0))
        self.auth_retry_delay = float(self.api.get("auth_retry_delay_seconds", 0.5))
        self.max_login_attempts = int(self.api.get("max_login_attempts", 3))
        self.login_retry_delay = float(self.api.get("login_retry_delay_seconds", 1.0))
        self.internship_id = self.defaults["internship_id"]

        self._validate_runtime_config()

    def _validate_runtime_config(self) -> None:
        if self.delay_min < 0 or self.delay_max < 0 or self.delay_min > self.delay_max:
            raise ValueError("request delay range is invalid; ensure min/max are non-negative and min <= max")
        if self.max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        if self.retry_delay < 0:
            raise ValueError("retry_delay_seconds must be >= 0")
        if self.auth_retry_delay < 0:
            raise ValueError("auth_retry_delay_seconds must be >= 0")
        if self.max_login_attempts < 1:
            raise ValueError("max_login_attempts must be >= 1")
        if self.login_retry_delay < 0:
            raise ValueError("login_retry_delay_seconds must be >= 0")

    @staticmethod
    def _build_headers(settings: Dict[str, Any]) -> Dict[str, str]:
        auth = settings["auth"]
        headers = dict(auth.get("headers", {}))
        mode = auth.get("mode", "cookie").lower()
        if mode == "bearer":
            token = auth.get("access_token", "").strip()
            if not token:
                raise ValueError("auth.access_token is required for bearer mode")
            headers["Authorization"] = f"Bearer {token}"
        elif mode == "cookie":
            cookie = auth.get("cookie", "").strip()
            if not cookie:
                token = auth.get("access_token", "").strip()
                if token:
                    cookie = f"access_token={token}"
            if not cookie:
                raise ValueError("Provide auth.cookie or auth.access_token for cookie mode")
            headers["Cookie"] = cookie
        elif mode == "login":
            pass
        else:
            raise ValueError("auth.mode must be 'cookie', 'bearer', or 'login'")
        return headers

    @staticmethod
    def _is_auth_expired(response: requests.Response, data: Dict[str, Any]) -> bool:
        if response.status_code == 401:
            return True
        code = str(data.get("code", "")).upper()
        message = str(data.get("message", "")).lower()
        if code in {"UNAUTHENTICATED", "TOKEN_EXPIRED", "INVALID_TOKEN"}:
            return True
        return "token" in message and ("expired" in message or "invalid" in message or "unauth" in message)

    @staticmethod
    def _validate_entry(entry: Dict[str, Any], index: int) -> None:
        missing = [k for k in REQUIRED_ENTRY_KEYS if k not in entry]
        if missing:
            raise ValueError(f"Entry #{index} missing keys: {missing}")
        if "date" in entry and str(entry["date"]).strip():
            try:
                datetime.strptime(str(entry["date"]), "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError(f"Entry #{index} has invalid date '{entry['date']}', expected YYYY-MM-DD") from exc

    def login_once(self) -> None:
        email = os.getenv("VTU_EMAIL", "").strip()
        password = os.getenv("VTU_PASSWORD", "").strip()
        if not email or not password:
            raise ValueError("Set VTU_EMAIL and VTU_PASSWORD in .env or environment variables")

        login_path = self.api.get("login_path", "/api/v1/auth/login")
        login_url = f"{self.base_url}{login_path}"
        response = self.session.post(
            login_url,
            headers={"Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=self.timeout,
        )
        data = response.json() if response.content else {}
        if not response.ok or data.get("success") is not True:
            raise ValueError(f"Login failed: HTTP {response.status_code} | {data}")
        if "access_token" not in self.session.cookies:
            raise ValueError("Login succeeded but access_token cookie was not set")

    def login_with_guard(self) -> None:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_login_attempts + 1):
            try:
                LOGGER.info("Login attempt %s/%s", attempt, self.max_login_attempts)
                self.login_once()
                return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.max_login_attempts:
                    LOGGER.warning("Login failed on attempt %s: %s", attempt, exc)
                    if self.login_retry_delay > 0:
                        time.sleep(self.login_retry_delay)
                else:
                    LOGGER.error("Login failed after %s attempts. Stopping execution.", self.max_login_attempts)
        if last_error is not None:
            raise last_error

    def request_with_reauth(
        self,
        method: str,
        url: str,
        json_payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[requests.Response, Dict[str, Any]]:
        response = self.session.request(
            method=method,
            url=url,
            headers=self.headers,
            json=json_payload,
            timeout=self.timeout,
        )
        data = response.json() if response.content else {}
        if self.auth_mode != "login":
            return response, data

        if self._is_auth_expired(response, data):
            LOGGER.warning("Auth appears expired (HTTP %s). Re-authenticating and retrying request.", response.status_code)
            self.login_with_guard()
            if self.auth_retry_delay > 0:
                LOGGER.info("Sleeping %.2fs after re-login before retry", self.auth_retry_delay)
                time.sleep(self.auth_retry_delay)
            response = self.session.request(
                method=method,
                url=url,
                headers=self.headers,
                json=json_payload,
                timeout=self.timeout,
            )
            data = response.json() if response.content else {}
        return response, data

    def fetch_existing_dates(self) -> Set[str]:
        list_path = self.api.get("diary_list_path", "/api/v1/student/internship-diaries")
        page = 1
        dates: Set[str] = set()
        while True:
            url = f"{self.base_url}{list_path}?page={page}"
            response, data = self.request_with_reauth("GET", url)
            if not response.ok or data.get("success") is not True:
                raise ValueError(f"Fetch diaries failed: HTTP {response.status_code} | {data}")

            payload = data.get("data", {})
            next_page_url = None
            if isinstance(payload, dict):
                items: List[Dict[str, Any]] = payload.get("data", [])
                next_page_url = payload.get("next_page_url")
            elif isinstance(payload, list):
                items = payload
            else:
                items = []

            for item in items:
                if isinstance(item, dict) and item.get("date"):
                    dates.add(str(item["date"]))

            if not next_page_url:
                break
            page += 1
        return dates

    def build_holiday_filters(self) -> Tuple[Set[int], Set[str]]:
        configured_weekdays = self.defaults.get("holiday_weekdays", [])
        configured_dates = self.defaults.get("holiday_dates", [])
        env_weekdays = parse_csv_env("HOLIDAY_WEEKDAYS")
        env_dates = parse_csv_env("HOLIDAY_DATES")

        weekday_names = list(configured_weekdays) + env_weekdays
        holiday_dates = set(list(configured_dates) + env_dates)
        weekday_indexes: Set[int] = set()
        for day in weekday_names:
            idx = WEEKDAY_NAME_TO_INDEX.get(str(day).strip().lower())
            if idx is None:
                raise ValueError(f"Invalid holiday weekday: {day}")
            weekday_indexes.add(idx)
        return weekday_indexes, holiday_dates

    @staticmethod
    def is_holiday(date_str: str, holiday_weekdays: Set[int], holiday_dates: Set[str]) -> bool:
        if date_str in holiday_dates:
            return True
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.weekday() in holiday_weekdays

    def build_working_dates(self, holiday_weekdays: Set[int], holiday_dates: Set[str]) -> List[str]:
        start_raw = self.defaults.get("internship_start_date")
        end_raw = self.defaults.get("internship_end_date", "today")
        if not start_raw:
            raise ValueError("defaults.internship_start_date is required when auto date assignment is used")
        start_date = parse_date_value(start_raw)
        end_date = parse_date_value(end_raw)
        if start_date > end_date:
            raise ValueError("internship_start_date cannot be after internship_end_date")

        result: List[str] = []
        cursor = start_date
        while cursor <= end_date:
            d = cursor.isoformat()
            if not self.is_holiday(d, holiday_weekdays, holiday_dates):
                result.append(d)
            cursor += timedelta(days=1)
        return result

    def assign_missing_dates(self, candidate_dates: List[str], existing_dates: Set[str]) -> None:
        already_used = {
            str(entry["date"])
            for entry in self.entries
            if "date" in entry and str(entry["date"]).strip()
        }
        available = [d for d in candidate_dates if d not in existing_dates and d not in already_used]
        pointer = 0
        for i, entry in enumerate(self.entries, start=1):
            if "date" in entry and str(entry["date"]).strip():
                continue
            if pointer >= len(available):
                raise ValueError(
                    "Not enough working dates available to auto-assign all entries. "
                    "Reduce entries or extend internship_end_date."
                )
            entry["date"] = available[pointer]
            LOGGER.info("[AUTO-DATE] Entry #%s -> %s", i, entry["date"])
            pointer += 1

    def build_payload(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "internship_id": entry.get("internship_id", self.internship_id),
            "date": entry["date"],
            "description": entry["description"],
            "hours": entry["hours"],
            "links": entry["links"],
            "blockers": entry["blockers"],
            "learnings": entry["learnings"],
            "mood_slider": entry["mood_slider"],
            "skill_ids": entry["skill_ids"],
        }

    def submit_with_retries(self, entry_index: int, payload: Dict[str, Any]) -> bool:
        delay = random.uniform(self.delay_min, self.delay_max)
        LOGGER.info("Sleeping %.2fs before POST entry #%s", delay, entry_index)
        time.sleep(delay)

        for attempt in range(1, self.max_retries + 1):
            try:
                LOGGER.info(
                    "Posting entry #%s for %s (attempt %s/%s)",
                    entry_index,
                    payload["date"],
                    attempt,
                    self.max_retries,
                )
                response, data = self.request_with_reauth("POST", self.store_url, json_payload=payload)
                if response.ok and data.get("success") is True:
                    LOGGER.info("[OK] Entry #%s (%s): %s", entry_index, payload["date"], data.get("message", "Created"))
                    return True

                retryable_status = response.status_code >= 500 or response.status_code == 429
                if attempt < self.max_retries and retryable_status:
                    LOGGER.warning(
                        "[RETRY] Entry #%s (%s): HTTP %s. Retrying in %.1fs",
                        entry_index,
                        payload["date"],
                        response.status_code,
                        self.retry_delay,
                    )
                    time.sleep(self.retry_delay)
                    continue

                LOGGER.error(
                    "[FAIL] Entry #%s (%s): HTTP %s | %s",
                    entry_index,
                    payload["date"],
                    response.status_code,
                    data,
                )
                return False
            except requests.RequestException as exc:
                if attempt < self.max_retries:
                    LOGGER.warning(
                        "[RETRY] Entry #%s (%s): %s. Retrying in %.1fs",
                        entry_index,
                        payload["date"],
                        exc,
                        self.retry_delay,
                    )
                    time.sleep(self.retry_delay)
                    continue
                LOGGER.error("[ERROR] Entry #%s (%s): %s", entry_index, payload["date"], exc)
                return False
        return False

    def run(
        self,
        dry_run: bool,
        login_only: bool,
        show_access_token: bool,
        print_existing: bool,
        auto_dates: bool,
    ) -> None:
        has_missing_dates = any("date" not in e or not str(e.get("date", "")).strip() for e in self.entries)
        auto_dates_enabled = auto_dates or has_missing_dates
        idempotency_enabled = True

        needs_auth_call = login_only or print_existing or not dry_run or auto_dates_enabled or idempotency_enabled
        if self.auth_mode == "login" and needs_auth_call:
            LOGGER.info("Authenticating using login endpoint")
            self.login_with_guard()
            if show_access_token:
                LOGGER.info("access_token=%s", self.session.cookies.get("access_token", ""))
            if login_only:
                LOGGER.info("Login successful.")
                return

        existing_dates: Set[str] = set()
        if idempotency_enabled or print_existing or auto_dates_enabled:
            LOGGER.info("Fetching existing diary dates from server")
            existing_dates = self.fetch_existing_dates()
            LOGGER.info("Fetched %s existing diary dates", len(existing_dates))
            if print_existing:
                LOGGER.info("Existing dates:\n%s", json.dumps(sorted(existing_dates), indent=2))
                if dry_run:
                    return

        holiday_weekdays, holiday_dates = self.build_holiday_filters()
        LOGGER.info("Holiday weekdays=%s holiday_dates=%s", sorted(holiday_weekdays), sorted(holiday_dates))
        if auto_dates_enabled:
            working_dates = self.build_working_dates(holiday_weekdays, holiday_dates)
            LOGGER.info("Auto-date enabled. Candidate working dates available: %s", len(working_dates))
            self.assign_missing_dates(working_dates, existing_dates)

        ok_count = 0
        fail_count = 0
        skipped_count = 0

        for i, entry in enumerate(self.entries, start=1):
            self._validate_entry(entry, i)
            payload = self.build_payload(entry)

            if self.is_holiday(payload["date"], holiday_weekdays, holiday_dates):
                skipped_count += 1
                LOGGER.info("[SKIP] Entry #%s (%s): configured holiday", i, payload["date"])
                continue

            if payload["date"] in existing_dates:
                skipped_count += 1
                LOGGER.info("[SKIP] Entry #%s (%s): already filled", i, payload["date"])
                continue

            if dry_run:
                LOGGER.info("[DRY-RUN] Would POST entry #%s for %s", i, payload["date"])
                continue

            success = self.submit_with_retries(i, payload)
            if success:
                ok_count += 1
                existing_dates.add(payload["date"])
            else:
                fail_count += 1

        if dry_run:
            LOGGER.info("Dry run completed.")
        else:
            LOGGER.info("Completed. Success: %s, Failed: %s, Skipped: %s", ok_count, fail_count, skipped_count)


def _make_client(settings: str, entries: str, env_file: str, log_level: str) -> AutoDiaryClient:
    setup_logging(log_level)
    return AutoDiaryClient(Path(settings), Path(entries), Path(env_file))


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context,
    settings: str = typer.Option("config/settings.json", help="Path to settings JSON"),
    entries: str = typer.Option("entries/diary_entries.json", help="Path to entries JSON"),
    env_file: str = typer.Option(".env", help="Path to .env file"),
    log_level: str = typer.Option("INFO", help="Logging level: DEBUG, INFO, WARNING, ERROR"),
    dry_run: bool = typer.Option(False, help="Legacy: same as run --dry-run"),
    login_only: bool = typer.Option(False, help="Legacy: same as login"),
    show_access_token: bool = typer.Option(False, help="Print access_token from login cookie"),
    print_existing: bool = typer.Option(False, help="Legacy: same as existing"),
    auto_dates: bool = typer.Option(False, help="Legacy: same as run --auto-dates"),
) -> None:
    # Keep old command style working when no explicit subcommand is provided.
    if ctx.invoked_subcommand is not None:
        return
    client = _make_client(settings, entries, env_file, log_level)
    client.run(
        dry_run=dry_run,
        login_only=login_only,
        show_access_token=show_access_token,
        print_existing=print_existing,
        auto_dates=auto_dates,
    )


@app.command("run")
def run_command(
    settings: str = typer.Option("config/settings.json", help="Path to settings JSON"),
    entries: str = typer.Option("entries/diary_entries.json", help="Path to entries JSON"),
    env_file: str = typer.Option(".env", help="Path to .env file"),
    log_level: str = typer.Option("INFO", help="Logging level: DEBUG, INFO, WARNING, ERROR"),
    dry_run: bool = typer.Option(False, help="Validate and print without sending"),
    auto_dates: bool = typer.Option(False, help="Auto-assign missing dates"),
) -> None:
    client = _make_client(settings, entries, env_file, log_level)
    client.run(
        dry_run=dry_run,
        login_only=False,
        show_access_token=False,
        print_existing=False,
        auto_dates=auto_dates,
    )


@app.command("login")
def login_command(
    settings: str = typer.Option("config/settings.json", help="Path to settings JSON"),
    entries: str = typer.Option("entries/diary_entries.json", help="Path to entries JSON"),
    env_file: str = typer.Option(".env", help="Path to .env file"),
    log_level: str = typer.Option("INFO", help="Logging level: DEBUG, INFO, WARNING, ERROR"),
    show_access_token: bool = typer.Option(False, help="Print access_token after login"),
) -> None:
    client = _make_client(settings, entries, env_file, log_level)
    client.run(
        dry_run=False,
        login_only=True,
        show_access_token=show_access_token,
        print_existing=False,
        auto_dates=False,
    )


@app.command("existing")
def existing_command(
    settings: str = typer.Option("config/settings.json", help="Path to settings JSON"),
    entries: str = typer.Option("entries/diary_entries.json", help="Path to entries JSON"),
    env_file: str = typer.Option(".env", help="Path to .env file"),
    log_level: str = typer.Option("INFO", help="Logging level: DEBUG, INFO, WARNING, ERROR"),
) -> None:
    client = _make_client(settings, entries, env_file, log_level)
    client.run(
        dry_run=True,
        login_only=False,
        show_access_token=False,
        print_existing=True,
        auto_dates=False,
    )


@app.command("interactive")
def interactive_command(
    settings: str = typer.Option("config/settings.json", help="Path to settings JSON"),
    entries: str = typer.Option("entries/diary_entries.json", help="Path to entries JSON"),
    env_file: str = typer.Option(".env", help="Path to .env file"),
    log_level: str = typer.Option("INFO", help="Logging level: DEBUG, INFO, WARNING, ERROR"),
) -> None:
    client = _make_client(settings, entries, env_file, log_level)
    mode = typer.prompt("Mode [run/login/existing]", default="run").strip().lower()
    if mode == "login":
        show_token = typer.confirm("Show access token?", default=False)
        client.run(
            dry_run=False,
            login_only=True,
            show_access_token=show_token,
            print_existing=False,
            auto_dates=False,
        )
        return
    if mode == "existing":
        client.run(
            dry_run=True,
            login_only=False,
            show_access_token=False,
            print_existing=True,
            auto_dates=False,
        )
        return
    dry_run = typer.confirm("Dry run?", default=True)
    auto_dates = typer.confirm("Auto-assign dates?", default=True)
    client.run(
        dry_run=dry_run,
        login_only=False,
        show_access_token=False,
        print_existing=False,
        auto_dates=auto_dates,
    )


if __name__ == "__main__":
    app()
