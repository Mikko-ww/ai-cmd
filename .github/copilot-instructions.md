# AI Command Line Tool - AI Agent Instructions

## Project Architecture

This is an intelligent CLI tool that converts natural language to shell commands using OpenRouter API, with sophisticated caching and user interaction features.

### Core Architecture Pattern
- **Graceful Degradation**: All enhanced features (caching, confidence scoring, user interaction) wrap around the basic API functionality in `get_shell_command_original()`. Any failure in enhanced features automatically falls back to basic mode.
- **Multi-layer Configuration**: Environment variables > JSON config files > defaults, with validation and type conversion throughout.
- **Database-backed Caching**: SQLite with cross-platform safety, confidence scoring, and similarity matching for query optimization.

### Key Components

**Primary Flow (`ai.py`)**: 
- `get_shell_command()` orchestrates all components with fallback to `get_shell_command_original()`
- Interactive vs non-interactive modes change behavior significantly
- Confidence thresholds determine auto-copy vs user confirmation

**Configuration (`config_manager.py`)**:
- Nested JSON structure in `setting_template.json` flattened to simple keys
- User config: `~/.ai-cmd/settings.json`, Project config: `.ai-cmd.json`
- Environment variables use `AI_CMD_*` prefix

**Caching System**:
- `cache_manager.py`: CRUD operations with `CacheEntry` model
- `database_manager.py`: Thread-safe SQLite with graceful degradation
- `confidence_calculator.py`: Bayesian-style scoring with time decay
- `query_matcher.py`: Semantic similarity for fuzzy matching

## Development Workflows

### Essential Commands
```bash
uv sync                              # Install/sync dependencies
uv pip install -e .                  # Editable install
aicmd "list files" --force-api       # Test basic functionality
aicmd --status                       # Debug cache/confidence stats
aicmd --create-config                # Generate user config
```

### Testing Strategy
- No formal test suite currently exists
- Manual testing uses `--force-api`, `--disable-interactive`, `--status` flags
- Cache debugging with `--recalculate-confidence`, `--cleanup-cache`
- Configuration validation with `--validate-config`, `--show-config`

### Configuration Debugging
Interactive mode behavior changes dramatically based on thresholds:
- `auto_copy_threshold` (0.9): Auto-copy without confirmation
- `confidence_threshold` (0.8): Minimum for cache usage
- `similarity_threshold` (0.7): Fuzzy matching cutoff

## Project-Specific Patterns

### Error Handling Philosophy
Every enhanced feature uses `GracefulDegradationManager` to ensure the basic API functionality always works. Never let caching/interaction failures break core functionality.

### Database Schema Awareness
The SQLite schema includes OS/shell context fields for cross-platform compatibility. Hash strategies ("simple" vs "normalized") affect query matching behavior.

### Safety System
`CommandSafetyChecker` integrates with confidence scoring - dangerous commands force confirmation even with high confidence scores. Auto-clipboard copying can be disabled for security.

### Confidence Scoring Logic
- Time-based decay of confidence over time
- Positive/negative feedback weights from user confirmations
- Combined with similarity scores for fuzzy matches
- Recalculation affects entire cache when algorithm changes

## Integration Points

### OpenRouter API Client
- Supports primary/backup models via environment variables
- Custom base URLs for proxy/testing scenarios
- Fallback model switching on API failures

### Cross-platform Input Handling
`cross_platform_input.py` provides timeout-based user input across Windows/Unix systems for interactive confirmation prompts.

### Clipboard Integration
Automatic clipboard copying with safety override - uses `pyperclip` with graceful degradation on clipboard failures.

## Key Files for Understanding

- `src/aicmd/ai.py`: Main orchestration and CLI entry point
- `src/aicmd/setting_template.json`: Complete configuration structure reference
- `src/aicmd/config_manager.py`: Multi-source configuration loading logic
- `src/aicmd/cache_manager.py`: Database interaction patterns and CacheEntry model
- `AGENTS.md`: Comprehensive development guidelines and workflow details

## Common Debugging Approaches

1. **Configuration Issues**: Use `aicmd --show-config` to see effective configuration and sources
2. **Cache Problems**: Check `aicmd --status` for database availability and confidence statistics
3. **API Issues**: Test with `--force-api` to bypass all caching layers
4. **Interactive Behavior**: Use `--disable-interactive` to isolate interaction-related issues