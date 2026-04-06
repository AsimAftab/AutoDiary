"""
Upload Menu - Handle diary entry upload operations.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import questionary
from rich.console import Console
from rich.panel import Panel

from autodiary.cli.utils import (
    create_progress_bar,
    format_hours,
    format_mood,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
)
from autodiary.core.client import VTUApiClient

console = Console()


class UploadMenu:
    """Upload menu for diary entries."""

    def __init__(self, config_manager):
        """Initialize upload menu."""
        self.config_manager = config_manager

    def show(self) -> None:
        """Display upload menu."""
        while True:
            choice = questionary.select(
                "Upload Diaries",
                choices=[
                    {"name": "Upload with Auto-Dates", "value": "auto"},
                    {"name": "Upload Specific Date Range", "value": "range"},
                    {"name": "Dry Run (Validate Only)", "value": "dry"},
                    {"name": "Upload from File", "value": "file"},
                    {"name": "Interactive Upload", "value": "interactive"},
                    {"name": "← Back to Main Menu", "value": "back"},
                ],
                use_indicator=True,
            ).ask()

            if not choice or choice == "back":
                break

            if choice == "auto":
                self.upload_with_auto_dates()
            elif choice == "range":
                self.upload_date_range()
            elif choice == "dry":
                self.dry_run_upload()
            elif choice == "file":
                self.upload_from_file()
            elif choice == "interactive":
                self.interactive_upload()

    def upload_with_auto_dates(
        self,
        dry_run: bool = False,
        start_date: str | None = None,
        end_date: str | None = None,
        entries: list[dict[str, Any]] | None = None,
    ) -> None:
        """Upload entries with automatic date assignment.

        Args:
            dry_run: If True, validate without uploading
            start_date: Optional custom start date (YYYY-MM-DD), overrides internship config
            end_date: Optional custom end date (YYYY-MM-DD), overrides internship config
            entries: Optional pre-loaded entries; if None, prompts user for a file
        """
        console.print()
        print_header("📤 Upload with Auto-Dates")

        if entries is None:
            # Get entries file
            entries_path = self._get_entries_file()
            if not entries_path:
                return

            entries = self._load_entries(entries_path)
            if not entries:
                return

        # Get configuration
        client = VTUApiClient(self.config_manager)
        try:
            internship = client.get_internship_config()
            holidays = client.get_holiday_config()
        except Exception as e:
            print_error(f"Failed to fetch configuration from server: {e}")
            questionary.press_any_key_to_continue().ask()
            return

        # Use custom date range if provided, otherwise use internship config
        date_start = start_date if start_date else internship["start_date"]
        date_end = end_date if end_date else internship["end_date"]

        # Generate working dates
        working_dates = self._generate_working_dates(date_start, date_end, holidays)

        if not working_dates:
            print_error("No working dates available in the specified range")
            return

        console.print(f"\n[dim]Found {len(working_dates)} working dates[/dim]")

        # Get existing entries
        existing_dates = set()
        if self.config_manager.config.auto_skip_existing:
            print_info("Fetching existing entries from server...")
            try:
                existing_dates = client.fetch_existing_dates()
            except Exception as e:
                print_error(f"Failed to fetch existing entries: {e}")
                return
            console.print(f"[dim]Found {len(existing_dates)} existing entries[/dim]\n")

        # Assign dates to entries
        entries_with_dates = self._assign_dates_to_entries(entries, working_dates, existing_dates)

        # Show summary
        self._show_upload_summary(entries_with_dates, existing_dates, holidays)

        if not questionary.confirm("\nProceed with upload?", default=True).ask():
            print_warning("Upload cancelled")
            return

        # Perform upload
        self._perform_upload(client, entries_with_dates, dry_run)

    def upload_date_range(self) -> None:
        """Upload entries for a specific date range."""
        console.print()
        print_header("📤 Upload Date Range")

        # Get date range
        start_date = questionary.text(
            "Start date (YYYY-MM-DD):",
            validate=lambda x: self._validate_date(x) or "Invalid date format",
        ).ask()

        if not start_date:
            return

        end_date = questionary.text(
            "End date (YYYY-MM-DD):",
            validate=lambda x: self._validate_date(x) or "Invalid date format",
        ).ask()

        if not end_date:
            return

        dry_run = questionary.confirm("Dry run (validate without uploading)?", default=False).ask()

        # Pass date range to upload method
        print_info(f"Uploading entries from {start_date} to {end_date}")
        self.upload_with_auto_dates(dry_run=dry_run, start_date=start_date, end_date=end_date)

    def dry_run_upload(self) -> None:
        """Validate entries without uploading."""
        console.print()
        print_header("🔍 Dry Run - Validate Entries")

        entries_path = self._get_entries_file()
        if not entries_path:
            return

        entries = self._load_entries(entries_path)
        if not entries:
            return

        console.print("\n[bold]Validating entries...[/bold]\n")

        for i, entry in enumerate(entries, 1):
            try:
                self._validate_entry(entry, i)
                console.print(f"[green]✓[/green] Entry {i}: Valid")
            except Exception as e:
                console.print(f"[red]✗[/red] Entry {i}: {e}")

        console.print(f"\n[bold]Validation complete:[/bold] {len(entries)} entries checked")
        questionary.press_any_key_to_continue().ask()

    def upload_from_file(self) -> None:
        """Upload entries from a specific file."""
        console.print()
        print_header("📁 Upload from File")

        file_path = questionary.path(
            "Path to entries file (JSON):",
            only_files=True,
            validate=lambda x: (
                Path(x).exists()
                and Path(x).suffix.lower() == ".json"
                or "File not found or not JSON"
            ),
        ).ask()

        if not file_path:
            return

        entries = self._load_entries(Path(file_path))
        if not entries:
            return

        # Upload with auto-dates using already-loaded entries
        self.upload_with_auto_dates(entries=entries)

    def interactive_upload(self) -> None:
        """Interactive upload with review and approval."""
        console.print()
        print_header("🔄 Interactive Upload")

        entries_path = self._get_entries_file()
        if not entries_path:
            return

        entries = self._load_entries(entries_path)
        if not entries:
            return

        console.print(f"\n[bold]Loaded {len(entries)} entries[/bold]\n")
        client = VTUApiClient(self.config_manager)
        internship_id = client.get_internship_id()

        # Show entries and let user review
        for i, entry in enumerate(entries, 1):
            self._show_entry_details(entry, i)

            action = questionary.select(
                f"Entry {i}/{len(entries)}: What would you like to do?",
                choices=[
                    {"name": "✓ Upload this entry", "value": "upload"},
                    {"name": "✗ Skip this entry", "value": "skip"},
                    {"name": "← Edit this entry", "value": "edit"},
                    {"name": "✗ Stop uploading", "value": "stop"},
                ],
            ).ask()

            if action == "stop":
                print_warning("Upload stopped by user")
                return
            elif action == "skip":
                continue
            elif action == "edit":
                # For simplicity, just skip editing in this version
                print_warning("Edit feature coming soon!")
                continue

            # Upload this entry
            entry["internship_id"] = internship_id

            console.print(f"\n[dim]Uploading entry {i}...[/dim]")
            success, message = client.upload_entry(entry)

            if success:
                print_success(f"Entry {i} uploaded successfully!")
            else:
                print_error(f"Entry {i} upload failed: {message}")
                if not questionary.confirm("Continue with next entry?", default=True).ask():
                    break

    def _get_entries_file(self) -> Path | None:
        """Get entries file path from user."""
        default_path = Path("entries/diary_entries.json")

        use_default = questionary.confirm(
            f"Use default entries file ({default_path})?", default=True
        ).ask()

        if use_default:
            if default_path.exists():
                return default_path
            else:
                print_error(f"Default file not found: {default_path}")
                return None

        file_path = questionary.path(
            "Path to entries file:",
            only_files=True,
            validate=lambda x: Path(x).exists() or "File not found",
        ).ask()

        return Path(file_path) if file_path else None

    def _load_entries(self, path: Path) -> list[dict[str, Any]]:
        """Load entries from JSON file."""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                print_error("Entries file must contain a JSON array")
                return []

            console.print(f"[green]✓[/green] Loaded {len(data)} entries from {path}")
            return data

        except Exception as e:
            print_error(f"Failed to load entries: {e}")
            return []

    def _generate_working_dates(
        self, start_date: str, end_date: str, holidays: dict[str, Any]
    ) -> list[str]:
        """Generate list of working dates (excluding holidays)."""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = (
                datetime.strptime(end_date, "%Y-%m-%d").date()
                if end_date.lower() != "today"
                else date.today()
            )

            if start > end:
                print_error("Start date cannot be after end date")
                return []

            holiday_weekdays = self._get_holiday_weekday_indexes(holidays.get("weekdays", []))
            holiday_dates = set(holidays.get("dates", []))

            working_dates = []
            current = start

            while current <= end:
                date_str = current.isoformat()
                if date_str not in holiday_dates and current.weekday() not in holiday_weekdays:
                    working_dates.append(date_str)
                current += timedelta(days=1)

            return working_dates

        except Exception as e:
            print_error(f"Failed to generate working dates: {e}")
            return []

    def _get_holiday_weekday_indexes(self, weekdays: list[str]) -> set[int]:
        """Convert weekday names to indexes."""
        weekday_map = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        return {weekday_map.get(day.lower()) for day in weekdays if day.lower() in weekday_map}

    def _assign_dates_to_entries(
        self, entries: list[dict[str, Any]], working_dates: list[str], existing_dates: set[str]
    ) -> list[dict[str, Any]]:
        """Assign dates to entries that don't have them."""
        available_dates = [d for d in working_dates if d not in existing_dates]
        assigned = []

        for entry in entries:
            entry_copy = entry.copy()

            if not entry_copy.get("date"):
                if available_dates:
                    entry_copy["date"] = available_dates.pop(0)
                else:
                    print_warning("No more available dates for remaining entries")
                    break

            assigned.append(entry_copy)

        return assigned

    def _show_upload_summary(
        self, entries: list[dict[str, Any]], existing_dates: set[str], holidays: dict[str, Any]
    ) -> None:
        """Show summary before upload."""
        console.print("\n[bold]Upload Summary:[/bold]\n")
        console.print(f"  Total entries: {len(entries)}")

        new_entries = [e for e in entries if e.get("date") not in existing_dates]
        console.print(f"  New entries to upload: {len(new_entries)}")
        console.print(f"  Existing entries to skip: {len(entries) - len(new_entries)}")

        # Show first few entries
        if new_entries:
            console.print("\n[dim]First few entries to upload:[/dim]")
            for entry in new_entries[:3]:
                console.print(f"  • {entry.get('date')}: {entry.get('description', '')[:50]}...")

    def _perform_upload(
        self, client: VTUApiClient, entries: list[dict[str, Any]], dry_run: bool
    ) -> None:
        """Perform the actual upload with progress bar."""
        console.print("\n")

        if dry_run:
            print_info("DRY RUN - No entries will be uploaded")
            for i, entry in enumerate(entries, 1):
                console.print(
                    f"  [dim]{i}.[/dim] {entry.get('date')}: {entry.get('description', '')[:50]}..."
                )
            return

        with create_progress_bar() as progress:
            task = progress.add_task("Uploading entries...", total=len(entries))

            success_count = 0
            failed_entries: list[tuple[str, str]] = []

            for entry in entries:
                entry["internship_id"] = client.get_internship_id()

                success, message = client.upload_entry(entry)

                if success:
                    success_count += 1
                else:
                    failed_entries.append((entry.get("date", "unknown"), message))

                progress.update(task, advance=1)

        console.print("\n[bold]Upload Results:[/bold]\n")
        console.print(f"  [green]✓[/green] Success: {success_count}")
        console.print(f"  [red]✗[/red] Failed: {len(failed_entries)}")

        if failed_entries:
            console.print("\n[yellow]Failed entries:[/yellow]")
            for entry_date, msg in failed_entries[:10]:
                console.print(f"  • {entry_date}: {msg}")
            if len(failed_entries) > 10:
                console.print(f"  ... and {len(failed_entries) - 10} more")

        questionary.press_any_key_to_continue().ask()

    def _show_entry_details(self, entry: dict[str, Any], index: int) -> None:
        """Show detailed view of an entry."""
        panel_content = f"""
[bold]Entry {index}[/bold]

[dim]Date:[/dim] {entry.get("date", "Not assigned")}
[dim]Hours:[/dim] {format_hours(entry.get("hours", 0))}
[dim]Mood:[/dim] {format_mood(entry.get("mood_slider", 3))}

[bold]Description:[/bold]
{entry.get("description", "No description")}

[bold]Learnings:[/bold]
{entry.get("learnings", "No learnings")}

[dim]Links:[/dim] {entry.get("links", "None") or "None"}
[dim]Blockers:[/dim] {entry.get("blockers", "None") or "None"}
[dim]Skills:[/dim] {", ".join(entry.get("skill_ids", []))}
        """
        console.print(Panel.fit(panel_content, border_style="blue"))

    def _validate_entry(self, entry: dict[str, Any], index: int) -> None:
        """Validate a single entry."""
        required_fields = [
            "description",
            "hours",
            "links",
            "blockers",
            "learnings",
            "mood_slider",
            "skill_ids",
        ]

        missing = [field for field in required_fields if field not in entry]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        if entry.get("date"):
            try:
                datetime.strptime(entry["date"], "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date format: {entry['date']}") from None

    def _validate_date(self, date_str: str) -> bool:
        """Validate date format."""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
