# AI Command Line Tool

`ai-cmd` is an intelligent command-line tool that converts natural language prompts into shell commands using the OpenRouter API. With advanced caching, user interaction features, and flexible configuration options, it's designed to boost your productivity while maintaining safety and reliability.

## ✨ Features

- 🧠 **AI-Powered Command Generation**: Convert natural language to shell commands using state-of-the-art AI models
- 🚀 **Smart Caching System**: Intelligent command caching with confidence-based decisions  
- 🔄 **Interactive Mode**: User confirmation system for enhanced safety
- ⚙️ **Flexible Configuration**: Multi-layer configuration with JSON files and environment variables
- 📊 **Statistics & Analytics**: Detailed usage statistics and performance metrics
- 🛡️ **Error Resilience**: Graceful degradation and error recovery mechanisms
- 📋 **Auto-Clipboard**: Automatic clipboard integration for seamless workflow

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Mikko-ww/ai-cmd.git
cd ai-cmd

# Install dependencies (requires uv)
uv sync

# Install the tool
uv pip install -e .
```

### Configuration

1. **Set up your API key:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenRouter API key
   ```

2. **Create user configuration (optional):**
   ```bash
   aicmd --create-config
   ```

### Basic Usage

```bash
# Generate a command
aicmd "list all files in current directory"

# Force API call (bypass cache)
aicmd "create new directory" --force-api

# Disable interactive mode for automation
aicmd "check disk usage" --disable-interactive
```

## 📖 Documentation

### Command Line Options

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and exit |
| `-v, --version` | Show version information |
| `--config` | Show current configuration |
| `--show-config` | Show detailed configuration summary |
| `--create-config` | Create user configuration file |
| `--validate-config` | Validate current configuration |
| `--force-api` | Force API call, bypass cache |
| `--disable-interactive` | Disable interactive mode |
| `--stats` | Show cache and interaction statistics |
| `--reset-errors` | Reset error state |

### Configuration System

`ai-cmd` supports multi-layer configuration with the following priority order:

1. **Environment Variables** (highest priority)
2. **JSON Configuration Files**
3. **Default Values** (fallback)

#### Configuration File Locations

- User config: `~/.ai-cmd/settings.json`
- Project config: `.ai-cmd.json` (in current directory)

#### Configuration Options

```json
{
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
    "database_file": "ai_cmd_cache.db",
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

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_CMD_OPENROUTER_API_KEY` | OpenRouter API key | Required |
| `AI_CMD_OPENROUTER_MODEL` | AI model to use | `google/gemma-3-27b-it:free` |
| `AI_CMD_INTERACTIVE_MODE` | Enable interactive mode | `false` |
| `AI_CMD_CACHE_ENABLED` | Enable caching | `true` |
| `AI_CMD_AUTO_COPY_THRESHOLD` | Auto-copy confidence threshold | `0.9` |
| `AI_CMD_CONFIDENCE_THRESHOLD` | Manual confirmation threshold | `0.8` |

## 🔧 Advanced Features

### Smart Caching

The tool maintains a local cache of command translations with confidence scoring:

- **High Confidence (≥0.9)**: Commands are automatically copied to clipboard
- **Medium Confidence (0.8-0.9)**: User confirmation required in interactive mode
- **Low Confidence (<0.8)**: Always requires confirmation or API call

### Interactive Mode

When enabled, interactive mode provides:
- User confirmation for generated commands
- Feedback collection to improve future suggestions
- Safety prompts for potentially dangerous operations

### Statistics and Monitoring

```bash
# View detailed statistics
aicmd --stats

# View configuration status
aicmd --show-config

# Validate configuration
aicmd --validate-config
```

## 🛠️ Development

### Requirements

- Python 3.9+
- [uv](https://docs.astral.sh/uv/) for package management

### Setup

```bash
# Install development dependencies
uv sync

# Run linting
uv run black src/
uv run flake8 src/

# Run tests
uv run python -m pytest
```

### Project Structure

```
ai-cmd/
├── src/aicmd/           # Main package
│   ├── ai.py           # Core functionality
│   ├── config_manager.py    # Configuration management
│   ├── cache_manager.py     # Caching system
│   ├── interactive_manager.py  # User interaction
│   └── ...
├── config_template.json     # Configuration template
├── pyproject.toml          # Project configuration
└── README.md              # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `uv run python -m pytest`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenRouter for providing AI model access
- The open-source community for inspiration and tools

## 🔗 Links

- **GitHub**: [https://github.com/Mikko-ww/ai-cmd](https://github.com/Mikko-ww/ai-cmd)
- **Issues**: [https://github.com/Mikko-ww/ai-cmd/issues](https://github.com/Mikko-ww/ai-cmd/issues)
- **Documentation**: [README.md](README.md)
