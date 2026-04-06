# Development Guide

Welcome! Thank you for considering contributing to the **VTU Auto Diary** CLI. We maintain a very fast, minimal, and incredibly modern Python stacks. We use the **Astral `uv` Ecosystem** to handle all packaging, rendering, and dependencies.

This document will help you onboard seamlessly from cloning the codebase to compiling the final Windows executable.

## ⚡ Prerequisites

To develop logically and securely with our stack, you **only** need:
1. **Python 3.8+**
2. **`uv`** (The blazing fast Python package manager written in Rust).
   - [Install `uv` Here](https://docs.astral.sh/uv/getting-started/installation/)

## 🚀 Quickstart Onboarding

You do not need to configure virtual environments, run `pip install`, or activate anything manually. Our `pyproject.toml` handles the whole ecosystem.

```powershell
# 1. Clone the repository
git clone https://github.com/AsimAftab/AutoDiary.git
cd AutoDiary

# 2. Sync the environment INSTANTLY
# This automatically creates an isolated `.venv` and installs all dependencies and dev-tools.
uv sync

# 3. Run the CLI
uv run python -m autodiary
# Or via the registered command
uv run autodiary
```

## 🏗️ Project Architecture (src Layout)

We strictly use the **`src` Layout** to ensure the codebase remains production-grade.

```text
AutoDiary/
├── src/
│   └── autodiary/           <-- Core CLI Application code
│       ├── cli/             <-- User Interface logic (Rich, Typer, Questionary)
│       ├── core/            <-- Underlying API interactions and logic
│       ├── models/          <-- Data logic (PyDantic)
│       └── resources/       <-- Embedded templates & mappings
├── pyproject.toml           <-- Single source of truth for dependencies and scripts
├── autodiary.spec           <-- Configuration for the Windows PyInstaller compiler
└── uv.lock                  <-- Frozen dependency states (Always commit this!)
```

## 🛠️ Essential Development Commands

We rely heavily on `uv run <command>` which safely executes logic purely inside the isolated virtual environment.

### Code Hygiene (Ruff)
Before opening a Pull Request, ensure your code aligns with the repository's strict formatting. We use `ruff` (also an Astral tool) which runs in milliseconds.

```powershell
# Format your code automatically
uv run ruff format .

# Check for linting bugs and issues
uv run ruff check .
```

### Compiling to an Executable
If you are developing a new feature and want to test the standalone natively-compiled `.exe` file just as the user would:

```powershell
# Clean build the PyInstaller executable via our .spec config
uv run pyinstaller --clean autodiary.spec
```
The compiled executable will be automatically spit out inside the `dist/` directory. (Never commit the `dist/` or `build/` directories to source control).

## 💡 Troubleshooting
*   **"Module Not Found" ?** If your IDE is complaining that `rich` or `requests` isn't found, ensure your IDE's Python Interpreter is pointing to the natively generated `.venv` directory root! 
*   **"Missing entry files" ?** The `.exe` or `uv run` will natively scaffold dummy text files (`entries/`, `previous_entries/`) wherever it is executed the first time if you walk through the configuration wizard.

---

*Thank you for contributing! Let's build something brilliant together.*
