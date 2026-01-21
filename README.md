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
- Set your API key securely: `aicmd --set-api-key <provider> <your_api_key>`
- Example: `aicmd --set-api-key openrouter sk-or-v1-your-key-here`

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
- API key management: `--set-api-key PROVIDER KEY`, `--list-api-keys`, `--get-api-key PROVIDER`, `--delete-api-key PROVIDER`
- Provider management: `--list-providers`, `--test-provider PROVIDER`
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
  "version": "1.0.1",
  "basic": {
    "interactive_mode": true,
    "cache_enabled": true,
    "auto_copy_threshold": 1.0,
    "manual_confirmation_threshold": 0.7
  },
  "api": { "timeout_seconds": 30, "max_retries": 3, "default_provider": "openrouter" },
  "providers": {
    "openrouter": { "model": "", "base_url": "https://openrouter.ai/api/v1/chat/completions" },
    "openai": { "model": "gpt-3.5-turbo", "base_url": "https://api.openai.com/v1/chat/completions" },
    "deepseek": { "model": "deepseek-chat", "base_url": "https://api.deepseek.com/v1/chat/completions" },
    "xai": { "model": "grok-beta", "base_url": "https://api.x.ai/v1/chat/completions" },
    "gemini": { "model": "gemini-pro", "base_url": "https://generativelanguage.googleapis.com/v1beta/models" },
    "qwen": { "model": "qwen-turbo", "base_url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation" }
  },
  "cache": { "cache_directory": "~/.ai-cmd", "database_file": "cache.db", "max_cache_age_days": 30, "cache_size_limit": 1000 },
  "interaction": { "interaction_timeout_seconds": 30, "positive_weight": 0.3, "negative_weight": 0.6, "similarity_threshold": 0.6, "confidence_threshold": 0.75 },
  "display": { "show_confidence": false, "show_source": false, "colored_output": true }
}
```

Note: API keys are stored securely in system keyring, not in config files.

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

Supported Providers
- **OpenRouter** (default): Multi-model API gateway
- **OpenAI**: GPT models (gpt-3.5-turbo, gpt-4, etc.)
- **DeepSeek**: DeepSeek Chat models
- **xAI/Grok**: Grok models (grok-beta)
- **Google Gemini**: Gemini Pro models
- **Alibaba Qwen**: Qwen Turbo models

Each provider supports custom model and base_url configuration.

API Key Management
- Keys are stored securely in system keyring (not in config files)
- Set key: `aicmd --set-api-key <provider> <key>`
- List configured providers: `aicmd --list-api-keys`
- Test provider: `aicmd --test-provider <provider>`
- Remove key: `aicmd --delete-api-key <provider>`

Troubleshooting
- "API key not found": use `aicmd --set-api-key <provider> <key>` to store your API key securely
- "No model specified": set the model with `aicmd --set-config providers.<provider>.model <model_name>`
- "Rate limit exceeded": the client retries; try again or configure a backup provider
- Cache disabled due to errors: run `aicmd --reset-errors`, check `~/.ai-cmd/logs/`
- Provider issues: use `aicmd --test-provider <provider>` to diagnose configuration problems
- Configuration validation: use `aicmd --validate-config` to check for issues

Development
- Install: `uv sync`
- Run CLI locally: `uv run aicmd "list all files"`
- Format/lint: `uv run black src/` and `uv run flake8 src/`
- Tests: `uv run python -m pytest`

License
- MIT. See repository for details.
