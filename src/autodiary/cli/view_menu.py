"""
View Menu - Handle viewing and downloading of existing diary entries.
"""

import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import questionary
from rich.console import Console
from rich.table import Table

from autodiary.cli.utils import (
    format_entry_date,
    format_hours,
    format_mood,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
)
from autodiary.core.client import VTUApiClient
from autodiary.utils.validators import validate_date_format

console = Console()


class ViewMenu:
    """View menu for diary entries."""

    def __init__(self, config_manager):
        """Initialize view menu."""
        self.config_manager = config_manager

    def show(self) -> None:
        """Display view menu."""
        while True:
            choice = questionary.select(
                "View/Download Entries",
                choices=[
                    {"name": "View All Existing Entries", "value": "all"},
                    {"name": "View by Date Range", "value": "range"},
                    {"name": "View Entry Statistics", "value": "stats"},
                    {"name": "Download All Entries (JSON)", "value": "download"},
                    {"name": "Export to CSV", "value": "csv"},
                    {"name": "← Back to Main Menu", "value": "back"},
                ],
                use_indicator=True,
            ).ask()

            if not choice or choice == "back":
                break

            if choice == "all":
                self.view_all_entries()
            elif choice == "range":
                self.view_date_range()
            elif choice == "stats":
                self.view_statistics()
            elif choice == "download":
                self.download_entries()
            elif choice == "csv":
                self.export_to_csv()

    def view_all_entries(self) -> None:
        """View all existing entries from server."""
        console.print()
        print_header("📥 View All Entries")

        print_info("Fetching entries from server...")
        client = VTUApiClient(self.config_manager)

        try:
            entries = client.fetch_all_entries()

            if not entries:
                print_warning("No entries found on server")
                questionary.press_any_key_to_continue().ask()
                return

            console.print(f"\n[green]✓[/green] Found {len(entries)} entries\n")

            # Show entries in pages
            self._display_entries_paginated(entries)

        except Exception as e:
            print_error(f"Failed to fetch entries: {e}")

        questionary.press_any_key_to_continue().ask()

    def view_date_range(self) -> None:
        """View entries within a specific date range."""
        console.print()
        print_header("📅 View by Date Range")

        start_date = questionary.text(
            "Start date (YYYY-MM-DD):",
            validate=lambda x: validate_date_format(x) or "Invalid date format",
        ).ask()

        if not start_date:
            return

        end_date = questionary.text(
            "End date (YYYY-MM-DD):",
            validate=lambda x: validate_date_format(x) or "Invalid date format",
        ).ask()

        if not end_date:
            return

        # Validate date range
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
            if start > end:
                print_warning("Start date must be on or before end date")
                questionary.press_any_key_to_continue().ask()
                return
        except ValueError:
            print_error("Invalid date format")
            questionary.press_any_key_to_continue().ask()
            return

        print_info(f"Fetching entries from {start_date} to {end_date}...")
        client = VTUApiClient(self.config_manager)

        try:
            all_entries = client.fetch_all_entries()

            # Filter by date range
            filtered = [e for e in all_entries if start_date <= e.get("date", "") <= end_date]

            if not filtered:
                print_warning(f"No entries found between {start_date} and {end_date}")
                questionary.press_any_key_to_continue().ask()
                return

            console.print(f"\n[green]✓[/green] Found {len(filtered)} entries in range\n")

            self._display_entries_paginated(filtered)

        except Exception as e:
            print_error(f"Failed to fetch entries: {e}")

        questionary.press_any_key_to_continue().ask()

    def view_statistics(self) -> None:
        """View entry statistics."""
        console.print()
        print_header("📊 Entry Statistics")

        print_info("Fetching entries from server...")
        client = VTUApiClient(self.config_manager)

        try:
            entries = client.fetch_all_entries()

            if not entries:
                print_warning("No entries found")
                questionary.press_any_key_to_continue().ask()
                return

            # Calculate statistics
            stats = self._calculate_statistics(entries)

            # Display statistics
            console.print("\n[bold]Internship Progress:[/bold]\n")
            console.print(f"  Total Entries: [cyan]{stats['total_entries']}[/cyan]")
            console.print(f"  Total Hours: [cyan]{stats['total_hours']}h[/cyan]")
            console.print(f"  Average Hours: [cyan]{stats['avg_hours']:.1f}h[/cyan]")
            console.print(f"  Average Mood: [cyan]{stats['avg_mood']:.1f}/5[/cyan]")

            console.print("\n[bold]Date Range:[/bold]\n")
            console.print(f"  Start: {stats['earliest_date'] or 'N/A'}")
            console.print(f"  End: {stats['latest_date'] or 'N/A'}")
            console.print(f"  Span: {stats['day_span']} days")

            console.print("\n[bold]Mood Distribution:[/bold]\n")
            for mood, count in stats["mood_distribution"].items():
                bar = "█" * count
                console.print(f"  {mood}: {bar} ({count})")

            console.print("\n[bold]Skills Used:[/bold]\n")
            top_skills = sorted(stats["skill_counts"].items(), key=lambda x: x[1], reverse=True)[:5]
            for skill, count in top_skills:
                console.print(f"  • {skill}: {count} times")

        except Exception as e:
            print_error(f"Failed to calculate statistics: {e}")

        console.print()
        questionary.press_any_key_to_continue().ask()

    def download_entries(self) -> None:
        """Download all entries to JSON file."""
        console.print()
        print_header("💾 Download Entries (JSON)")

        default_path = Path("previous_entries/all_entries.json")

        save_path = questionary.text(
            f"Save path (default: {default_path}):", default=str(default_path)
        ).ask() or str(default_path)

        print_info("Fetching entries from server...")
        client = VTUApiClient(self.config_manager)

        try:
            entries = client.fetch_all_entries()

            if not entries:
                print_warning("No entries to download")
                questionary.press_any_key_to_continue().ask()
                return

            # Save to file
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)

            print_success(f"Downloaded {len(entries)} entries to {save_path}")

        except Exception as e:
            print_error(f"Failed to download entries: {e}")

        questionary.press_any_key_to_continue().ask()

    def export_to_csv(self) -> None:
        """Export entries to CSV format."""
        console.print()
        print_header("📄 Export to CSV")

        default_path = Path("previous_entries/entries.csv")

        save_path = questionary.text(
            f"Save path (default: {default_path}):", default=str(default_path)
        ).ask() or str(default_path)

        print_info("Fetching entries from server...")
        client = VTUApiClient(self.config_manager)

        try:
            entries = client.fetch_all_entries()

            if not entries:
                print_warning("No entries to export")
                questionary.press_any_key_to_continue().ask()
                return

            # Convert to CSV
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, "w", newline="", encoding="utf-8") as f:
                # Use logical field ordering; append any extra keys alphabetically
                preferred_order = [
                    "date",
                    "description",
                    "hours",
                    "learnings",
                    "mood_slider",
                    "skill_ids",
                    "links",
                    "blockers",
                    "internship_id",
                ]
                all_keys = {k for entry in entries for k in entry}
                fieldnames = [k for k in preferred_order if k in all_keys]
                fieldnames += sorted(all_keys - set(fieldnames))
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(entries)

            print_success(f"Exported {len(entries)} entries to {save_path}")

        except Exception as e:
            print_error(f"Failed to export entries: {e}")

        questionary.press_any_key_to_continue().ask()

    def _display_entries_paginated(
        self, entries: list[dict[str, Any]], page_size: int = 10
    ) -> None:
        """Display entries in pages."""
        total_pages = (len(entries) + page_size - 1) // page_size
        current_page = 0

        while 0 <= current_page < total_pages:
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(entries))
            page_entries = entries[start_idx:end_idx]

            # Create table
            table = Table(title=f"Entries (Page {current_page + 1}/{total_pages})")
            table.add_column("Date", style="cyan")
            table.add_column("Hours", justify="right")
            table.add_column("Mood", justify="center")
            table.add_column("Description")

            for entry in page_entries:
                table.add_row(
                    str(format_entry_date(entry.get("date", "N/A"))),
                    str(format_hours(entry.get("hours", 0))),
                    str(format_mood(entry.get("mood_slider", 3))),
                    entry.get("description", "")[:50] + "..."
                    if len(entry.get("description", "")) > 50
                    else entry.get("description", ""),
                )

            console.print(table)
            console.print()

            if current_page >= total_pages - 1:
                # Last page — only allow going back or exiting
                if current_page > 0:
                    action = questionary.select(
                        "Navigation:",
                        choices=[
                            {"name": "← Previous Page", "value": "prev"},
                            {"name": "Exit Viewing", "value": "exit"},
                        ],
                    ).ask()
                    if action == "prev":
                        current_page -= 1
                        continue
                else:
                    questionary.press_any_key_to_continue().ask()
                break
            else:
                # Middle or first page — build dynamic choices
                choices = []
                if current_page > 0:
                    choices.append({"name": "← Previous Page", "value": "prev"})
                choices.append({"name": "Next Page →", "value": "next"})
                choices.append({"name": "Exit Viewing", "value": "exit"})

                action = questionary.select("Navigation:", choices=choices).ask()

                if action == "exit":
                    break
                elif action == "prev":
                    current_page -= 1
                else:
                    current_page += 1

    def _calculate_statistics(self, entries: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate statistics from entries."""
        total_entries = len(entries)
        total_hours = sum(e.get("hours", 0) for e in entries)
        avg_hours = total_hours / total_entries if total_entries > 0 else 0
        avg_mood = (
            sum(e.get("mood_slider", 0) for e in entries) / total_entries
            if total_entries > 0
            else 0
        )

        # Date range
        dates = [e.get("date") for e in entries if e.get("date")]
        earliest_date = min(dates) if dates else None
        latest_date = max(dates) if dates else None

        # Calculate day span
        day_span = 0
        if earliest_date and latest_date:
            try:
                start = datetime.strptime(earliest_date, "%Y-%m-%d")
                end = datetime.strptime(latest_date, "%Y-%m-%d")
                day_span = (end - start).days + 1
            except ValueError:
                pass

        # Mood distribution
        mood_dist = {}
        for entry in entries:
            mood = entry.get("mood_slider", 3)
            mood_label = f"{mood}/5"
            mood_dist[mood_label] = mood_dist.get(mood_label, 0) + 1

        # Skill counts
        skill_counts = {}
        for entry in entries:
            skills = entry.get("skill_ids", [])
            for skill in skills:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1

        return {
            "total_entries": total_entries,
            "total_hours": total_hours,
            "avg_hours": avg_hours,
            "avg_mood": avg_mood,
            "earliest_date": earliest_date,
            "latest_date": latest_date,
            "day_span": day_span,
            "mood_distribution": mood_dist,
            "skill_counts": skill_counts,
        }
