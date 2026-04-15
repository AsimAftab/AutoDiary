"""
Configuration Menu - Handle application configuration and setup wizard.
"""

import json
import logging
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import questionary
from rich.console import Console

from autodiary.cli.utils import print_error, print_header, print_info, print_success, print_warning
from autodiary.core.client import VTUApiClient
from autodiary.core.config import ConfigManager
from autodiary.models.config import AppConfig
from autodiary.utils.validators import (
    get_valid_weekdays,
    validate_date_format,
    validate_email,
    validate_internship_id,
)

console = Console()
LOGGER = logging.getLogger("autodiary")


def _normalize_api_date(date_value: str | None) -> str:
    """Convert VTU API date/datetime values to YYYY-MM-DD for local config."""
    if not date_value:
        return ""

    date_value = date_value.strip()
    try:
        return datetime.strptime(date_value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        pass

    try:
        return datetime.fromisoformat(date_value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        LOGGER.debug("Could not normalize API date value: %s", date_value)
        return ""


class ConfigMenu:
    """Configuration menu and setup wizard."""

    def __init__(self, config_manager):
        """Initialize configuration menu."""
        self.config_manager = config_manager

    def show(self) -> None:
        """Display configuration menu."""
        while True:
            choice = questionary.select(
                "Configuration Management",
                choices=[
                    {"name": "First-Time Setup Wizard", "value": "wizard"},
                    {"name": "Edit Credentials", "value": "credentials"},
                    {"name": "Edit Internship Settings", "value": "internship"},
                    {"name": "Edit Holiday Settings", "value": "holidays"},
                    {"name": "Advanced Settings", "value": "advanced"},
                    {"name": "Test Connection", "value": "test"},
                    {"name": "View Current Configuration", "value": "view"},
                    {"name": "Backup Configuration", "value": "backup"},
                    {"name": "Restore from Backup", "value": "restore"},
                    {"name": "Reset to Defaults", "value": "reset"},
                    {"name": "← Back to Main Menu", "value": "back"},
                ],
                use_indicator=True,
            ).ask()

            if not choice or choice == "back":
                break

            if choice == "wizard":
                self.run_setup_wizard()
            elif choice == "credentials":
                self.edit_credentials()
            elif choice == "internship":
                self.edit_internship_settings()
            elif choice == "holidays":
                self.edit_holiday_settings()
            elif choice == "advanced":
                self.edit_advanced_settings()
            elif choice == "test":
                self.test_connection()
            elif choice == "view":
                self.view_configuration()
            elif choice == "backup":
                self.backup_config()
            elif choice == "restore":
                self.restore_config()
            elif choice == "reset":
                self.reset_to_defaults()

    def run_setup_wizard(self) -> bool:
        """
        Run first-time setup wizard.

        Returns:
            True if setup completed successfully, False otherwise
        """
        console.print()
        print_header("🎉 Welcome to VTU Auto Diary Filler!", "Let's set up your configuration")

        console.print("\n[bold]This wizard will guide you through:[/bold]")
        console.print("  • Setting up your VTU credentials")
        console.print("  • Configuring your internship details")
        console.print("  • Setting up holidays and weekends")
        console.print()

        if not questionary.confirm("Ready to begin?", default=True).ask():
            return False

        if not self._accept_terms_and_conditions():
            return False

        # Step 1: Credentials (with retry loop)
        max_credential_attempts = 3
        email = None
        password = None
        client = None
        internships = None
        temp_config_path = Path(tempfile.gettempdir()) / "temp_vtu_config.json"

        for credential_attempt in range(1, max_credential_attempts + 1):
            console.print("\n[bold cyan]Step 1 of 5: VTU Credentials[/bold cyan]")
            if credential_attempt > 1:
                console.print(
                    f"[yellow]Attempt {credential_attempt}/{max_credential_attempts}[/yellow]\n"
                )
            console.print("[dim]Your credentials will be encrypted and stored locally.[/dim]\n")

            email = (
                questionary.text(
                    "Your VTU email address:",
                    validate=lambda x: validate_email(x.strip()) or "Invalid email format",
                ).ask()
                or ""
            ).strip()

            if not email:
                print_warning("Setup cancelled by user")
                return False

            password = questionary.password(
                "Your VTU password:", validate=lambda x: len(x) > 0 or "Password cannot be empty"
            ).ask()

            if not password:
                print_warning("Setup cancelled by user")
                return False

            # Step 2: Fetch Available Internships
            console.print("\n[bold cyan]Step 2 of 5: Select Your Internship[/bold cyan]")
            console.print("[dim]Fetching your available internships from VTU portal...[/dim]\n")

            try:
                # Create a temporary config manager to test login and fetch internships
                # Create temp config with the user's credentials
                # Use a temporary valid internship_id (we'll get the real one from the API)
                temp_config_manager = ConfigManager(temp_config_path)
                temp_config = AppConfig(
                    email=email,
                    password_encrypted="",
                    internship_id=999999,  # Temporary ID for connection testing only
                    internship_start_date=str(date.today()),
                    internship_end_date="today",
                )
                temp_config_manager.save(temp_config)
                temp_config_manager.set_password(password)

                # Create client and fetch internships
                client = VTUApiClient(temp_config_manager)

                with console.status("[bold cyan]Connecting to VTU portal...[/bold cyan]"):
                    login_ok = client.login(email, password)

                if not login_ok:
                    print_error(
                        "Failed to login to VTU portal. Please check your email and password."
                    )
                    if credential_attempt < max_credential_attempts:
                        print_info(
                            f"You have {max_credential_attempts - credential_attempt} attempt(s) remaining."
                        )
                        console.print()
                        if not questionary.confirm(
                            "Try again with different credentials?", default=True
                        ).ask():
                            print_warning("Setup cancelled by user")
                            return False
                        continue
                    else:
                        print_error(f"Login failed after {max_credential_attempts} attempts.")
                        return False

                print_success("Login successful!")

                # Fetch available internships
                with console.status("[bold cyan]Fetching your internships...[/bold cyan]"):
                    internships = self._fetch_user_internships(client)

                # Successfully logged in and fetched data, break the retry loop
                break

            except Exception as e:
                print_error(f"An error occurred: {e}")
                if credential_attempt < max_credential_attempts:
                    print_info(
                        f"You have {max_credential_attempts - credential_attempt} attempt(s) remaining."
                    )
                    if not questionary.confirm("Try again?", default=True).ask():
                        print_warning("Setup cancelled by user")
                        return False
                    continue
                else:
                    print_error(f"Setup failed after {max_credential_attempts} attempts.")
                    return False
            finally:
                # Clean up temp config
                if temp_config_path.exists():
                    try:
                        temp_config_path.unlink()
                    except Exception:
                        pass

        # If we got here without client/internships, something went wrong
        if not client or internships is None:
            print_error("Failed to complete credential verification")
            return False

        # Handle internship selection
        if not internships:
            print_warning("No internships found. You'll need to enter details manually.")

            # Manual entry fallback
            internship_id = questionary.text(
                "Internship ID:", validate=lambda x: validate_internship_id(x) or "Invalid ID"
            ).ask()

            if not internship_id:
                print_warning("Setup cancelled by user")
                return False

            title = (questionary.text("Internship title (optional):").ask() or "").strip()
            company = (questionary.text("Company name (optional):").ask() or "").strip()

            start_date = questionary.text(
                "Internship start date (YYYY-MM-DD):",
                default=str(date.today()),
                validate=lambda x: validate_date_format(x) or "Invalid date format",
            ).ask()

            end_date = questionary.text(
                "Internship end date (YYYY-MM-DD or 'today'):",
                default="today",
                validate=lambda x: (
                    x.lower() == "today" or validate_date_format(x) or "Invalid date format"
                ),
            ).ask()

        else:
            console.print("\n[bold]Your Available Internships:[/bold]\n")

            # Display internships with selection
            internship_choices = []
            for idx, intern in enumerate(internships, 1):
                status = "🟢 Active" if intern.get("is_active") else "⚪ Inactive"
                title = intern.get("title", "Unknown Internship")
                company = intern.get("company", "Unknown Company")
                internship_choices.append(
                    {"name": f"{idx}. {title} at {company} ({status})", "value": idx - 1}
                )

            internship_choices.append({"name": "0. Enter details manually", "value": "manual"})

            selected = questionary.select(
                "Select your ongoing internship:", choices=internship_choices
            ).ask()

            if selected == "manual" or selected is None:
                # Manual entry
                internship_id = questionary.text(
                    "Internship ID:",
                    validate=lambda x: validate_internship_id(x) or "Invalid ID",
                ).ask()

                if not internship_id:
                    print_warning("Setup cancelled by user")
                    return False

                title = (questionary.text("Internship title (optional):").ask() or "").strip()
                company = (questionary.text("Company name (optional):").ask() or "").strip()

                start_date = questionary.text(
                    "Internship start date (YYYY-MM-DD):",
                    default=str(date.today()),
                    validate=lambda x: validate_date_format(x) or "Invalid date format",
                ).ask()

                end_date = questionary.text(
                    "Internship end date (YYYY-MM-DD or 'today'):",
                    default="today",
                    validate=lambda x: (
                        x.lower() == "today" or validate_date_format(x) or "Invalid date format"
                    ),
                ).ask()

            else:
                # Auto-fill from selected internship
                selected_internship = internships[selected]
                internship_id = selected_internship.get("id")
                title = selected_internship.get("title", "")
                company = selected_internship.get("company", "")

                console.print(f"\n[green]✓[/green] Selected: {title}")
                console.print(f"[dim]Internship ID: {internship_id}[/dim]")

                # Auto-detect dates if available
                if selected_internship.get("start_date"):
                    start_date = selected_internship["start_date"]
                    console.print(f"[dim]Start date detected: {start_date}[/dim]")
                else:
                    start_date = questionary.text(
                        "Internship start date (YYYY-MM-DD):",
                        default=str(date.today()),
                        validate=lambda x: validate_date_format(x) or "Invalid date format",
                    ).ask()

                if selected_internship.get("end_date"):
                    end_date = selected_internship["end_date"]
                    console.print(f"[dim]End date detected: {end_date}[/dim]")
                else:
                    end_date = questionary.text(
                        "Internship end date (YYYY-MM-DD or 'today'):",
                        default="today",
                        validate=lambda x: (
                            x.lower() == "today" or validate_date_format(x) or "Invalid date format"
                        ),
                    ).ask()

        # Now continue with Step 3 (holidays) regardless of how we got the internship data

        # Step 3: Holiday Configuration
        console.print("\n[bold cyan]Step 3 of 5: Holiday Configuration[/bold cyan]")
        console.print("[dim]Select days to EXCLUDE from diary uploads (e.g., weekends).[/dim]\n")

        holiday_weekdays = questionary.checkbox(
            "Select days to exclude from uploads:",
            choices=get_valid_weekdays(),
            validate=lambda x: len(x) > 0 or "Select at least one day to exclude",
        ).ask()

        if not holiday_weekdays:
            print_warning("Setup cancelled by user")
            return False

        # Convert to lowercase
        holiday_weekdays = [day.lower() for day in holiday_weekdays]

        holiday_dates_str = (
            questionary.text(
                "Specific holiday dates (comma-separated, YYYY-MM-DD format, optional):",
            ).ask()
            or ""
        )

        holiday_dates = []
        if holiday_dates_str.strip():
            holiday_dates = [d.strip() for d in holiday_dates_str.split(",") if d.strip()]
            # Validate dates
            for d in holiday_dates:
                if not validate_date_format(d):
                    print_error(f"Invalid date format: {d}")
                    return False

        # Step 4: Confirm and Save
        console.print("\n[bold cyan]Step 4 of 5: Confirm & Save[/bold cyan]\n")

        console.print("[bold]Configuration Summary:[/bold]\n")
        console.print(f"  [dim]Email:[/dim] {email}")
        console.print(f"  [dim]Internship ID:[/dim] {internship_id}")
        console.print(f"  [dim]Start Date:[/dim] {start_date}")
        console.print(f"  [dim]End Date:[/dim] {end_date}")
        console.print(f"  [dim]Title:[/dim] {title or 'Not specified'}")
        console.print(f"  [dim]Company:[/dim] {company or 'Not specified'}")
        console.print(f"  [dim]Holiday Weekdays:[/dim] {', '.join(holiday_weekdays)}")
        console.print(f"  [dim]Holiday Dates:[/dim] {len(holiday_dates)} specific dates")

        console.print()

        if not questionary.confirm("Save this configuration?", default=True).ask():
            print_warning("Setup cancelled by user")
            return False

        # Save configuration
        try:
            config = AppConfig(
                email=email,
                password_encrypted="",  # Will be set by set_password
                internship_id=int(internship_id),
                internship_start_date=start_date,
                internship_end_date=end_date,
                internship_title=title,
                company_name=company,
                holiday_weekdays=holiday_weekdays,
                holiday_dates=holiday_dates,
            )

            # Save config first (sets self._config internally), then encrypt password and persist
            self.config_manager.save(config)
            self.config_manager.set_password(password)
            self.config_manager.save(self.config_manager.config)

            print_success("Configuration saved successfully!")
            console.print()

            # Step 5: Workspace Setup
            console.print("\n[bold cyan]Step 5 of 5: Workspace Setup[/bold cyan]")
            console.print(
                "[dim]Creating workspace folders (entries, previous_entries, skills)...[/dim]\n"
            )

            create_samples = questionary.confirm(
                "Create sample diary entries to try out the upload feature?", default=True
            ).ask()

            self._scaffold_workspace(create_samples)

            if create_samples:
                print_success("Workspace generated with sample entries!")
                console.print()
                print_info("[bold]💡 About Skill IDs:[/bold]")
                print_info(
                    "Sample entries include common skill IDs (Python: 3, Data modeling: 44, etc.)"
                )
                print_warning(
                    "Use 'Help > View Available Skills' to see all 100+ available skills!"
                )
                console.print()
                if questionary.confirm("Would you like to try uploading now?", default=False).ask():
                    print_info("Returning to main menu. Select 'Upload Diaries' to get started.")
                    return True
                else:
                    print_info("You can upload diaries later from the main menu.")
                    return True
            else:
                print_info("Workspace folders created successfully.")
                print_info("No entries created. You can create your own entries file later.")
                print_info("See QUICKSTART.txt for the entry format.")
                print_warning(
                    "💡 Use the copied skills/skills_mapping.json to find skill IDs for your entries!"
                )
                console.print()
                return True

        except Exception as e:
            print_error(f"Failed to save configuration: {e}")
            return False

    def edit_credentials(self) -> None:
        """Edit user credentials."""
        console.print()
        print_header("🔐 Edit Credentials")

        try:
            current_config = self.config_manager.load()
            console.print(f"\n[dim]Current email:[/dim] {current_config.email}")
        except Exception:
            console.print("\n[dim]No credentials configured yet.[/dim]")

        console.print()

        email = (
            questionary.text(
                "New email address (leave empty to keep current):",
                validate=lambda x: (
                    not x.strip() or validate_email(x.strip()) or "Invalid email format"
                ),
            ).ask()
            or ""
        ).strip()

        password = questionary.password("New password (leave empty to keep current):").ask()

        if not email and not password:
            print_warning("No changes made")
            return

        try:
            config = self.config_manager.config

            if email:
                config.email = email

            if password:
                self.config_manager.set_password(password)

            self.config_manager.save(config)
            print_success("Credentials updated successfully!")

            # Test login
            if questionary.confirm("Test login with new credentials?", default=True).ask():
                self.test_connection()

        except Exception as e:
            print_error(f"Failed to update credentials: {e}")

    def edit_internship_settings(self) -> None:
        """Edit internship settings."""
        console.print()
        print_header("💼 Edit Internship Settings")

        try:
            config = self.config_manager.load()
            console.print("\n[dim]Current settings:[/dim]")
            console.print(f"  ID: {config.internship_id}")
            console.print(f"  Start Date: {config.internship_start_date}")
            console.print(f"  End Date: {config.internship_end_date}")
            console.print(f"  Title: {config.internship_title or 'Not set'}")
            console.print(f"  Company: {config.company_name or 'Not set'}")
        except Exception as e:
            print_error(f"Failed to load configuration: {e}")
            return

        console.print()

        internship_id = questionary.text(
            "Internship ID (leave empty to keep current):",
            validate=lambda x: not x or validate_internship_id(x) or "Invalid ID",
        ).ask()

        start_date = questionary.text(
            "Start date (YYYY-MM-DD, leave empty to keep current):",
            validate=lambda x: not x or validate_date_format(x) or "Invalid date format",
        ).ask()

        end_date = questionary.text(
            "End date (YYYY-MM-DD or 'today', leave empty to keep current):",
            validate=lambda x: (
                not x or x.lower() == "today" or validate_date_format(x) or "Invalid format"
            ),
        ).ask()

        title = (
            questionary.text("Internship title (leave empty to keep current):").ask() or ""
        ).strip()
        company = (
            questionary.text("Company name (leave empty to keep current):").ask() or ""
        ).strip()

        if not any([internship_id, start_date, end_date, title, company]):
            print_warning("No changes made")
            return

        try:
            if internship_id:
                config.internship_id = int(internship_id)
            if start_date:
                config.internship_start_date = start_date
            if end_date:
                config.internship_end_date = end_date
            if title:
                config.internship_title = title
            if company:
                config.company_name = company

            self.config_manager.save(config)
            print_success("Internship settings updated!")

        except Exception as e:
            print_error(f"Failed to update settings: {e}")

    def _fetch_user_internships(self, client: VTUApiClient) -> list:
        """
        Fetch available internships for the user.

        Args:
            client: Authenticated VTU API client

        Returns:
            List of internship dictionaries
        """
        try:
            data = client.fetch_internships()

            if data.get("success") and data.get("data"):
                # Extract internships from the response
                response_data = data["data"]

                # Handle the specific VTU API response structure
                if isinstance(response_data, dict) and "data" in response_data:
                    # VTU API has nested data structure
                    internships_raw = response_data["data"]
                    return self._normalize_vtu_internships(internships_raw)
                elif isinstance(response_data, list):
                    return self._normalize_vtu_internships(response_data)

            # If we get here, something went wrong
            LOGGER.debug("Internships API response did not match the expected structure")
            return []

        except Exception as e:
            LOGGER.debug("Could not fetch internships", exc_info=e)
            return []

    def _normalize_vtu_internships(self, raw_internships: list) -> list:
        """
        Normalize VTU internship data from the API response.

        Args:
            raw_internships: Raw internship data from VTU API

        Returns:
            Normalized list of internship dictionaries
        """
        normalized = []

        for intern in raw_internships:
            if not isinstance(intern, dict):
                continue

            # Extract VTU-specific internship data
            internship_id = intern.get("internship_id")
            internship_details = intern.get("internship_details", {})

            if not internship_id:
                continue

            # Normalize the internship data
            normalized_intern = {
                "id": internship_id,
                "title": internship_details.get("name", "Unknown Internship"),
                "company": internship_details.get("company", "Unknown Company"),
                "start_date": _normalize_api_date(intern.get("created_at")),
                "end_date": _normalize_api_date(intern.get("end_date")) or None,
                "is_active": intern.get("status") == 6,  # Status 6 appears to be "ongoing"
                "stipend": internship_details.get("internship_stipend"),
                "internship_type": internship_details.get("internship_type"),
            }

            normalized.append(normalized_intern)

        return normalized

    def _scaffold_workspace(self, create_samples: bool) -> None:
        """Scaffold the local workspace directories and copy essential files."""
        # Create directories
        Path("entries").mkdir(exist_ok=True)
        Path("previous_entries").mkdir(exist_ok=True)
        skills_dir = Path("skills")
        skills_dir.mkdir(exist_ok=True)

        # Copy skills mapping
        import sys

        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent.parent

        src_skills = base_path / "autodiary" / "resources" / "skills_mapping.json"
        dest_skills = skills_dir / "skills_mapping.json"

        try:
            if src_skills.exists():
                import shutil

                shutil.copy2(src_skills, dest_skills)
        except Exception as e:
            print_error(f"Failed to copy skills mapping: {e}")

        if create_samples:
            self._create_sample_entries()

    def _create_sample_entries(self) -> None:
        """
        Create sample diary entries file for new users to try the upload feature.
        """

        # Get current configuration for context
        try:
            config = self.config_manager.config
            internship_title = config.internship_title or "Internship"
            company_name = config.company_name or "Company"
        except Exception:
            internship_title = "Internship"
            company_name = "Company"

        # Create realistic sample entries (with user-friendly skill suggestions)
        today = date.today()
        sample_entries = []

        # Entry 1: First day (using common skills: Python, Git)
        sample_entries.append(
            {
                "description": f"On my first day of the {internship_title} at {company_name}, I set up my development environment and met with my mentor. We discussed the project roadmap and my learning objectives for the internship.",
                "hours": 8,
                "links": "",
                "blockers": "",
                "learnings": "I learned about the company's development workflow, coding standards, and the project architecture we'll be working with.",
                "mood_slider": 5,
                "skill_ids": ["3", "63"],  # Python (3), Git (63) - common skills
                "date": (today - timedelta(days=7)).isoformat(),
            }
        )

        # Entry 2: Learning phase (Data modeling, Data visualization)
        sample_entries.append(
            {
                "description": f"Started working on understanding the existing codebase and architecture documentation. Reviewed the project structure and familiarized myself with the tools and technologies used at {company_name}.",
                "hours": 8,
                "links": "https://github.com/project",
                "blockers": "Some documentation was outdated, had to cross-reference with team members",
                "learnings": "Improved my understanding of microservices architecture and API design patterns. Learned about the company's internal tools and development processes.",
                "mood_slider": 4,
                "skill_ids": ["44", "16"],  # Data modeling (44), Data visualization (16)
                "date": (today - timedelta(days=6)).isoformat(),
            }
        )

        # Entry 3: Active work (SQL, Data modeling)
        sample_entries.append(
            {
                "description": "Began implementing user authentication module using best security practices. Worked on JWT token implementation, session management, and password encryption following OWASP guidelines.",
                "hours": 8,
                "links": "https://owasp.org/www-project-top-ten/",
                "blockers": "",
                "learnings": "Deepened my knowledge of JWT tokens, OAuth flows, secure session management, and authentication security best practices. Gained hands-on experience with production-grade security implementation.",
                "mood_slider": 5,
                "skill_ids": ["20", "44"],  # SQL (20), Data modeling (44)
                "date": (today - timedelta(days=5)).isoformat(),
            }
        )

        # Entry 4: Database work (Database design, SQL)
        sample_entries.append(
            {
                "description": "Worked on database schema optimization and query performance tuning. Analyzed slow queries, added appropriate indexes, and refactored complex joins for better performance.",
                "hours": 8,
                "links": "",
                "blockers": "Had to coordinate with DBA team for schema changes",
                "learnings": "Learned advanced SQL optimization techniques, query execution plans, and database indexing strategies. Improved my ability to write efficient database queries.",
                "mood_slider": 4,
                "skill_ids": ["19", "20"],  # Database design (19), SQL (20)
                "date": (today - timedelta(days=4)).isoformat(),
            }
        )

        # Entry 5: Team collaboration (Multiple skills)
        sample_entries.append(
            {
                "description": "Participated in daily standup meeting and sprint planning. Collaborated with team members on feature implementation and code reviews. Contributed to technical discussions and architectural decisions.",
                "hours": 8,
                "links": "",
                "blockers": "",
                "learnings": "Improved my communication skills and learned about agile methodologies. Gained experience in collaborative development and team dynamics.",
                "mood_slider": 5,
                "skill_ids": ["3", "44", "16"],  # Python, Data modeling, Data visualization
                "date": (today - timedelta(days=3)).isoformat(),
            }
        )

        # Ensure entries directory exists
        entries_dir = Path("entries")
        entries_dir.mkdir(exist_ok=True)

        # Write sample entries to file
        sample_file = entries_dir / "diary_entries.json"

        with open(sample_file, "w", encoding="utf-8") as f:
            json.dump(sample_entries, f, indent=2)

        print_success(f"Created sample entries file: {sample_file}")
        print_info(f"The file contains {len(sample_entries)} sample diary entries")
        print_info("Sample entries include common skill IDs (Python: 3, Data modeling: 44, etc.)")
        print_warning("💡 TIP: Use 'Help > View Available Skills' to see all skill IDs!")
        console.print()
        print_info("You can edit this file or create your own entries later.")

    def edit_holiday_settings(self) -> None:
        """Edit holiday settings."""
        console.print()
        print_header("📅 Edit Holiday Settings")

        try:
            config = self.config_manager.load()
            console.print("\n[dim]Current settings:[/dim]")
            console.print(f"  Weekdays: {', '.join(config.holiday_weekdays) or 'None'}")
            console.print(f"  Specific dates: {len(config.holiday_dates)} dates")
        except Exception as e:
            print_error(f"Failed to load configuration: {e}")
            return

        console.print()

        holiday_weekdays = questionary.checkbox(
            "Select days to exclude from uploads (current selections pre-selected):",
            choices=get_valid_weekdays(),
            default=[day.capitalize() for day in config.holiday_weekdays],
        ).ask()

        if holiday_weekdays is None:
            print_warning("Edit cancelled")
            return

        holiday_dates_str = (
            questionary.text(
                "Specific holiday dates (comma-separated YYYY-MM-DD, leave empty to keep current):",
            ).ask()
            or ""
        )

        holiday_dates = []
        if holiday_dates_str.strip():
            holiday_dates = [d.strip() for d in holiday_dates_str.split(",") if d.strip()]
            # Validate
            for d in holiday_dates:
                if not validate_date_format(d):
                    print_error(f"Invalid date: {d}")
                    return

        try:
            config.holiday_weekdays = [day.lower() for day in holiday_weekdays]
            if holiday_dates_str.strip():
                config.holiday_dates = holiday_dates

            self.config_manager.save(config)
            print_success("Holiday settings updated!")

        except Exception as e:
            print_error(f"Failed to update settings: {e}")

    def edit_advanced_settings(self) -> None:
        """Edit advanced settings."""
        console.print()
        print_header("⚙️ Advanced Settings")

        try:
            config = self.config_manager.load()
            console.print("\n[dim]Current settings:[/dim]")
            console.print(f"  Timeout: {config.timeout_seconds}s")
            console.print(
                f"  Request Delay: {config.request_delay_min}-{config.request_delay_max}s"
            )
            console.print(f"  Max Retries: {config.max_retries}")
            console.print(f"  Auto Skip Existing: {config.auto_skip_existing}")
        except Exception as e:
            print_error(f"Failed to load configuration: {e}")
            return

        console.print(
            "\n[yellow]Warning: Only change these if you know what you're doing![/yellow]\n"
        )

        timeout = questionary.text(
            "Request timeout in seconds (leave empty to keep current):",
            validate=lambda x: not x or (x.isdigit() and 1 <= int(x) <= 300) or "Enter 1-300",
        ).ask()

        delay_min = questionary.text(
            "Min request delay in seconds (leave empty to keep current):",
            validate=lambda x: (
                not x or (x.replace(".", "").isdigit() and float(x) >= 0) or "Enter positive number"
            ),
        ).ask()

        delay_max = questionary.text(
            "Max request delay in seconds (leave empty to keep current):",
            validate=lambda x: (
                not x or (x.replace(".", "").isdigit() and float(x) >= 0) or "Enter positive number"
            ),
        ).ask()

        max_retries = questionary.text(
            "Maximum upload retries (leave empty to keep current):",
            validate=lambda x: not x or (x.isdigit() and int(x) >= 1) or "Enter number >= 1",
        ).ask()

        auto_skip = questionary.confirm(
            "Automatically skip existing entries?", default=config.auto_skip_existing
        ).ask()

        if auto_skip is None:
            print_warning("Edit cancelled")
            return

        try:
            if timeout:
                config.timeout_seconds = int(timeout)
            if delay_min:
                config.request_delay_min = float(delay_min)
            if delay_max:
                config.request_delay_max = float(delay_max)
            if config.request_delay_min > config.request_delay_max:
                print_error("Min request delay cannot be greater than max request delay.")
                return
            if max_retries:
                config.max_retries = int(max_retries)

            config.auto_skip_existing = auto_skip

            self.config_manager.save(config)
            print_success("Advanced settings updated!")

        except Exception as e:
            print_error(f"Failed to update settings: {e}")

    def test_connection(self) -> None:
        """Test connection to VTU API."""
        console.print()
        print_header("🔍 Testing Connection")

        try:
            client = VTUApiClient(self.config_manager)
            print_success("Connecting to VTU API...")

            if client.test_connection():
                console.print()
                print_success("✓ Connection successful!")
                console.print("  Your credentials are working correctly.")
                console.print("  The application is ready to use.")
            else:
                console.print()
                print_error("✗ Connection failed!")
                console.print("  Please check your credentials in Configuration.")
                console.print("  Make sure VTU portal is accessible.")

        except Exception as e:
            print_error(f"Connection test failed: {e}")

        console.print()
        questionary.press_any_key_to_continue().ask()

    def view_configuration(self) -> None:
        """View current configuration."""
        console.print()
        print_header("📋 Current Configuration")

        try:
            config = self.config_manager.load()
            internship = self.config_manager.get_internship_config()
            holidays = self.config_manager.get_holiday_config()

            console.print("\n[bold]Credentials:[/bold]")
            console.print(f"  Email: {config.email}")
            console.print(
                f"  Password: {'****** (encrypted)' if config.password_encrypted else 'Not set'}"
            )

            console.print("\n[bold]Internship:[/bold]")
            console.print(f"  ID: {internship.get('id')}")
            console.print(f"  Title: {internship.get('title') or 'Not set'}")
            console.print(f"  Company: {internship.get('company') or 'Not set'}")
            console.print(f"  Start Date: {internship.get('start_date')}")
            console.print(f"  End Date: {internship.get('end_date')}")

            console.print("\n[bold]Holidays:[/bold]")
            console.print(f"  Weekdays: {', '.join(holidays.get('weekdays', [])) or 'None'}")
            console.print(f"  Specific Dates: {len(holidays.get('dates', []))} dates")

            console.print("\n[bold]Advanced:[/bold]")
            console.print(f"  API URL: {config.api_base_url}")
            console.print(f"  Timeout: {config.timeout_seconds}s")
            console.print(
                f"  Request Delay: {config.request_delay_min}-{config.request_delay_max}s"
            )
            console.print(f"  Max Retries: {config.max_retries}")
            console.print(f"  Auto Skip Existing: {config.auto_skip_existing}")

        except Exception as e:
            print_error(f"Failed to load configuration: {e}")

        console.print()
        questionary.press_any_key_to_continue().ask()

    def backup_config(self) -> None:
        """Create a backup of current configuration."""
        console.print()
        print_header("💾 Backup Configuration")

        try:
            backup_path = self.config_manager.backup()
            print_success(f"Configuration backed up to: {backup_path}")
        except Exception as e:
            print_error(f"Failed to create backup: {e}")

        console.print()
        questionary.press_any_key_to_continue().ask()

    def restore_config(self) -> None:
        """Restore configuration from a backup."""
        console.print()
        print_header("🔄 Restore from Backup")

        backups = self.config_manager.list_backups()
        if not backups:
            print_warning("No backups found.")
            questionary.press_any_key_to_continue().ask()
            return

        choices = [
            {"name": f"{b.name} ({b.stat().st_size} bytes)", "value": str(b)} for b in backups
        ]
        choices.append({"name": "← Cancel", "value": "cancel"})

        selected = questionary.select("Select backup to restore:", choices=choices).ask()

        if not selected or selected == "cancel":
            print_warning("Restore cancelled")
            return

        try:
            from pathlib import Path

            self.config_manager.restore(Path(selected))
            print_success("Configuration restored successfully!")
        except Exception as e:
            print_error(f"Failed to restore backup: {e}")

        console.print()
        questionary.press_any_key_to_continue().ask()

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        console.print()
        print_warning("⚠️  This will reset all configuration to defaults!")

        if not questionary.confirm(
            "Are you sure you want to continue? All your settings will be lost.", default=False
        ).ask():
            print_warning("Reset cancelled")
            return

        try:
            self.config_manager.reset_to_default()
            print_success("Configuration reset to defaults!")
            print_info("Please run the setup wizard again.")

            if questionary.confirm("Run setup wizard now?", default=True).ask():
                self.run_setup_wizard()

        except Exception as e:
            print_error(f"Failed to reset configuration: {e}")

    def _accept_terms_and_conditions(self) -> bool:
        """Show setup terms and require acknowledgement before collecting credentials."""
        console.print()
        print_header("Terms and Responsible Use")
        console.print(
            "\n[bold]Please read before continuing:[/bold]\n"
            "  • AutoDiary is provided for educational and personal productivity purposes.\n"
            "  • You are responsible for using it only with your own VTU account and data.\n"
            "  • Do not use it for abuse, disruption, unauthorized access, or harm to any system.\n"
            "  • The developers provide this tool in good faith and are not responsible for misuse.\n"
            "  • You should follow your institution's rules and the VTU portal's terms.\n"
        )

        accepted = questionary.confirm(
            "I understand and agree to use AutoDiary responsibly.", default=False
        ).ask()

        if not accepted:
            print_warning("Setup cannot continue unless the terms are accepted.")
            return False

        return True
