"""
Interactive Manager 测试
测试用户交互逻辑，包括输入处理、超时、颜色输出等
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from aicmd.interactive_manager import (
    InteractiveManager,
    ConfirmationResult,
    create_simple_prompt_function,
)
from aicmd.cross_platform_input import InputTimeoutError


@pytest.fixture
def mock_config_manager():
    """Mock 配置管理器"""
    config = Mock()
    config.get.side_effect = lambda key, default=None: {
        "interaction_timeout_seconds": 30,
        "auto_confirm_on_timeout": True,
        "show_detailed_info": True,
        "colored_output": True,
        "interactive_mode": False,
        "confidence_threshold": 0.8,
        "auto_copy_threshold": 0.9,
        "manual_confirmation_threshold": 0.8,
    }.get(key, default)
    return config


@pytest.fixture
def interactive_manager(mock_config_manager):
    """创建 InteractiveManager 实例"""
    return InteractiveManager(
        config_manager=mock_config_manager,
        no_color=False
    )


@pytest.fixture
def interactive_manager_no_color(mock_config_manager):
    """创建禁用颜色的 InteractiveManager 实例"""
    return InteractiveManager(
        config_manager=mock_config_manager,
        no_color=True
    )


class TestInteractiveManagerInit:
    """测试 InteractiveManager 初始化"""

    def test_init_with_defaults(self):
        """测试使用默认配置初始化"""
        manager = InteractiveManager()
        
        assert manager.config is not None
        assert manager.degradation_manager is not None
        assert manager.default_timeout == 30
        assert manager.auto_confirm_on_timeout is True

    def test_init_with_custom_config(self, mock_config_manager):
        """测试使用自定义配置初始化"""
        manager = InteractiveManager(config_manager=mock_config_manager)
        
        assert manager.default_timeout == 30
        assert manager.show_detailed_info is True

    def test_init_no_color_parameter(self, mock_config_manager):
        """测试 no_color 参数"""
        manager_color = InteractiveManager(
            config_manager=mock_config_manager,
            no_color=False
        )
        manager_no_color = InteractiveManager(
            config_manager=mock_config_manager,
            no_color=True
        )
        
        # no_color=True 应该禁用颜色
        assert manager_no_color.use_colors is False
        # no_color=False 且配置允许时应该启用颜色（取决于终端支持）
        # 注意：在测试环境中可能因为终端不支持而返回 False

    def test_interaction_stats_initialized(self, interactive_manager):
        """测试交互统计初始化"""
        stats = interactive_manager.interaction_stats
        
        assert stats["total_prompts"] == 0
        assert stats["confirmed"] == 0
        assert stats["rejected"] == 0
        assert stats["timeouts"] == 0
        assert stats["cancelled"] == 0
        assert stats["errors"] == 0


class TestInteractiveManagerColorization:
    """测试颜色输出"""

    def test_colorize_with_colors_enabled(self, interactive_manager):
        """测试启用颜色时的着色"""
        # 强制启用颜色用于测试
        interactive_manager.use_colors = True
        
        colored_text = interactive_manager._colorize("test", "green")
        
        # 应该包含 ANSI 颜色代码
        assert "\033[" in colored_text
        assert "test" in colored_text

    def test_colorize_with_colors_disabled(self, interactive_manager_no_color):
        """测试禁用颜色时的着色"""
        colored_text = interactive_manager_no_color._colorize("test", "red")
        
        # 不应该包含 ANSI 颜色代码
        assert "\033[" not in colored_text
        assert colored_text == "test"

    def test_colorize_invalid_color(self, interactive_manager):
        """测试无效颜色名称"""
        interactive_manager.use_colors = True
        colored_text = interactive_manager._colorize("test", "invalid_color")
        
        # 应该返回文本加 reset 代码
        assert "test" in colored_text


class TestInteractiveManagerConfirmation:
    """测试用户确认功能"""

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_prompt_user_confirmation_yes(self, mock_input, interactive_manager):
        """测试用户确认（Yes）"""
        mock_input.return_value = "y"
        
        result, details = interactive_manager.prompt_user_confirmation(
            command="ls -la",
            source="API",
            confidence=0.85
        )
        
        assert result == ConfirmationResult.CONFIRMED
        assert details["command"] == "ls -la"
        assert details["source"] == "API"
        assert details["confidence"] == 0.85
        
        # 验证统计
        assert interactive_manager.interaction_stats["total_prompts"] == 1
        assert interactive_manager.interaction_stats["confirmed"] == 1

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_prompt_user_confirmation_no(self, mock_input, interactive_manager):
        """测试用户拒绝（No）"""
        mock_input.return_value = "n"
        
        result, details = interactive_manager.prompt_user_confirmation(
            command="rm -rf /",
            source="API"
        )
        
        assert result == ConfirmationResult.REJECTED
        
        # 验证统计
        assert interactive_manager.interaction_stats["rejected"] == 1

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_prompt_user_confirmation_enter(self, mock_input, interactive_manager):
        """测试用户按回车（默认 Yes）"""
        mock_input.return_value = ""
        
        result, details = interactive_manager.prompt_user_confirmation(
            command="pwd",
            source="Cache"
        )
        
        assert result == ConfirmationResult.CONFIRMED

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_prompt_user_confirmation_timeout(self, mock_input, interactive_manager):
        """测试超时处理"""
        mock_input.side_effect = InputTimeoutError()
        
        result, details = interactive_manager.prompt_user_confirmation(
            command="echo hello",
            source="API",
            timeout=5
        )
        
        # 默认超时自动确认
        assert result == ConfirmationResult.TIMEOUT
        assert interactive_manager.interaction_stats.get("timeout", 0) >= 1

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_prompt_user_confirmation_timeout_no_auto_confirm(self, mock_input, mock_config_manager):
        """测试超时不自动确认"""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "auto_confirm_on_timeout": False,
            "interaction_timeout_seconds": 30,
        }.get(key, default)
        
        manager = InteractiveManager(config_manager=mock_config_manager)
        mock_input.side_effect = InputTimeoutError()
        
        result, details = manager.prompt_user_confirmation(
            command="echo hello",
            source="API"
        )
        
        # 超时应该取消
        assert result == ConfirmationResult.CANCELLED

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_prompt_user_confirmation_ctrl_c(self, mock_input, interactive_manager):
        """测试 Ctrl+C 中断"""
        mock_input.side_effect = KeyboardInterrupt()
        
        result, details = interactive_manager.prompt_user_confirmation(
            command="ls",
            source="API"
        )
        
        assert result == ConfirmationResult.CANCELLED
        assert interactive_manager.interaction_stats["cancelled"] == 1

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_prompt_user_confirmation_eof(self, mock_input, interactive_manager):
        """测试 EOF (Ctrl+D)"""
        mock_input.side_effect = EOFError()
        
        result, details = interactive_manager.prompt_user_confirmation(
            command="ls",
            source="API"
        )
        
        assert result == ConfirmationResult.CANCELLED

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_prompt_user_confirmation_various_yes_responses(self, mock_input, interactive_manager):
        """测试各种 Yes 响应"""
        yes_responses = ["y", "yes", "Y", "YES", "是", "好", "确认"]
        
        for response in yes_responses:
            mock_input.return_value = response
            result, _ = interactive_manager.prompt_user_confirmation("ls", "API")
            assert result == ConfirmationResult.CONFIRMED, f"Failed for: {response}"

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_prompt_user_confirmation_various_no_responses(self, mock_input, interactive_manager):
        """测试各种 No 响应"""
        no_responses = ["n", "no", "N", "NO", "否", "不", "cancel"]
        
        for response in no_responses:
            mock_input.return_value = response
            result, _ = interactive_manager.prompt_user_confirmation("ls", "API")
            assert result == ConfirmationResult.REJECTED, f"Failed for: {response}"

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_prompt_user_confirmation_unrecognized_response(self, mock_input, interactive_manager):
        """测试无法识别的响应（默认为 Yes）"""
        mock_input.return_value = "maybe"
        
        result, _ = interactive_manager.prompt_user_confirmation("ls", "API")
        
        # 无法识别的响应应该默认确认
        assert result == ConfirmationResult.CONFIRMED


class TestInteractiveManagerDisplay:
    """测试显示功能"""

    def test_display_info(self, interactive_manager, capsys):
        """测试显示信息"""
        interactive_manager.display_info("Test message", "blue")
        
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_display_metrics(self, interactive_manager, capsys):
        """测试显示指标"""
        interactive_manager.display_metrics(confidence=0.85, similarity=0.75)
        
        captured = capsys.readouterr()
        assert "Confidence" in captured.out
        assert "Similarity" in captured.out
        assert "85" in captured.out
        assert "75" in captured.out

    def test_display_metrics_none_values(self, interactive_manager, capsys):
        """测试显示空指标"""
        interactive_manager.display_metrics(confidence=None, similarity=None)
        
        captured = capsys.readouterr()
        # 不应该有输出
        assert captured.out == ""

    def test_display_success_message(self, interactive_manager, capsys):
        """测试显示成功消息"""
        interactive_manager.display_success_message("ls -la", copied=True)
        
        captured = capsys.readouterr()
        assert "Copied to clipboard" in captured.out or "✓" in captured.out

    def test_display_rejection_message(self, interactive_manager, capsys):
        """测试显示拒绝消息"""
        interactive_manager.display_rejection_message()
        
        captured = capsys.readouterr()
        assert "Not copied" in captured.out or "✗" in captured.out


class TestInteractiveManagerQuickConfirm:
    """测试快速确认功能"""

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_quick_confirm_yes(self, mock_input, interactive_manager):
        """测试快速确认 Yes"""
        mock_input.return_value = "y"
        
        result = interactive_manager.quick_confirm("Delete file?", default=True)
        
        assert result is True

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_quick_confirm_no(self, mock_input, interactive_manager):
        """测试快速确认 No"""
        mock_input.return_value = "n"
        
        result = interactive_manager.quick_confirm("Delete file?", default=True)
        
        assert result is False

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_quick_confirm_default_true(self, mock_input, interactive_manager):
        """测试快速确认默认 True"""
        mock_input.return_value = ""  # 空响应
        
        result = interactive_manager.quick_confirm("Delete file?", default=True)
        
        assert result is True

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_quick_confirm_default_false(self, mock_input, interactive_manager):
        """测试快速确认默认 False"""
        mock_input.return_value = ""  # 空响应
        
        result = interactive_manager.quick_confirm("Delete file?", default=False)
        
        assert result is False

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_quick_confirm_timeout(self, mock_input, interactive_manager):
        """测试快速确认超时使用默认值"""
        mock_input.side_effect = InputTimeoutError()
        
        result = interactive_manager.quick_confirm("Delete file?", default=True, timeout=5)
        
        assert result is True  # 应该使用默认值


class TestInteractiveManagerStats:
    """测试统计功能"""

    def test_get_interaction_stats_empty(self, interactive_manager):
        """测试获取空统计"""
        stats = interactive_manager.get_interaction_stats()
        
        assert "message" in stats
        assert stats["message"] == "No interactions yet"

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_get_interaction_stats_with_data(self, mock_input, interactive_manager):
        """测试获取有数据的统计"""
        # 模拟一些交互
        mock_input.return_value = "y"
        interactive_manager.prompt_user_confirmation("ls", "API")
        
        mock_input.return_value = "n"
        interactive_manager.prompt_user_confirmation("rm", "API")
        
        stats = interactive_manager.get_interaction_stats()
        
        assert stats["total_prompts"] == 2
        assert stats["confirmed"] == 1
        assert stats["rejected"] == 1
        assert "confirmed_percentage" in stats
        assert "rejected_percentage" in stats

    def test_reset_stats(self, interactive_manager):
        """测试重置统计"""
        # 设置一些统计数据
        interactive_manager.interaction_stats["total_prompts"] = 10
        interactive_manager.interaction_stats["confirmed"] = 5
        
        # 重置
        interactive_manager.reset_stats()
        
        # 验证已重置
        assert interactive_manager.interaction_stats["total_prompts"] == 0
        assert interactive_manager.interaction_stats["confirmed"] == 0


class TestInteractiveManagerConfiguration:
    """测试配置相关功能"""

    def test_is_interactive_mode_enabled_true(self, mock_config_manager):
        """测试交互模式启用"""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "interactive_mode": True
        }.get(key, default)
        
        manager = InteractiveManager(config_manager=mock_config_manager)
        
        assert manager.is_interactive_mode_enabled() is True

    def test_is_interactive_mode_enabled_false(self, mock_config_manager):
        """测试交互模式禁用"""
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "interactive_mode": False
        }.get(key, default)
        
        manager = InteractiveManager(config_manager=mock_config_manager)
        
        assert manager.is_interactive_mode_enabled() is False

    def test_should_prompt_for_confirmation_high_confidence(self, interactive_manager):
        """测试高置信度不需要确认"""
        # 置信度 >= auto_copy_threshold (0.9)
        should_prompt = interactive_manager.should_prompt_for_confirmation(0.95)
        
        assert should_prompt is False

    def test_should_prompt_for_confirmation_medium_confidence(self, interactive_manager):
        """测试中等置信度需要确认"""
        # 置信度介于 manual_confirmation_threshold 和 auto_copy_threshold 之间
        should_prompt = interactive_manager.should_prompt_for_confirmation(0.85)
        
        assert should_prompt is True

    def test_should_prompt_for_confirmation_low_confidence(self, interactive_manager):
        """测试低置信度需要确认"""
        should_prompt = interactive_manager.should_prompt_for_confirmation(0.5)
        
        assert should_prompt is True

    def test_should_prompt_for_confirmation_very_low_confidence(self, interactive_manager):
        """测试非常低的置信度需要确认"""
        should_prompt = interactive_manager.should_prompt_for_confirmation(0.3)
        
        assert should_prompt is True


class TestInteractiveManagerHelpers:
    """测试辅助功能"""

    def test_show_help(self, interactive_manager, capsys):
        """测试显示帮助"""
        interactive_manager.show_help()
        
        captured = capsys.readouterr()
        assert "Interactive Mode Help" in captured.out or "Y/yes" in captured.out

    def test_supports_color_in_tty(self, interactive_manager):
        """测试 TTY 环境下颜色支持检测"""
        # 这个测试结果取决于运行环境
        result = interactive_manager._supports_color()
        
        assert isinstance(result, bool)


class TestCreateSimplePromptFunction:
    """测试简化提示函数创建"""

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_simple_prompt_function_confirmed(self, mock_input, mock_config_manager):
        """测试简化提示函数返回确认"""
        mock_input.return_value = "y"
        
        prompt_func = create_simple_prompt_function(mock_config_manager)
        result = prompt_func("ls -la", "API", timeout=30)
        
        assert result is True

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_simple_prompt_function_rejected(self, mock_input, mock_config_manager):
        """测试简化提示函数返回拒绝"""
        mock_input.return_value = "n"
        
        prompt_func = create_simple_prompt_function(mock_config_manager)
        result = prompt_func("rm -rf /", "API", timeout=30)
        
        assert result is False

    @patch("aicmd.interactive_manager.universal_input.input_with_timeout")
    def test_simple_prompt_function_timeout(self, mock_input, mock_config_manager):
        """测试简化提示函数超时视为确认"""
        mock_input.side_effect = InputTimeoutError()
        
        prompt_func = create_simple_prompt_function(mock_config_manager)
        result = prompt_func("ls", "API", timeout=30)
        
        # 超时应该视为确认
        assert result is True
