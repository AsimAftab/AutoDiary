"""
Main Menu System - Rich console interface for VTU Auto Diary Filler.
"""

import json
import logging
import sys
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from autodiary.cli.config_menu import ConfigMenu
from autodiary.cli.upload_menu import UploadMenu
from autodiary.cli.utils import (
    print_error,
    print_info,
    print_success,
    print_warning,
)
from autodiary.cli.view_menu import ViewMenu
from autodiary.core.config import ConfigManager

console = Console()


class MainMenu:
    """Main menu system for VTU Auto Diary Filler."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize main menu.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.upload_menu = UploadMenu(config_manager)
        self.view_menu = ViewMenu(config_manager)
        self.config_menu = ConfigMenu(config_manager)

    def show(self) -> None:
        """Display and handle main menu."""
        while True:
            try:
                # Clear screen (optional, keeps interface clean)
                # console.clear()

                # Display welcome header
                self._show_welcome_header()

                # Check configuration status
                if not self.config_manager.is_configured:
                    console.print()
                    print_warning(
                        "Configuration incomplete or missing. Please complete setup first."
                    )
                    console.print()

                    # Force setup wizard
                    if self.config_menu.run_setup_wizard():
                        print_success("Setup complete! You can now use all features.")
                    else:
                        print_error(
                            "Setup was cancelled. The application requires configuration to function."
                        )
                        return

                    continue

                # Show menu options
                choice = questionary.select(
                    "What would you like to do?",
                    choices=[
                        {"name": "[Upload] Upload Diaries", "value": "upload"},
                        {"name": "[View] View/Download Entries", "value": "view"},
                        {"name": "[Config] Configuration", "value": "config"},
                        {"name": "[Auth] Login & Authentication", "value": "auth"},
                        {"name": "[Help] Help & Documentation", "value": "help"},
                        {"name": "0. [Exit] Exit Application", "value": "exit"},
                    ],
                    use_indicator=True,
                ).ask()

                if not choice:  # User pressed Ctrl+C
                    break

                # Handle choice
                if choice == "exit":
                    self._handle_exit()
                    break
                elif choice == "upload":
                    self.upload_menu.show()
                elif choice == "view":
                    self.view_menu.show()
                elif choice == "config":
                    self.config_menu.show()
                elif choice == "auth":
                    self._handle_auth_menu()
                elif choice == "help":
                    self._handle_help_menu()

            except KeyboardInterrupt:
                console.print("\n")
                if questionary.confirm("Do you want to exit?", default=True).ask():
                    break
                continue
            except Exception as e:
                console.print_exception()
                print_error(f"An error occurred: {e}")
                if not questionary.confirm("Continue?", default=True).ask():
                    break

    def _show_welcome_header(self) -> None:
        """Display welcome header with ASCII logo."""
        logo = (
            "[bold cyan]"
            "    _    ____  \n"
            "   / \\  |  _ \\ \n"
            "  / _ \\ | | | |\n"
            " / ___ \\| |_| |\n"
            "/_/   \\_\\____/ \n"
            "[/bold cyan]"
        )

        # Get internship info for personalization
        try:
            internship = self.config_manager.get_internship_config()
            company = internship.get("company", "Your Company")
            title = internship.get("title", "Internship")

            header_text = (
                f"{logo}\n"
                f"[bold cyan]VTU Auto Diary Filler[/bold cyan]\n"
                f"[dim]{title} at {company}[/dim]"
            )
        except Exception as e:
            logging.debug("Failed to load internship config for header: %s", e)
            header_text = f"{logo}\n[bold cyan]VTU Auto Diary Filler[/bold cyan]"

        console.print(Panel.fit(header_text, border_style="cyan"))

    def _handle_exit(self) -> None:
        """Handle application exit."""
        console.print()
        print_success("Thank you for using VTU Auto Diary Filler!")
        print_info("Your progress has been saved.")
        console.print()

    def _handle_auth_menu(self) -> None:
        """Handle authentication menu."""
        while True:
            choice = questionary.select(
                "Login & Authentication",
                choices=[
                    {"name": "Test Login", "value": "test"},
                    {"name": "Get Access Token", "value": "token"},
                    {"name": "View Session Info", "value": "session"},
                    {"name": "Logout / Clear Saved Credentials", "value": "logout"},
                    {"name": "← Back to Main Menu", "value": "back"},
                ],
                use_indicator=True,
            ).ask()

            if not choice or choice == "back":
                break

            if choice == "test":
                self._test_login()
            elif choice == "token":
                self._show_access_token()
            elif choice == "session":
                self._show_session_info()
            elif choice == "logout":
                if self._logout_clear_credentials():
                    break

    def _test_login(self) -> None:
        """Test login credentials."""
        from autodiary.core.client import VTUApiClient

        console.print()
        print_info("Testing login credentials...")

        try:
            client = VTUApiClient(self.config_manager)
            if client.test_connection():
                print_success("Login successful! Your credentials are working.")
            else:
                print_error("Login failed. Please check your credentials in Configuration.")
        except Exception as e:
            print_error(f"Login test failed: {e}")

        console.print()
        questionary.press_any_key_to_continue().ask()

    def _show_access_token(self) -> None:
        """Show current access token."""
        from autodiary.core.client import VTUApiClient

        console.print()
        print_info("Fetching access token...")

        try:
            client = VTUApiClient(self.config_manager)
            credentials = self.config_manager.get_credentials()

            if client.login(credentials["email"], credentials["password"]):
                token = client.get_access_token()
                if token:
                    # Mask token for security (show first 8 and last 8 chars)
                    if len(token) > 20:
                        masked_token = f"{token[:8]}...{token[-8:]}"
                    else:
                        masked_token = "*" * len(token)

                    console.print(
                        Panel.fit(
                            f"[bold]Access Token (Masked):[/bold]\n{masked_token}",
                            title="🔑 Session Token",
                            border_style="green",
                        )
                    )

                    # Ask if user wants to see full token
                    show_full = questionary.confirm(
                        "Show full token? (Security risk if screen is visible to others)",
                        default=False,
                    ).ask()

                    if show_full:
                        console.print()
                        console.print(
                            Panel.fit(
                                f"[bold yellow]⚠️  Full Access Token:[/bold yellow]\n{token}",
                                title="🔓 Unmasked Token",
                                border_style="yellow",
                            )
                        )
                else:
                    print_warning("No access token found in session.")
            else:
                print_error("Failed to login. Please check your credentials.")

        except Exception as e:
            print_error(f"Failed to get access token: {e}")

        console.print()
        questionary.press_any_key_to_continue().ask()

    def _logout_clear_credentials(self) -> bool:
        """Clear saved credentials from local configuration."""
        console.print()
        print_warning("This will remove the saved email and encrypted password.")
        print_info("Internship settings, holidays, entries, and downloads will be kept.")

        if not questionary.confirm("Log out and clear saved credentials?", default=False).ask():
            print_warning("Logout cancelled")
            console.print()
            return False

        try:
            self.config_manager.clear_credentials()
            print_success("Saved credentials cleared. Please run setup before uploading again.")
            console.print()
            questionary.press_any_key_to_continue().ask()
            return True
        except Exception as e:
            print_error(f"Failed to clear credentials: {e}")
            console.print()
            questionary.press_any_key_to_continue().ask()
            return False

    def _show_session_info(self) -> None:
        """Show session information."""
        console.print()
        print_info("Session Information")

        try:
            internship = self.config_manager.get_internship_config()
            holidays = self.config_manager.get_holiday_config()

            console.print(f"  [dim]Internship ID:[/dim] {internship.get('id', 'N/A')}")
            console.print(f"  [dim]Company:[/dim] {internship.get('company', 'N/A')}")
            console.print(f"  [dim]Title:[/dim] {internship.get('title', 'N/A')}")
            console.print(f"  [dim]Start Date:[/dim] {internship.get('start_date', 'N/A')}")
            console.print(f"  [dim]End Date:[/dim] {internship.get('end_date', 'N/A')}")
            console.print(
                f"  [dim]Holiday Weekdays:[/dim] {', '.join(holidays.get('weekdays', []))}"
            )
            console.print(
                f"  [dim]Holiday Dates:[/dim] {len(holidays.get('dates', []))} specific dates"
            )

        except Exception as e:
            print_error(f"Failed to load session info: {e}")

        console.print()
        questionary.press_any_key_to_continue().ask()

    def _handle_help_menu(self) -> None:
        """Handle help menu."""
        while True:
            choice = questionary.select(
                "Help & Documentation",
                choices=[
                    {"name": "User Guide", "value": "guide"},
                    {"name": "View Available Skills", "value": "skills"},
                    {"name": "Troubleshooting", "value": "trouble"},
                    {"name": "About", "value": "about"},
                    {"name": "← Back to Main Menu", "value": "back"},
                ],
                use_indicator=True,
            ).ask()

            if not choice or choice == "back":
                break

            if choice == "guide":
                self._show_user_guide()
            elif choice == "skills":
                self._show_available_skills()
            elif choice == "trouble":
                self._show_troubleshooting()
            elif choice == "about":
                self._show_about()

    def _show_user_guide(self) -> None:
        """Show user guide."""
        guide_text = """
[bold cyan]VTU Auto Diary Filler - User Guide[/bold cyan]

[bold]Getting Started:[/bold]
1. First time users will be guided through setup
2. Enter your VTU credentials and internship details
3. Configure your holidays and weekends

[bold]Uploading Diaries:[/bold]
1. Prepare your diary entries in JSON format
2. Select 'Upload Diaries' from main menu
3. Choose your upload options
4. Review and confirm upload

[bold]Skill IDs:[/bold]
• Use 'View Available Skills' in Help menu to see all skill IDs
• Add skill IDs to your entries: "skill_ids": ["3", "44"]
• Common skills: 3 (Python), 1 (JavaScript), 44 (Data modeling)

[bold]Viewing Entries:[/bold]
1. Select 'View/Download Entries'
2. Choose to view existing entries or download them
3. Entries can be exported to JSON format

[bold]Configuration:[/bold]
- Access Configuration menu to change settings
- Test your connection anytime
- Reset to defaults if needed

[bold]Tips:[/bold]
- Use 'Dry Run' to test without uploading
- Enable 'Auto Skip Existing' to avoid duplicates
- Configure holidays to skip weekends automatically
- Check 'View Available Skills' for skill ID reference
        """
        console.print()
        console.print(Panel.fit(guide_text, title="[USER GUIDE]", border_style="blue"))
        console.print()
        questionary.press_any_key_to_continue().ask()

    def _show_troubleshooting(self) -> None:
        """Show troubleshooting guide."""
        trouble_text = """
[bold red]Common Issues and Solutions[/bold red]

[bold]Login Issues:[/bold]
• Verify email and password are correct
• Check VTU portal is accessible
• Try 'Test Login' in Authentication menu

[bold]Upload Fails:[/bold]
• Check internet connection
• Verify entries have valid dates
• Try 'Dry Run' first to validate
• Check if date is a holiday

[bold]Configuration Issues:[/bold]
• Use 'Reset to Defaults' in Configuration
• Run setup wizard again
• Check all required fields are filled

[bold]Performance Issues:[/bold]
• Reduce request delay in advanced settings
• Check your internet speed
• Close other applications

[bold]Still Need Help?[/bold]
• Check our documentation
• Visit our GitHub repository
• Contact support
        """
        console.print()
        console.print(Panel.fit(trouble_text, title="[TROUBLESHOOTING]", border_style="yellow"))
        console.print()
        questionary.press_any_key_to_continue().ask()

    def _show_about(self) -> None:
        """Show about information."""
        about_text = """
[bold cyan]VTU Auto Diary Filler[/bold cyan]

Version: 1.0.0

A user-friendly console application for automatically
uploading internship diary entries to the VTU portal.

[bold]Features:[/bold]
• Rich console interface with colors
• Automatic date assignment
• Holiday and weekend detection
• Batch upload with retry logic
• View and download existing entries
• Encrypted credential storage

[bold]Made with:[/bold]
• Python
• Rich (console UI)
• Typer (CLI framework)
• Requests (HTTP client)

[dim]© 2026 VTU Auto Diary Team[/dim]
        """
        console.print()
        console.print(Panel.fit(about_text, title="[ABOUT]", border_style="cyan"))
        console.print()
        questionary.press_any_key_to_continue().ask()

    def _show_available_skills(self) -> None:
        """Show available skills from VTU portal."""
        console.print()
        print_info("Loading available skills...")

        # Determine base path for bundled files
        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent.parent

        skills_file = base_path / "autodiary" / "resources" / "skills_mapping.json"

        # Fallback to path relative to this module's package
        if not skills_file.exists():
            skills_file = Path(__file__).parent.parent / "resources" / "skills_mapping.json"

        if not skills_file.exists():
            print_error("Skills mapping file not found. Using built-in common skills.")
            # Fallback to common skills
            skills = [
                {"id": "1", "name": "JavaScript"},
                {"id": "3", "name": "Python"},
                {"id": "10", "name": "Java"},
                {"id": "15", "name": "Machine learning"},
                {"id": "16", "name": "Data visualization"},
                {"id": "17", "name": "Statistical analysis"},
                {"id": "19", "name": "Database design"},
                {"id": "20", "name": "SQL"},
                {"id": "24", "name": "DevOps"},
                {"id": "42", "name": "MySQL"},
                {"id": "44", "name": "Data modeling"},
                {"id": "63", "name": "Git"},
            ]
        else:
            try:
                with open(skills_file, encoding="utf-8") as f:
                    data = json.load(f)
                    skills = data.get("skills", [])
            except Exception as e:
                print_error(f"Failed to load skills: {e}")
                questionary.press_any_key_to_continue().ask()
                return

        if not skills:
            print_error("No skills found.")
            questionary.press_any_key_to_continue().ask()
            return

        # Optional search filter
        search = (
            (
                questionary.text(
                    "Search skills (leave empty to show all):",
                ).ask()
                or ""
            )
            .strip()
            .lower()
        )

        display_skills = skills
        if search:
            display_skills = [
                s
                for s in skills
                if search in s.get("name", "").lower() or search in str(s.get("id", ""))
            ]
            if not display_skills:
                print_warning(f"No skills matching '{search}'")
                questionary.press_any_key_to_continue().ask()
                return

        # Create a table to display skills
        title = (
            f"[SKILLS MATCHING '{search.upper()}']"
            if search
            else "[AVAILABLE SKILLS FOR DIARY ENTRIES]"
        )
        table = Table(
            title=title,
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("ID", style="cyan", width=6)
        table.add_column("Skill Name", style="white")

        for skill in display_skills:
            skill_id = str(skill.get("id", ""))
            skill_name = skill.get("name", "Unknown")
            table.add_row(skill_id, skill_name)

        console.print()
        console.print(table)
        console.print(f"\n[dim]Showing {len(display_skills)} of {len(skills)} skills[/dim]")
        console.print()

        # Show usage information
        usage_text = """
[bold cyan]How to Use Skill IDs:[/bold cyan]

1. [bold]Note the Skill ID[/bold] - Find the skill that matches your work and note its ID number
2. [bold]Update Your Entries[/bold] - Add the skill ID to your diary_entries.json file:
   [dim]"skill_ids": ["1", "15", "44"][/dim]
3. [bold]Multiple Skills[/bold] - You can add multiple skill IDs as a list
4. [bold]Common Skills[/bold] - Popular IDs: 1 (JavaScript), 3 (Python), 44 (Data modeling), 16 (Data visualization)

[bold]Example Entry:[/bold]
{
  "date": "2026-01-05",
  "description": "Learned Python data analysis",
  "hours": 8,
  "links": "",
  "blockers": "",
  "learnings": "Mastered pandas and numpy",
  "mood_slider": 4,
  "skill_ids": ["3", "44", "16"]
}
        """

        console.print(Panel.fit(usage_text, title="[SKILL IDs GUIDE]", border_style="green"))
        console.print()
        questionary.press_any_key_to_continue().ask()
