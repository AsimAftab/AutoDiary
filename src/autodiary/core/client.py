"""
VTU API Client - Handles all communication with the VTU internship portal.
"""

import logging
import random
import time
from typing import Any

import requests

from autodiary.core.config import ConfigManager

LOGGER = logging.getLogger("autodiary")


class VTUApiClient:
    """Client for VTU Internship Portal API."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize API client.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.config = config_manager.config

        # API configuration
        api_config = config_manager.get_api_config()
        self.base_url = api_config["base_url"].rstrip("/")
        self.timeout = api_config["timeout"]
        self.delay_min = api_config["request_delay_min"]
        self.delay_max = api_config["request_delay_max"]
        self.max_retries = api_config["max_retries"]

        # Session
        self.session = requests.Session()

        # URLs
        self.login_url = f"{self.base_url}/api/v1/auth/login"
        self.diary_store_url = f"{self.base_url}/api/v1/student/internship-diaries/store"
        self.diary_list_url = f"{self.base_url}/api/v1/student/internship-diaries"
        self.internship_list_url = (
            f"{self.base_url}/api/v1/student/internship-applys?page=1&status=6"
        )

        # Retry settings
        self.retry_delay = 2.0
        self.auth_retry_delay = 0.5
        self.max_login_attempts = 3
        self.login_retry_delay = 1.0

        # Authentication state
        self._authenticated = False

        # Headers
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

    def login(self, email: str, password: str) -> bool:
        """
        Perform login to VTU portal.

        Args:
            email: User email
            password: User password

        Returns:
            True if login successful, False otherwise
        """
        for attempt in range(1, self.max_login_attempts + 1):
            try:
                LOGGER.info(f"Login attempt {attempt}/{self.max_login_attempts}")

                # Use randomized delay for login too
                if attempt > 1:
                    time.sleep(self.login_retry_delay + random.uniform(0.5, 2.0))

                response = self.session.post(
                    self.login_url,
                    headers=self.headers,
                    json={"email": email, "password": password},
                    timeout=self.timeout,
                )
                data = response.json() if response.content else {}

                if response.ok and data.get("success") is True:
                    LOGGER.info("Login successful")
                    self._authenticated = True
                    return True

                # Retry on transient server errors and auth failures (401, 429, 5xx)
                if response.status_code in (401, 429, 502, 503, 504):
                    LOGGER.warning(
                        f"Login attempt {attempt} failed: "
                        f"HTTP {response.status_code} | {data}"
                    )
                    if attempt < self.max_login_attempts:
                        continue
                    else:
                        LOGGER.error(
                            f"Login failed after {self.max_login_attempts} attempts "
                            f"with HTTP {response.status_code}"
                        )
                        self._authenticated = False
                        return False

                # Non-retryable client error (403, 404, etc.)
                LOGGER.error(f"Login failed: HTTP {response.status_code} | {data}")
                self._authenticated = False
                return False

            except Exception as exc:
                LOGGER.warning(f"Login failed on attempt {attempt}: {exc}")
                if attempt < self.max_login_attempts:
                    time.sleep(self.login_retry_delay)

        LOGGER.error(f"Login failed after {self.max_login_attempts} attempts")
        self._authenticated = False
        return False

    def _ensure_authenticated(self) -> bool:
        """
        Ensure session is authenticated, logging in if necessary.

        Returns:
            True if authenticated, False otherwise
        """
        if self._authenticated:
            LOGGER.debug("Already authenticated, skipping login")
            return True

        credentials = self.config_manager.get_credentials()
        return self.login(credentials["email"], credentials["password"])

    def test_connection(self) -> bool:
        """
        Test connection to VTU API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            credentials = self.config_manager.get_credentials()
            if not self.login(credentials["email"], credentials["password"]):
                return False

            # Try to fetch diary list
            response = self.session.get(
                self.diary_list_url,
                headers=self.headers,
                timeout=self.timeout,
            )
            return response.ok
        except Exception as e:
            LOGGER.error(f"Connection test failed: {e}")
            return False

    def get_access_token(self) -> str | None:
        """
        Get current access token from session cookies.

        Returns:
            Access token if available, None otherwise
        """
        return self.session.cookies.get("access_token")

    def _paginate_diary_list(self) -> list[dict[str, Any]]:
        """
        Paginate through the diary list API and return all items.

        Returns:
            List of diary item dictionaries from all pages

        Raises:
            ValueError: If login or API request fails
        """
        if not self._ensure_authenticated():
            raise ValueError("Login failed while fetching diary list")

        all_items: list[dict[str, Any]] = []
        page = 1

        while True:
            url = f"{self.diary_list_url}?page={page}"
            response = self.session.get(url, headers=self.headers, timeout=self.timeout)

            if not response.ok:
                raise ValueError(f"Fetch failed: HTTP {response.status_code}")

            data = response.json() if response.content else {}
            if not data.get("success"):
                raise ValueError(f"API error: {data}")

            payload = data.get("data", {})
            items = []
            next_page_url = None

            if isinstance(payload, dict):
                items = payload.get("data", [])
                next_page_url = payload.get("next_page_url")
            elif isinstance(payload, list):
                items = payload

            all_items.extend(items)

            if not next_page_url:
                break

            page += 1
            time.sleep(0.3)

        return all_items

    def fetch_existing_dates(self) -> set[str]:
        """
        Fetch all existing diary dates from server.

        Returns:
            Set of date strings (YYYY-MM-DD format)
        """
        try:
            items = self._paginate_diary_list()
            dates = {
                str(item["date"])
                for item in items
                if isinstance(item, dict) and item.get("date")
            }
            LOGGER.info(f"Fetched {len(dates)} existing diary dates")
            return dates
        except Exception as e:
            LOGGER.error(f"Failed to fetch existing dates: {e}")
            return set()

    def fetch_all_entries(self) -> list[dict[str, Any]]:
        """
        Fetch all diary entries from server.

        Returns:
            List of diary entry dictionaries
        """
        try:
            entries = self._paginate_diary_list()
            LOGGER.info(f"Fetched {len(entries)} diary entries")
            return entries
        except Exception as e:
            LOGGER.error(f"Failed to fetch entries: {e}")
            return []

    def upload_entry(self, entry: dict[str, Any]) -> tuple[bool, str]:
        """
        Upload a single diary entry with human-like delays.

        Args:
            entry: Diary entry dictionary

        Returns:
            Tuple of (success, message)
        """
        try:
            # Human-like delay: Base random delay + small jitter
            # Industry standard to avoid simple threshold detection
            base_delay = random.uniform(self.delay_min, self.delay_max)
            jitter = random.uniform(0.1, 0.8)
            total_delay = base_delay + jitter

            LOGGER.info(f"Applying safety delay of {total_delay:.2f}s...")
            time.sleep(total_delay)

            # Attempt upload with retries
            for attempt in range(1, self.max_retries + 1):
                try:
                    LOGGER.info(
                        f"Uploading entry for {entry.get('date')} (attempt {attempt}/{self.max_retries})"
                    )

                    response = self.session.post(
                        self.diary_store_url,
                        headers=self.headers,
                        json=entry,
                        timeout=self.timeout,
                    )

                    data = response.json() if response.content else {}

                    if response.ok and data.get("success") is True:
                        message = data.get("message", "Created successfully")
                        LOGGER.info(f"Upload successful: {message}")

                        # Extra small delay after success to not look mechanical
                        time.sleep(random.uniform(0.5, 1.5))
                        return True, message

                    # Check if retryable error (e.g., Server Overload or Rate Limit)
                    if response.status_code >= 500 or response.status_code == 429:
                        if attempt < self.max_retries:
                            # Exponential backoff for safety
                            wait_time = self.retry_delay * (2 ** (attempt - 1)) + random.uniform(
                                0.5, 2.0
                            )
                            LOGGER.warning(
                                f"Server busy (HTTP {response.status_code}), cooling down for {wait_time:.2f}s..."
                            )
                            time.sleep(wait_time)
                            continue

                    # Non-retryable error
                    error_msg = data.get("message", "Unknown error")
                    LOGGER.error(f"Upload failed: HTTP {response.status_code} | {error_msg}")
                    return False, error_msg

                except requests.RequestException as e:
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay + random.uniform(1.0, 3.0)
                        LOGGER.warning(f"Network issue: {e}, retrying in {wait_time:.2f}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        LOGGER.error(f"Upload failed after retries: {e}")
                        return False, str(e)

            return False, "Max retries exceeded"

        except Exception as e:
            LOGGER.error(f"Unexpected error during upload: {e}")
            return False, str(e)

    def upload_entries(
        self, entries: list[dict[str, Any]], dry_run: bool = False
    ) -> dict[str, int]:
        """
        Upload multiple diary entries.

        Args:
            entries: List of diary entries to upload
            dry_run: If True, validate without uploading

        Returns:
            Dictionary with success, failed, and skipped counts
        """
        results = {"success": 0, "failed": 0, "skipped": 0}

        if not entries:
            LOGGER.info("No entries to upload")
            return results

        # Login before uploading
        if not dry_run:
            credentials = self.config_manager.get_credentials()
            if not self.login(credentials["email"], credentials["password"]):
                raise ValueError("Login failed. Cannot upload entries.")

        # Get existing dates to skip duplicates
        existing_dates = set()
        if self.config.auto_skip_existing and not dry_run:
            existing_dates = self.fetch_existing_dates()
            LOGGER.info(f"Found {len(existing_dates)} existing entries on server")

        # Upload each entry
        for i, entry in enumerate(entries, start=1):
            entry_date = entry.get("date", "")
            LOGGER.info(f"Processing entry {i}/{len(entries)}: {entry_date}")

            # Check if already exists
            if entry_date in existing_dates:
                LOGGER.info(f"Skipping {entry_date} - already exists on server")
                results["skipped"] += 1
                continue

            if dry_run:
                LOGGER.info(f"[DRY RUN] Would upload entry for {entry_date}")
                results["success"] += 1
                continue

            # Upload entry
            success, message = self.upload_entry(entry)
            if success:
                results["success"] += 1
                existing_dates.add(entry_date)  # Add to avoid duplicates
            else:
                results["failed"] += 1

        return results

    def get_internship_id(self) -> int:
        """Get internship ID from configuration."""
        return self.config.internship_id

    def get_holiday_config(self) -> dict[str, Any]:
        """Get holiday configuration."""
        return self.config_manager.get_holiday_config()

    def get_internship_config(self) -> dict[str, Any]:
        """Get internship configuration."""
        return self.config_manager.get_internship_config()

    def fetch_internships(self) -> dict[str, Any]:
        """
        Fetch available internships for the authenticated user.

        Returns:
            Parsed JSON response dictionary from the internship API
        """
        response = self.session.get(
            self.internship_list_url,
            headers=self.headers,
            timeout=self.timeout,
        )
        if response.ok:
            return response.json() if response.content else {}
        return {}
