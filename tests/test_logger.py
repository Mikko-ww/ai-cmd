"""
Logger 单元测试
测试增强的日志功能
"""

import pytest
import os
import tempfile
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestColoredFormatter:
    """ColoredFormatter 测试类"""

    def test_colored_formatter_with_color(self):
        """测试带颜色的格式化"""
        from aicmd.logger import ColoredFormatter
        
        formatter = ColoredFormatter(use_color=True, fmt='%(levelname)s - %(message)s')
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # 格式化后应该正常工作
        formatted = formatter.format(record)
        assert "Test message" in formatted

    def test_colored_formatter_without_color(self):
        """测试不带颜色的格式化"""
        from aicmd.logger import ColoredFormatter
        
        formatter = ColoredFormatter(use_color=False, fmt='%(levelname)s - %(message)s')
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "INFO" in formatted
        assert "Test message" in formatted


class TestJSONFormatter:
    """JSONFormatter 测试类"""

    def test_json_formatter_basic(self):
        """测试基本 JSON 格式化"""
        from aicmd.logger import JSONFormatter
        import json
        
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.funcName = "test_func"
        record.module = "test_module"
        
        formatted = formatter.format(record)
        
        # 应该是有效的 JSON
        data = json.loads(formatted)
        
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["module"] == "test_module"

    def test_json_formatter_with_extra(self):
        """测试带额外字段的 JSON 格式化"""
        from aicmd.logger import JSONFormatter
        import json
        
        formatter = JSONFormatter(include_extra=True)
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.custom_field = "custom_value"
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert "extra" in data
        assert data["extra"]["custom_field"] == "custom_value"


class TestAICommandLogger:
    """AICommandLogger 测试类"""

    def test_logger_initialization(self, temp_dir):
        """测试日志器初始化"""
        from aicmd.logger import AICommandLogger
        
        log_dir = temp_dir / "logs"
        logger = AICommandLogger(log_dir=str(log_dir))
        
        assert log_dir.exists()
        assert len(logger.logger.handlers) >= 2  # 控制台和文件

    def test_logger_methods(self, temp_dir):
        """测试日志方法"""
        from aicmd.logger import AICommandLogger
        
        log_dir = temp_dir / "logs"
        logger = AICommandLogger(log_dir=str(log_dir))
        
        # 所有方法都应该能正常工作
        logger.info("Info message")
        logger.success("Success message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.debug("Debug message")
        logger.critical("Critical message")

    def test_logger_set_level(self, temp_dir):
        """测试设置日志级别"""
        from aicmd.logger import AICommandLogger
        
        log_dir = temp_dir / "logs"
        logger = AICommandLogger(log_dir=str(log_dir))
        
        # 设置日志级别
        logger.set_level(console_level="DEBUG", file_level="WARNING")
        
        # 验证级别已更改
        assert logger.logger.handlers[0].level == logging.DEBUG
        assert logger.logger.handlers[1].level == logging.WARNING

    def test_logger_get_log_info(self, temp_dir):
        """测试获取日志信息"""
        from aicmd.logger import AICommandLogger
        
        log_dir = temp_dir / "logs"
        logger = AICommandLogger(log_dir=str(log_dir))
        
        info = logger.get_log_info()
        
        assert "log_dir" in info
        assert "log_file" in info
        assert "handlers" in info
        assert "max_bytes" in info
        assert "backup_count" in info

    def test_logger_request_context(self, temp_dir):
        """测试请求上下文"""
        from aicmd.logger import AICommandLogger
        
        log_dir = temp_dir / "logs"
        logger = AICommandLogger(log_dir=str(log_dir))
        
        # 使用请求上下文
        with logger.request_context() as request_id:
            assert request_id is not None
            assert len(request_id) == 8
            assert AICommandLogger._current_request_id == request_id
        
        # 上下文结束后应该清除
        assert AICommandLogger._current_request_id is None

    def test_logger_metrics(self, temp_dir):
        """测试性能指标"""
        from aicmd.logger import AICommandLogger
        
        log_dir = temp_dir / "logs"
        logger = AICommandLogger(log_dir=str(log_dir))
        
        # 记录一些操作
        logger.log_api_call(
            provider="openai",
            model="gpt-4",
            query="test query",
            response_time_ms=100.5,
            success=True
        )
        
        logger.log_cache_operation("hit", "hash123")
        logger.log_cache_operation("miss", "hash456")
        
        # 获取指标
        metrics = logger.get_metrics()
        
        assert metrics["api_calls"] == 1
        assert metrics["cache_hits"] == 1
        assert metrics["cache_misses"] == 1
        assert metrics["cache_hit_rate"] == 50.0
        assert metrics["avg_response_time_ms"] == 100.5

    def test_logger_reset_metrics(self, temp_dir):
        """测试重置指标"""
        from aicmd.logger import AICommandLogger
        
        log_dir = temp_dir / "logs"
        logger = AICommandLogger(log_dir=str(log_dir))
        
        # 记录一些操作
        logger.log_api_call("openai", "gpt-4", "query", 100, True)
        
        # 重置
        logger.reset_metrics()
        
        metrics = logger.get_metrics()
        assert metrics["api_calls"] == 0

    def test_logger_structured_logging(self, temp_dir):
        """测试结构化日志"""
        from aicmd.logger import AICommandLogger
        
        log_dir = temp_dir / "logs"
        logger = AICommandLogger(log_dir=str(log_dir))
        
        # 测试各种结构化日志方法
        logger.log_api_call(
            provider="test",
            model="test-model",
            query="test query",
            response_time_ms=50.0,
            success=True
        )
        
        logger.log_cache_operation("save", "hash123", confidence=0.85)
        
        logger.log_user_action("confirm", "ls -la")
        
        logger.log_safety_check(
            command="rm -rf /",
            is_dangerous=True,
            danger_level="critical",
            warnings=["dangerous"]
        )


class TestLogLevelFromEnv:
    """环境变量日志级别测试"""

    def test_get_log_level_from_env_default(self):
        """测试默认日志级别"""
        from aicmd.logger import get_log_level_from_env
        
        # 清除环境变量
        if "AICMD_LOG_LEVEL" in os.environ:
            del os.environ["AICMD_LOG_LEVEL"]
        
        level = get_log_level_from_env()
        assert level == "INFO"

    def test_get_log_level_from_env_custom(self):
        """测试自定义日志级别"""
        from aicmd.logger import get_log_level_from_env
        
        os.environ["AICMD_LOG_LEVEL"] = "DEBUG"
        
        level = get_log_level_from_env()
        assert level == "DEBUG"
        
        # 清理
        del os.environ["AICMD_LOG_LEVEL"]


class TestLoggerCompatibility:
    """向后兼容性测试"""

    def test_legacy_logger(self):
        """测试旧版 Logger 类"""
        from aicmd.logger import Logger
        
        logger = Logger(use_color=False)
        
        # 所有旧方法应该能工作
        logger.info("test")
        logger.success("test")
        logger.warning("test")
        logger.error("test")
        logger.bold("test")
        logger.print("test")


class TestLogConfigPrecedence:
    """日志配置优先级测试"""

    def test_resolve_log_config_cli_overrides(self):
        """CLI 参数应覆盖环境变量和配置文件"""
        from aicmd.logger import resolve_log_config

        config = {
            "log_level": "INFO",
            "file_log_level": "DEBUG",
            "log_dir": "/config/logs",
        }
        env = {
            "AICMD_LOG_LEVEL": "WARNING",
            "AICMD_FILE_LOG_LEVEL": "ERROR",
            "AICMD_LOG_DIR": "/env/logs",
        }

        resolved = resolve_log_config(
            cli_console_level="CRITICAL",
            cli_file_level="WARNING",
            cli_log_dir="/cli/logs",
            env=env,
            config=config,
        )

        assert resolved["console_level"] == "CRITICAL"
        assert resolved["file_level"] == "WARNING"
        assert resolved["log_dir"] == "/cli/logs"

    def test_resolve_log_config_env_over_config(self):
        """环境变量应覆盖配置文件"""
        from aicmd.logger import resolve_log_config

        config = {
            "log_level": "INFO",
            "file_log_level": "DEBUG",
            "log_dir": "/config/logs",
        }
        env = {
            "AICMD_LOG_LEVEL": "ERROR",
            "AICMD_FILE_LOG_LEVEL": "WARNING",
            "AICMD_LOG_DIR": "/env/logs",
        }

        resolved = resolve_log_config(env=env, config=config)

        assert resolved["console_level"] == "ERROR"
        assert resolved["file_level"] == "WARNING"
        assert resolved["log_dir"] == "/env/logs"

    def test_resolve_log_config_config_over_default(self):
        """配置文件应覆盖默认值"""
        from aicmd.logger import resolve_log_config

        config = {
            "log_level": "warning",
            "file_log_level": "error",
            "log_dir": "/config/logs",
        }

        resolved = resolve_log_config(env={}, config=config)

        assert resolved["console_level"] == "WARNING"
        assert resolved["file_level"] == "ERROR"
        assert resolved["log_dir"] == "/config/logs"
