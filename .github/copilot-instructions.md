# ai-cmd Project Guidelines

## Project Overview
This is a minimalist command-line tool that converts natural language prompts to shell commands using OpenRouter API. The entire application consists of a single Python file (`ai.py`) with focused functionality.

## Architecture & Key Files
- **`ai.py`**: The complete application - API client, command parsing, clipboard integration
- **`pyproject.toml`**: Defines the `aicmd` console script entry point pointing to `ai:main`
- **`.env`**: Required for OpenRouter API key (`AI_CMD_OPENROUTER_API_KEY`) and model selection

## Development Workflows

### Package Management with uv
This project uses `uv` (not pip/conda). Always use:
```bash
uv sync          # Install dependencies
uv add <package> # Add new dependencies
uv run aicmd     # Run the tool
```

### Testing & Quality
Use the predefined VS Code tasks:
- "安装依赖" - `uv sync`
- "运行 ai-cmd" - `uv run aicmd ${input:prompt}`
- "格式化代码" - `uv run black ai.py`
- "检查代码质量" - `uv run flake8 ai.py`

### Environment Setup
Always create `.env` from `.env.example`:
```bash
cp .env.example .env
# Then edit .env with actual API key
```

## Code Patterns & Conventions

### Single-File Architecture
- All functionality in `ai.py` - no modules or packages
- Simple functions: `get_shell_command()` for API calls, `main()` for CLI
- Direct imports at top: `requests`, `pyperclip`, `dotenv`

### Error Handling
- Check for missing API key with `os.getenv()` validation
- Handle HTTP errors with status code checks
- Return error strings rather than raising exceptions

### API Integration
- Uses OpenRouter chat completions endpoint
- System prompt enforces "shell command only" responses
- Model configurable via `AI_CMD_OPENROUTER_MODEL` env var

### User Experience
- Automatically copies output to clipboard with `pyperclip`
- Minimal output - just the command, no extra formatting
- Command-line args joined with spaces as single prompt

## Development Environment
- Python 3.11+ required (see `pyproject.toml`)
- VS Code configured for Black formatting and Flake8 linting
- `.venv` virtual environment expected in project root
- Environment variables loaded from `.env` file automatically

## Adding Features
When extending functionality:
1. Keep everything in `ai.py` unless compelling reason to split
2. Maintain the simple request/response pattern
3. Use environment variables for configuration
4. Test with `uv run aicmd "your test prompt"`
