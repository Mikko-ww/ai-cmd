AI Command (aicmd)
===================

A smart CLI that converts natural language into shell commands with caching, safety checks, and interactive confirmation — powered by OpenRouter.

Why you'll like it
- Natural language to shell commands (no extra prose)
- Smart cache with confidence learning and time-decay
- Interactive confirmation with safety warnings and clipboard copy
- Similar-query reuse to avoid repeated API calls
- JSON output for scripting and automation
- Graceful degradation: even if cache/DB fails, API flow still works

Quick start
1) Install dependencies and the CLI

- Using uv (recommended)
  - `uv sync`
  - `uv pip install -e .`

2) Configure your API key (required)

- Create config file: `aicmd --create-config`
- Edit `~/.ai-cmd/settings.json` and add your API key to the provider configuration
- Example: Set `providers.openrouter.api_key` to your OpenRouter API key

3) Run a prompt

- `aicmd "list all files recursively"`

4) Enable interactive mode (optional)

- `aicmd --create-config` then set `basic.interactive_mode` to `true` in `~/.ai-cmd/settings.json`
- Or inspect with `aicmd --show-config`

CLI at a glance
- Basic: `aicmd "<prompt>"`
- Force API only: `--force-api`
- Disable interactive (for this run): `--disable-interactive`
- Output JSON: `--json`
- No clipboard/color: `--no-clipboard`, `--no-color`
- Status and maintenance: `--status`, `--reset-errors`, `--cleanup-cache`, `--recalculate-confidence`
- Config helpers: `--config`, `--show-config`, `--create-config`, `--create-config-force`, `--validate-config`, `--set-config KEY VALUE`
- Networking: `--base-url https://proxy.example/api/v1/chat/completions`

Configuration
- Locations (highest priority last-write wins)
  - User config: `~/.ai-cmd/settings.json`
  - Project config: `./.ai-cmd.json`
  - Built-in defaults

- Create a starter config
  - `aicmd --create-config` (or `--create-config-force` to overwrite)

- Show and validate
  - `aicmd --show-config`
  - `aicmd --validate-config`

- Update a key
  - `aicmd --set-config interactive_mode true`

- Sample config (abbreviated)
```
{
  "version": "1.0.0",
  "basic": {
    "interactive_mode": true,
    "cache_enabled": true,
    "auto_copy_threshold": 1.0,
    "manual_confirmation_threshold": 0.7
  },
  "api": { "use_backup_model": false, "timeout_seconds": 30, "max_retries": 3 },
  "cache": { "cache_directory": "~/.ai-cmd", "database_file": "cache.db", "max_cache_age_days": 30, "cache_size_limit": 1000 },
  "interaction": { "interaction_timeout_seconds": 30, "positive_weight": 0.3, "negative_weight": 0.6, "similarity_threshold": 0.6, "confidence_threshold": 0.75 },
  "display": { "show_confidence": false, "show_source": false, "colored_output": true }
}
```

Behavior and workflow
- Modes
  - Basic mode: when `interactive_mode` is false or `--force-api`/`--disable-interactive` is used; directly calls the API and copies the command (unless disabled).
  - Interactive mode: shows confidence/similarity, runs safety checks, asks for confirmation depending on thresholds, and learns from your feedback.

- Cache and learning
  - SQLite DB: `~/.ai-cmd/cache.db` (configurable path/filename)
  - Exact-match hits compute a confidence score from confirmations/rejections with time-decay
  - Similar-query suggestions when no exact match (Jaccard + sequence similarity)
  - Maintenance: `--cleanup-cache` (TTL/size), `--recalculate-confidence`

- Safety checks
  - Detects potentially dangerous commands (e.g., `rm -rf`, `dd of=/dev/...`, etc.)
  - Can force confirmation and disable auto-copy for risky commands

- JSON output
  - `--json` prints: `{ command, source, confidence, similarity, dangerous, confirmed }`

Troubleshooting
- "API key not found": create config with `aicmd --create-config` and set your provider API key in `~/.ai-cmd/settings.json`
- "No model specified": set the model in your provider configuration or enable backup via config
- "Rate limit exceeded": the client retries; try again or set a backup model
- Cache disabled due to errors: run `aicmd --reset-errors`, check `~/.ai-cmd/logs/`

Development
- Install: `uv sync`
- Run CLI locally: `uv run aicmd "list all files"`
- Format/lint: `uv run black src/` and `uv run flake8 src/`
- Tests: `uv run python -m pytest`

License
- MIT. See repository for details.
