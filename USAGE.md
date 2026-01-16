# aicmd – Usage Guide

This guide explains how to use aicmd effectively: options, workflows, configuration, cache behavior, and safety.

Getting started
- Install with uv
  - `uv sync`
  - `uv pip install -e .`
- Configure API key
  - `aicmd --create-config` to generate `~/.ai-cmd/settings.json`
  - Edit the file and add your API key to the provider configuration (e.g., `providers.openrouter.api_key`)
- First run
  - `aicmd "list all files"`
  - Enable interactive mode in settings if desired

Basic usage
- `aicmd "<prompt>"` converts your prompt to a shell command.
- Multi-word prompts are supported; quotes are recommended.
- By default, if interactive mode is disabled, the command is printed and copied to clipboard (unless `--no-clipboard`).

CLI options
- `-v, --version`: Show version information.
- `--config`: Show current configuration summary.
- `--show-config`: Show detailed configuration with sources.
- `--create-config`: Create user configuration file at `~/.ai-cmd/settings.json`.
- `--create-config-force`: Create (overwrite) user configuration file.
- `--validate-config`: Validate current configuration values and ranges.
- `--set-config KEY VALUE`: Update a configuration key (e.g., `--set-config interactive_mode true`).
- `--force-api`: Force a fresh API call (bypass cache and interactive flow).
- `--disable-interactive`: Disable interactive mode for this run.
- `--status`: Show cache and interaction statistics.
- `--reset-errors`: Reset internal error state and re-enable cache if disabled.
- `--no-color`: Disable colored output.
- `--no-clipboard`: Do not copy results to clipboard.
- `--recalculate-confidence`: Recompute confidence scores for all cached entries.
- `--json`: Output a JSON object instead of plain text.
- `--base-url URL`: Override API base URL (useful for proxies).
- `--cleanup-cache`: Clean expired/oversized cache entries (TTL and size limit).

Interactive vs basic mode
- Basic mode
  - Active when `interactive_mode` is false or when `--force-api`/`--disable-interactive` is used.
  - Directly calls the API and prints the command, copying to clipboard unless disabled or deemed unsafe.
- Interactive mode
  - Enabled by setting `basic.interactive_mode: true` in config.
  - Shows confidence and similarity metrics when available.
  - Performs safety checks and may force confirmation or disable auto-copy for risky commands.
  - Asks for confirmation based on thresholds: `confidence_threshold`, `manual_confirmation_threshold`, `auto_copy_threshold`.

JSON output
- Use `--json` to receive structured output:
```
{
  "command": "ls -la",
  "source": "API | Cache | Similar Cache | FALLBACK",
  "confidence": 0.83,
  "similarity": 0.92,
  "dangerous": false,
  "confirmed": true
}
```

Configuration
- Sources and priority
  - User file: `~/.ai-cmd/settings.json`
  - Project file: `./.ai-cmd.json`
  - Built-in defaults fill the rest.
- Create template: `aicmd --create-config` (or `--create-config-force`)
- Inspect: `aicmd --show-config`
- Validate: `aicmd --validate-config`
- Update: `aicmd --set-config KEY VALUE`
- Key highlights (full structure in README)
  - `basic`: `interactive_mode`, `cache_enabled`, thresholds: `auto_copy_threshold`, `manual_confirmation_threshold`
  - `api`: `timeout_seconds`, `max_retries`, `use_backup_model`, `default_provider`
  - `providers`: Configure API keys and models for OpenRouter, OpenAI, DeepSeek, xAI, Gemini, Qwen
  - `cache`: `cache_directory`, `database_file`, `max_cache_age_days`, `cache_size_limit`
  - `interaction`: `interaction_timeout_seconds`, `positive_weight`, `negative_weight`, `similarity_threshold`, `confidence_threshold`
  - `display`: `colored_output`, `show_confidence`, `show_source`

Cache and confidence
- Storage: SQLite at `~/.ai-cmd/cache.db` by default (configurable path and file).
- Exact matches: confidence is computed from confirmations/rejections with time-decay.
- Similar matches: Jaccard + sequence similarity; best match considered if above `similarity_threshold`.
- Threshold logic
  - `auto_copy_threshold`: at or above this confidence, auto-copy unless safety prevents it.
  - `manual_confirmation_threshold`: confidence band where explicit confirmation is required.
  - `confidence_threshold`: minimum confidence for using cache vs calling API.
- Maintenance
  - `aicmd --cleanup-cache` (TTL via `max_cache_age_days` and size via `cache_size_limit`).
  - `aicmd --recalculate-confidence` to batch recompute scores.

Safety
- Detects risky patterns (`rm -rf`, `dd of=/dev/...`, filesystem formatting, mass delete, etc.).
- May force confirmation and disable automatic clipboard copy for dangerous commands.
- Always review commands before running them.

Examples
- Force fresh result and JSON output
  - `aicmd "show open ports" --force-api --json`
- Work non-interactively in scripts
  - `aicmd "list large files" --disable-interactive --no-clipboard`
- Use a proxy base URL
  - `aicmd "download file" --base-url https://proxy.example/api/v1/chat/completions`

Troubleshooting
- Missing API key: create config with `aicmd --create-config` and set your provider API key in `~/.ai-cmd/settings.json`.
- No model configured: set the model in your provider configuration or enable `use_backup_model` with a backup.
- Rate limit/timeout: automatic retries are enabled; try again later or provide a backup model.
- Cache disabled after errors: `aicmd --reset-errors` and check logs under `~/.ai-cmd/logs/`.

