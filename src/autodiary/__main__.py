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


def _configure_logging(config_dir: Path) -> list[Path]:
    """Configure diagnostics logging and return the paths that were enabled."""
    log_paths = [config_dir / "autodiary.log"]

    if getattr(sys, "frozen", False):
        exe_log_path = Path(sys.executable).resolve().parent / "autodiary.log"
        if exe_log_path not in log_paths:
            log_paths.append(exe_log_path)

    handlers: list[logging.Handler] = []
    active_paths: list[Path] = []
    log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    for log_path in log_paths:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
            handler.setFormatter(log_format)
            handlers.append(handler)
            active_paths.append(log_path)
        except OSError:
            continue

    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)
    logging.info("--- AutoDiary Bootstrapped ---")
    logging.info("Diagnostics log path(s): %s", ", ".join(str(path) for path in active_paths))
    return active_paths


def main():
    """Main entry point for the application."""
    log_paths: list[Path] = []
    try:
        # Initialize directories and configuration
        config_dir = Path.home() / ".autodiary"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "config.json"

        # Configure local file logging for diagnostics
        log_paths = _configure_logging(config_dir)

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
        log_help = ", ".join(str(path) for path in log_paths) or "~/.autodiary/autodiary.log"
        console.print(
            f"\n\n[red]An unexpected error occurred. See `{log_help}` for full traceback: {e}[/red]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
