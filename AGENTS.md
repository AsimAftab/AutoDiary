# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `src/autodiary/`. Keep menu and prompt flows in `src/autodiary/cli/`, API and config logic in `src/autodiary/core/`, data models in `src/autodiary/models/`, helpers in `src/autodiary/utils/`, and packaged templates or metadata in `src/autodiary/resources/`. Contributor-facing docs live in `docs/`, build helpers in `scripts/`, and release automation in `.github/workflows/release.yml`. Generated output belongs in `build/`, `dist/`, `.venv/`, `.ruff_cache/`, and `__pycache__/`.

## Build, Test, and Development Commands
Use `uv` as the default workflow for local development and dependency management:

```powershell
uv sync
uv run python -m autodiary
uv run autodiary
```

Run quality checks before every PR:

```powershell
uv run ruff format --check .
uv run ruff check .
```

Build the Windows executable with `uv run pyinstaller --clean autodiary.spec` or `scripts\build.bat`. Use `scripts/build.sh` on Unix-like systems. GitHub Releases trigger `.github/workflows/release.yml`, which installs with `uv`, runs Ruff, builds the executable, and uploads `dist/AutoDiary.exe`.

## Coding Style & Naming Conventions
Use 4-space indentation, double quotes, and a 100-character line target as defined in `pyproject.toml`. Follow existing Python naming: `snake_case` for modules, functions, and variables; `PascalCase` for classes. Keep terminal rendering in `src/autodiary/cli/` and avoid mixing UI concerns into `src/autodiary/core/`. Let Ruff enforce import order, pyupgrade rules, and common bugbear checks instead of hand-tuning style.

## Testing Guidelines
There is no committed automated test suite yet, so manual verification is required for every change. At minimum, run `uv run python -m autodiary` and exercise the affected menu path, config loading, and any JSON or template handling you touched. If you add automated coverage, place tests under `tests/` and name files `test_<module>.py` so the suite can grow predictably.

## Commit & Pull Request Guidelines
Use short, scoped commit messages. The history already uses Conventional Commit style, for example `feat: add diary entry records...`; continue that pattern where practical. PRs should include a concise summary, linked issue or rationale, manual verification notes, and screenshots only when terminal output or menu behavior changed materially. If a change affects packaging or releases, mention the expected impact on `autodiary.spec` or the GitHub release workflow.

## Security & Configuration Tips
Never commit `.env`, `.encryption_key`, local config files, or built `.exe` artifacts. Use the templates under `src/autodiary/resources/templates/` and the docs in `docs/` for local setup examples.
