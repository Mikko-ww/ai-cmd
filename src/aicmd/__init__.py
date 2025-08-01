"""
AI Command Line Tool v0.2.0

A smart command-line tool that converts natural language prompts to shell commands
using OpenRouter API with intelligent caching and user interaction features.
"""

__version__ = "0.2.0"
__author__ = "AI-CMD Team"
__email__ = "support@ai-cmd.dev"

from .ai import main, get_shell_command

__all__ = ["main", "get_shell_command"]
