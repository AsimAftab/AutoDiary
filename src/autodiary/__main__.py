#!/usr/bin/env python3
"""
VTU Auto Diary Filler - Main Entry Point
"""

import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from autodiary.cli.main_menu import MainMenu
from autodiary.core.config import ConfigManager
from autodiary.utils.validators import validate_first_run

console = Console()


def main():
    """Main entry point for the application."""
    try:
        # Initialize directories and configuration
        config_dir = Path.home() / ".autodiary"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "config.json"

        # Configure local file logging for diagnostics
        log_path = config_dir / "autodiary.log"
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filemode="a",
        )
        logging.info("--- AutoDiary Bootstrapped ---")

        config_manager = ConfigManager(config_path)

        # Check if first run
        if validate_first_run(config_path):
            console.print(
                Panel.fit(
                    "[bold cyan]Welcome to VTU Auto Diary Filler![/bold cyan]\n\n"
                    "This appears to be your first time running the application.\n"
                    "Let's set up your configuration.",
                    title="🎉 First-Time Setup",
                    border_style="cyan",
                )
            )
            # First-run setup will be handled in main menu

        # Start main menu
        main_menu = MainMenu(config_manager)
        main_menu.show()

    except KeyboardInterrupt:
        logging.info("Application interrupted heavily by user termination.")
        console.print("\n\n[yellow]Application interrupted by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        logging.exception(f"Fatal application crash captured: {e}")
        console.print(
            f"\n\n[red]An unexpected error occurred. See `~/.autodiary/autodiary.log` for full traceback: {e}[/red]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
