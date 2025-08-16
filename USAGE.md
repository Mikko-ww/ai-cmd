# AI Command Line Tool - Detailed Usage Guide

This guide provides comprehensive information about using `ai-cmd` effectively, including advanced features, best practices, and optimization tips.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Configuration Deep Dive](#configuration-deep-dive)
3. [Advanced Usage Patterns](#advanced-usage-patterns)
4. [Caching System](#caching-system)
5. [Interactive Mode](#interactive-mode)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)
8. [Integration Examples](#integration-examples)

## Getting Started

### Installation Methods

#### Method 1: Development Installation
```bash
git clone https://github.com/Mikko-ww/ai-cmd.git
cd ai-cmd
uv sync
uv pip install -e .
```

#### Method 2: Direct Installation (when available)
```bash
pip install ai-cmd
```

### Initial Setup

1. **Obtain an OpenRouter API Key**
   - Visit [OpenRouter](https://openrouter.ai)
   - Create an account and generate an API key
   - Choose an appropriate model for your needs

2. **Configure Environment**
   ```bash
   # Create environment file
   cp .env.example .env
   
   # Edit .env file
   AI_CMD_OPENROUTER_API_KEY="your_api_key_here"
   AI_CMD_OPENROUTER_MODEL="google/gemma-3-27b-it:free"
   ```

3. **Test Installation**
   ```bash
   aicmd --version
   aicmd --config
   ```

## Configuration Deep Dive

### Configuration Hierarchy

`ai-cmd` uses a three-tier configuration system:

1. **Environment Variables** (highest priority)
2. **JSON Configuration Files**
3. **Default Values** (fallback)

### Environment Variables Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AI_CMD_OPENROUTER_API_KEY` | string | *required* | Your OpenRouter API key |
| `AI_CMD_OPENROUTER_MODEL` | string | `google/gemma-3-27b-it:free` | AI model to use |
| `AI_CMD_INTERACTIVE_MODE` | boolean | `false` | Enable interactive confirmation |
| `AI_CMD_CACHE_ENABLED` | boolean | `true` | Enable command caching |
| `AI_CMD_AUTO_COPY_THRESHOLD` | float | `0.9` | Auto-copy confidence threshold |
| `AI_CMD_CONFIDENCE_THRESHOLD` | float | `0.8` | Manual confirmation threshold |
| `AI_CMD_SIMILARITY_THRESHOLD` | float | `0.7` | Query similarity threshold |
| `AI_CMD_POSITIVE_WEIGHT` | float | `0.2` | Positive feedback weight |
| `AI_CMD_NEGATIVE_WEIGHT` | float | `0.6` | Negative feedback weight |
| `AI_CMD_CACHE_SIZE_LIMIT` | integer | `1000` | Maximum cache entries |
| `AI_CMD_CACHE_DIR` | string | `~/.ai-cmd` | Cache directory path |

### JSON Configuration

#### Creating Configuration Files

```bash
# Create user configuration
aicmd --create-config

# This creates ~/.ai-cmd/settings.json
```

#### Configuration File Structure

```json
{
  "version": "0.2.2",
  "description": "AI Command Line Tool Configuration",
  "basic": {
    "interactive_mode": false,
    "cache_enabled": true,
    "auto_copy_threshold": 0.9,
    "manual_confirmation_threshold": 0.8
  },
  "api": {
    "timeout_seconds": 30,
    "max_retries": 3
  },
  "cache": {
    "cache_directory": "~/.ai-cmd",
    "database_file": "cache.db",
    "max_cache_age_days": 30,
    "cache_size_limit": 1000
  },
  "interaction": {
    "interaction_timeout_seconds": 10,
    "positive_weight": 0.2,
    "negative_weight": 0.6,
    "similarity_threshold": 0.7,
    "confidence_threshold": 0.8
  },
  "display": {
    "show_confidence": false,
    "show_source": false,
    "colored_output": true
  }
}
```

#### Project-Specific Configuration

Create `.ai-cmd.json` in your project root:

```json
{
  "basic": {
    "interactive_mode": true,
    "auto_copy_threshold": 0.95
  },
  "api": {
    "model": "anthropic/claude-3-sonnet:beta"
  }
}
```

### Configuration Management Commands

```bash
# View current configuration
aicmd --config

# View detailed configuration with sources
aicmd --show-config

# Validate configuration
aicmd --validate-config

# Create user configuration file
aicmd --create-config
```

## Advanced Usage Patterns

### Basic Command Generation

```bash
# Simple command generation
aicmd "list files"
aicmd "check disk space"
aicmd "find large files over 100MB"

# Complex operations
aicmd "create a backup of all .py files to backup folder"
aicmd "find all git repositories in home directory"
aicmd "show network connections on port 80"
```

### Bypassing Cache

```bash
# Force fresh API call
aicmd "update system packages" --force-api

# Useful for commands that change over time
aicmd "show current weather" --force-api
```

### Non-Interactive Mode

```bash
# Disable interactive prompts (useful for scripts)
aicmd "list directory contents" --disable-interactive

# Perfect for automation
for query in "check memory" "check cpu" "check disk"; do
    aicmd "$query" --disable-interactive
done
```

### Combining Options

```bash
# Force API and disable interaction
aicmd "complex system diagnosis" --force-api --disable-interactive

# Multiple queries with fresh results
aicmd "show current time" --force-api --disable-interactive
```

## Caching System

### How Caching Works

The caching system uses a SQLite database to store:
- Query text and generated commands
- Confidence scores
- User feedback (confirmations/rejections)
- Usage timestamps
- Similarity mappings

### Cache Behavior by Confidence Level

| Confidence Level | Behavior |
|-----------------|----------|
| ≥ 0.9 (High) | Auto-copy to clipboard, no confirmation needed |
| 0.8-0.9 (Medium) | Show command, ask for confirmation in interactive mode |
| < 0.8 (Low) | Always require confirmation or force API call |

### Cache Management

```bash
# View cache statistics
aicmd --status

# Reset error states (affects cache behavior)
aicmd --reset-errors

# Configuration for cache tuning
export AI_CMD_CACHE_SIZE_LIMIT=500
export AI_CMD_MAX_CACHE_AGE_DAYS=7
```

### Cache Location and Structure

- **Default location**: `~/.ai-cmd/cache.db`
- **Database tables**: queries, interactions, confidence_scores
- **Automatic cleanup**: Entries older than `max_cache_age_days`

## Interactive Mode

### Enabling Interactive Mode

```bash
# Via environment variable
export AI_CMD_INTERACTIVE_MODE=true

# Via configuration file
{
  "basic": {
    "interactive_mode": true
  }
}
```

### Interactive Flow

1. **Query Processing**: User provides natural language input
2. **Cache Check**: System checks for similar cached commands
3. **Confidence Evaluation**: Calculates confidence based on history
4. **User Interaction**: 
   - High confidence: Auto-execute
   - Medium confidence: Show and ask for confirmation
   - Low confidence: Require explicit confirmation
5. **Feedback Collection**: User can confirm/reject for future learning

### Interactive Prompts

```
Generated command: ls -la
Confidence: 0.85
Source: Cache (Medium Confidence)

Execute this command? [y/N/e/q]: 
  y - Yes, execute and copy to clipboard
  N - No, reject this suggestion
  e - Edit command before copying
  q - Quit without action
```

### Feedback System

User feedback improves future suggestions:
- **Positive feedback**: Increases confidence for similar queries
- **Negative feedback**: Decreases confidence, improves alternatives
- **Edit feedback**: Learns from user corrections

## Troubleshooting

### Common Issues

#### 1. API Key Not Found
```
Error: AI_CMD_OPENROUTER_API_KEY not found in .env file.
```

**Solution**:
```bash
# Check if .env file exists
ls -la .env

# Verify API key is set
grep AI_CMD_OPENROUTER_API_KEY .env

# Create or update .env file
echo 'AI_CMD_OPENROUTER_API_KEY="your_key_here"' >> .env
```

#### 2. Permission Errors

```
Error: Permission denied when accessing cache directory
```

**Solution**:
```bash
# Check cache directory permissions
ls -la ~/.ai-cmd/

# Fix permissions
chmod 755 ~/.ai-cmd/
chmod 644 ~/.ai-cmd/*.db
```

#### 3. Configuration Validation Errors

```bash
# Diagnose configuration issues
aicmd --validate-config

# View detailed configuration
aicmd --show-config
```

#### 4. Network/API Issues

```bash
# Reset error state
aicmd --reset-errors

# Check system status
aicmd --status
```

### Debug Mode

Enable detailed logging by setting:

```bash
export AI_CMD_DEBUG=true
aicmd "your query"
```

### Health Checks

```bash
# System health overview
aicmd --status

# Configuration validation
aicmd --validate-config

# Test basic functionality
aicmd "echo test" --disable-interactive
```

## Best Practices

### Security Considerations

1. **API Key Management**
   - Never commit `.env` files to version control
   - Use environment variables in production
   - Rotate API keys regularly

2. **Command Validation**
   - Always review generated commands before execution
   - Use interactive mode for sensitive operations
   - Be cautious with `--disable-interactive` in automated scripts

3. **Cache Security**
   - Cache files may contain sensitive command history
   - Regularly clean cache in shared environments
   - Consider disabling cache for sensitive queries

### Performance Optimization

1. **Cache Tuning**
   ```bash
   # Increase cache size for heavy users
   export AI_CMD_CACHE_SIZE_LIMIT=2000
   
   # Adjust cache age based on usage patterns
   export AI_CMD_MAX_CACHE_AGE_DAYS=60
   ```

2. **Model Selection**
   ```bash
   # Faster, less accurate
   export AI_CMD_OPENROUTER_MODEL="google/gemma-3-7b-it:free"
   
   # Slower, more accurate
   export AI_CMD_OPENROUTER_MODEL="anthropic/claude-3-sonnet:beta"
   ```

3. **Confidence Thresholds**
   ```bash
   # More aggressive caching (less API calls)
   export AI_CMD_AUTO_COPY_THRESHOLD=0.8
   
   # More conservative (more confirmations)
   export AI_CMD_AUTO_COPY_THRESHOLD=0.95
   ```

### Usage Patterns

1. **Daily Operations**
   ```bash
   # Enable interactive mode for safety
   export AI_CMD_INTERACTIVE_MODE=true
   
   # Use descriptive queries
   aicmd "safely remove all .tmp files from current directory"
   ```

2. **Automation Scripts**
   ```bash
   # Disable interactive mode
   # Use specific, tested queries
   aicmd "list process using port 8080" --disable-interactive
   ```

3. **Learning and Exploration**
   ```bash
   # Use --force-api for varied responses
   aicmd "different ways to monitor system performance" --force-api
   ```

## Integration Examples

### Shell Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
# Quick aliases
alias ai="aicmd"
alias aii="aicmd --disable-interactive"
alias aif="aicmd --force-api"

# Function for immediate execution
airun() {
    local cmd=$(aicmd "$*" --disable-interactive)
    echo "Generated: $cmd"
    read -p "Execute? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        eval "$cmd"
    fi
}
```

### Git Hooks

Pre-commit hook example:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Use ai-cmd to suggest commit message improvements
if [ -f .git/COMMIT_EDITMSG ]; then
    msg=$(cat .git/COMMIT_EDITMSG)
    suggestion=$(aicmd "improve this git commit message: $msg" --disable-interactive)
    echo "Suggested commit message improvement: $suggestion"
fi
```

### IDE Integration

VS Code task example (`.vscode/tasks.json`):

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "AI Command",
            "type": "shell",
            "command": "aicmd",
            "args": ["${input:prompt}"],
            "group": "build"
        }
    ],
    "inputs": [
        {
            "id": "prompt",
            "description": "Enter your command prompt",
            "default": "",
            "type": "promptString"
        }
    ]
}
```

### Scripting Integration

Python integration example:

```python
import subprocess
import json

def get_shell_command(prompt):
    """Get shell command using ai-cmd"""
    result = subprocess.run(
        ['aicmd', prompt, '--disable-interactive'],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

# Usage
cmd = get_shell_command("find all python files modified today")
print(f"Generated command: {cmd}")
```

### Monitoring and Logging

System monitoring script:

```bash
#!/bin/bash
# ai-monitoring.sh

log_file="/var/log/ai-cmd-usage.log"

# Function to log ai-cmd usage
log_usage() {
    local query="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] Query: $query" >> "$log_file"
    
    # Generate and log command
    local cmd=$(aicmd "$query" --disable-interactive)
    echo "[$timestamp] Generated: $cmd" >> "$log_file"
    
    return 0
}

# Example usage
log_usage "check system memory usage"
log_usage "find largest files in /var/log"
```

---

This guide covers the comprehensive usage of `ai-cmd`. For additional support, please visit our [GitHub repository](https://github.com/Mikko-ww/ai-cmd) or open an issue for specific questions.
