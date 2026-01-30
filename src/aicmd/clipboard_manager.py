"""
Clipboard Manager Module

Handles all clipboard operations with safety checks and error handling.
"""

import pyperclip
from typing import Optional


class ClipboardManager:
    """
    Manages clipboard operations with integrated safety checks.
    
    Centralizes all clipboard copy logic that was previously scattered
    throughout ai.py.
    """
    
    def __init__(self, logger=None):
        """
        Initialize clipboard manager.
        
        Args:
            logger: Optional logger instance for error reporting
        """
        self.logger = logger
    
    def copy_command(
        self,
        command: str,
        no_clipboard: bool = False,
        safety_info: Optional[dict] = None
    ) -> bool:
        """
        Copy command to clipboard with safety checks.
        
        Args:
            command: The command to copy
            no_clipboard: Whether clipboard copying is disabled by user
            safety_info: Safety information dict with 'disable_auto_copy' flag
            
        Returns:
            bool: True if copied successfully, False otherwise
        """
        # Check if clipboard is disabled by user
        if no_clipboard:
            return False
        
        # Check if clipboard is disabled for safety reasons
        if safety_info and safety_info.get("disable_auto_copy", False):
            return False
        
        # Try to copy to clipboard
        try:
            pyperclip.copy(command)
            return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to copy to clipboard: {e}")
            return False
    
    def should_show_safety_warning(self, safety_info: Optional[dict]) -> bool:
        """
        Check if safety warning about disabled clipboard should be shown.
        
        Args:
            safety_info: Safety information dict
            
        Returns:
            bool: True if warning should be shown
        """
        return (
            safety_info is not None
            and safety_info.get("disable_auto_copy", False)
        )
    
    def get_copy_status_message(
        self,
        command: str,
        no_clipboard: bool = False,
        safety_info: Optional[dict] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Determine copy status and get appropriate message.
        
        Args:
            command: The command to copy
            no_clipboard: Whether clipboard is disabled by user
            safety_info: Safety information dict
            
        Returns:
            tuple: (was_copied: bool, message: Optional[str])
        """
        copied = self.copy_command(command, no_clipboard, safety_info)
        
        if copied:
            return True, None
        elif self.should_show_safety_warning(safety_info):
            return False, "⚠️  Clipboard copying disabled for safety reasons"
        else:
            return False, None
