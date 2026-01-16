# Repository Guidelines

## Project Structure & Module Organization
- `src/aicmd/`: Core package (CLI in `ai.py`; config, cache, database, interaction, logging utilities; `setting_template.json`).
- `pyproject.toml`: Packaging, console script entry (`aicmd`), dev deps.
- Docs: `README.md`, `USAGE.md`.
- Config/Cache: user config `~/.ai-cmd/settings.json`; project config `.ai-cmd.json`; cache DB `~/.ai-cmd/cache.db`.

## Build, Test, and Development Commands
- Install deps: `uv sync`
- Editable install: `uv pip install -e .`
- Run CLI: `aicmd "list all files"` (or `uv run aicmd ...`)
- Lint/format: `uv run black src/` · `uv run flake8 src/`
- Tests: `uv run python -m pytest`

## Coding Style & Naming Conventions
- Python 3.9+, 4‑space indent; format with Black; lint with Flake8.
- Naming: modules `lower_snake_case`; functions/vars `lower_snake_case`; classes `PascalCase`; constants `UPPER_SNAKE_CASE`.
- CLI options must match documented flags (`--status`, `--force-api`, `--disable-interactive`, etc.).
- Use the project logger (see `src/aicmd/logger.py`) instead of `print` for diagnostics.

## Testing Guidelines
- Framework: `pytest`. Place tests under `tests/`, mirroring `aicmd` structure; files named `test_*.py`.
- Isolate external effects: mock `requests.Session.post`, environment variables, and clipboard; use temp dirs for cache (`~/.ai-cmd`) and project configs.
- Run locally with `uv run python -m pytest` before opening a PR.

## Commit & Pull Request Guidelines
- Commits: concise, present‑tense summaries; group related changes. The history favors descriptive messages (often Chinese); Conventional Commits are welcome but not required.
- Branches: `feat/...`, `fix/...`, `docs/...`, `refactor/...`.
- PRs must include: clear description and rationale, linked issues, usage notes or example CLI output for user‑visible changes, and updates to docs/config templates when flags or behavior change.
- Pre‑merge checklist: `uv sync`, format + lint, tests pass.

## Security & Configuration Tips
- Never commit cache DBs or sensitive configuration files.
- Configure API keys in `~/.ai-cmd/settings.json` using the providers section.
- Helpful: `aicmd --create-config`, `aicmd --validate-config`, `aicmd --show-config`.

## Test Script Location
- **CRITICAL**: When creating test scripts, always use the project's `./tmp/` directory, NOT the system `/tmp/` directory.
- Correct: `cat > ./tmp/test_example.sh` or `./tmp/test_api_key_preview.sh`
- Incorrect: `cat > /tmp/test_example.sh` (this writes to system root `/tmp`, not the project)
- Always include the `./` prefix to ensure scripts are created in the project's `tmp/` folder.

