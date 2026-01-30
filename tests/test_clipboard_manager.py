"""
Tests for ClipboardManager module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from aicmd.clipboard_manager import ClipboardManager


class TestClipboardManager:
    """Test suite for ClipboardManager"""
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger"""
        return Mock()
    
    @pytest.fixture
    def clipboard_manager(self, mock_logger):
        """Create a clipboard manager instance"""
        return ClipboardManager(logger=mock_logger)
    
    def test_initialization(self):
        """Test clipboard manager initialization"""
        manager = ClipboardManager()
        assert manager.logger is None
        
        mock_logger = Mock()
        manager_with_logger = ClipboardManager(logger=mock_logger)
        assert manager_with_logger.logger is mock_logger
    
    @patch('aicmd.clipboard_manager.pyperclip.copy')
    def test_copy_command_success(self, mock_copy, clipboard_manager):
        """Test successful command copy"""
        result = clipboard_manager.copy_command("echo hello")
        
        assert result is True
        mock_copy.assert_called_once_with("echo hello")
    
    @patch('aicmd.clipboard_manager.pyperclip.copy')
    def test_copy_command_with_no_clipboard_flag(self, mock_copy, clipboard_manager):
        """Test copy when no_clipboard flag is True"""
        result = clipboard_manager.copy_command("echo hello", no_clipboard=True)
        
        assert result is False
        mock_copy.assert_not_called()
    
    @patch('aicmd.clipboard_manager.pyperclip.copy')
    def test_copy_command_with_safety_disabled(self, mock_copy, clipboard_manager):
        """Test copy when safety info disables auto copy"""
        safety_info = {"disable_auto_copy": True}
        result = clipboard_manager.copy_command("rm -rf /", safety_info=safety_info)
        
        assert result is False
        mock_copy.assert_not_called()
    
    @patch('aicmd.clipboard_manager.pyperclip.copy')
    def test_copy_command_with_safe_command(self, mock_copy, clipboard_manager):
        """Test copy with safe command (safety info allows copy)"""
        safety_info = {"disable_auto_copy": False, "is_dangerous": False}
        result = clipboard_manager.copy_command("ls -la", safety_info=safety_info)
        
        assert result is True
        mock_copy.assert_called_once_with("ls -la")
    
    @patch('aicmd.clipboard_manager.pyperclip.copy')
    def test_copy_command_exception_handling(self, mock_copy, clipboard_manager):
        """Test copy command with pyperclip exception"""
        mock_copy.side_effect = Exception("Clipboard not available")
        
        result = clipboard_manager.copy_command("echo test")
        
        assert result is False
        clipboard_manager.logger.warning.assert_called_once()
        assert "Failed to copy to clipboard" in clipboard_manager.logger.warning.call_args[0][0]
    
    @patch('aicmd.clipboard_manager.pyperclip.copy')
    def test_copy_command_exception_without_logger(self, mock_copy):
        """Test copy command exception when no logger is set"""
        manager = ClipboardManager()
        mock_copy.side_effect = Exception("Clipboard error")
        
        # Should not raise exception even without logger
        result = manager.copy_command("echo test")
        assert result is False
    
    def test_should_show_safety_warning_with_disabled_copy(self, clipboard_manager):
        """Test safety warning detection when auto copy is disabled"""
        safety_info = {"disable_auto_copy": True, "is_dangerous": True}
        
        assert clipboard_manager.should_show_safety_warning(safety_info) is True
    
    def test_should_show_safety_warning_with_enabled_copy(self, clipboard_manager):
        """Test safety warning detection when auto copy is enabled"""
        safety_info = {"disable_auto_copy": False, "is_dangerous": False}
        
        assert clipboard_manager.should_show_safety_warning(safety_info) is False
    
    def test_should_show_safety_warning_with_none(self, clipboard_manager):
        """Test safety warning detection with None safety_info"""
        assert clipboard_manager.should_show_safety_warning(None) is False
    
    def test_should_show_safety_warning_with_empty_dict(self, clipboard_manager):
        """Test safety warning detection with empty safety_info"""
        assert clipboard_manager.should_show_safety_warning({}) is False
    
    @patch('aicmd.clipboard_manager.pyperclip.copy')
    def test_get_copy_status_message_success(self, mock_copy, clipboard_manager):
        """Test get_copy_status_message with successful copy"""
        copied, message = clipboard_manager.get_copy_status_message("echo hello")
        
        assert copied is True
        assert message is None
        mock_copy.assert_called_once()
    
    @patch('aicmd.clipboard_manager.pyperclip.copy')
    def test_get_copy_status_message_disabled_by_user(self, mock_copy, clipboard_manager):
        """Test get_copy_status_message when disabled by user"""
        copied, message = clipboard_manager.get_copy_status_message(
            "echo hello",
            no_clipboard=True
        )
        
        assert copied is False
        assert message is None
        mock_copy.assert_not_called()
    
    @patch('aicmd.clipboard_manager.pyperclip.copy')
    def test_get_copy_status_message_disabled_by_safety(self, mock_copy, clipboard_manager):
        """Test get_copy_status_message when disabled by safety"""
        safety_info = {"disable_auto_copy": True, "is_dangerous": True}
        copied, message = clipboard_manager.get_copy_status_message(
            "rm -rf /",
            safety_info=safety_info
        )
        
        assert copied is False
        assert message == "⚠️  Clipboard copying disabled for safety reasons"
        mock_copy.assert_not_called()
    
    @patch('aicmd.clipboard_manager.pyperclip.copy')
    def test_get_copy_status_message_with_exception(self, mock_copy, clipboard_manager):
        """Test get_copy_status_message when copy raises exception"""
        mock_copy.side_effect = Exception("Clipboard error")
        
        copied, message = clipboard_manager.get_copy_status_message("echo test")
        
        assert copied is False
        assert message is None
