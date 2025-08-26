"""
AI Command Line Tool v0.4.0

A smart command-line tool that converts natural language prompts to shell commands
using OpenRouter API with intelligent caching and user interaction features.
"""

__version__ = "0.4.0"
__author__ = "Mikko"
__email__ = "Allen125423412@163.com"

from .ai import main, get_shell_command

__all__ = ["main", "get_shell_command"]
