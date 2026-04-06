"""
CLI utility functions for rich console output and formatting.
"""

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.text import Text

console = Console()


def print_success(message: str) -> None:
    """Print a success message in green."""
    console.print(f"[green][OK][/green] {message}")


def print_error(message: str) -> None:
    """Print an error message in red."""
    console.print(f"[red][ERROR][/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    console.print(f"[yellow][WARNING][/yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message in cyan."""
    console.print(f"[cyan][INFO][/cyan] {message}")


def print_header(title: str, subtitle: str = "") -> None:
    """Print a formatted header."""
    if subtitle:
        console.print(Panel.fit(f"[bold cyan]{title}[/bold cyan]\n{subtitle}", border_style="cyan"))
    else:
        console.print(Panel.fit(f"[bold cyan]{title}[/bold cyan]", border_style="cyan"))


def create_progress_bar() -> Progress:
    """Create a rich progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    )


def create_table(title: str, columns: list[str]) -> Table:
    """Create a rich table with the given columns."""
    table = Table(title=title, show_header=True, header_style="bold magenta")
    for column in columns:
        table.add_column(column)
    return table


def print_panel(content: str, title: str = "", border_style: str = "blue") -> None:
    """Print content in a formatted panel."""
    console.print(Panel.fit(content, title=title, border_style=border_style))


def format_entry_date(date_str: str) -> Text:
    """Format a date string with color."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = dt.strftime("%A")
        return Text(f"{date_str} ({day_name})", style="cyan")
    except ValueError:
        return Text(date_str, style="red")


def format_hours(hours: int) -> Text:
    """Format hours with color."""
    color = "green" if hours >= 8 else "yellow" if hours >= 4 else "red"
    return Text(f"{hours}h", style=color)


def format_mood(mood: int) -> Text:
    """Format mood slider with emoji and color."""
    mood = max(1, min(5, mood))  # Clamp between 1-5 to prevent format bleed
    emoji = "😊" if mood >= 4 else "😐" if mood >= 3 else "😔"
    color = "green" if mood >= 4 else "yellow" if mood >= 3 else "red"
    return Text(f"{emoji} {mood}/5", style=color)
