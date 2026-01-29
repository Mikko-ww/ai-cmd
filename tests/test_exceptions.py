"""
exceptions 单元测试
测试统一异常类
"""

import pytest


class TestAICmdException:
    """AICmdException 基础异常测试"""

    def test_basic_exception(self):
        """测试基础异常"""
        from aicmd.exceptions import AICmdException
        
        exc = AICmdException("Test error")
        
        assert exc.message == "Test error"
        assert exc.error_code is None
        assert exc.details == {}
        assert exc.recovery_hint is None

    def test_exception_with_all_fields(self):
        """测试带所有字段的异常"""
        from aicmd.exceptions import AICmdException
        
        exc = AICmdException(
            message="Test error",
            error_code="TEST_001",
            details={"key": "value"},
            recovery_hint="Try again"
        )
        
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_001"
        assert exc.details == {"key": "value"}
        assert exc.recovery_hint == "Try again"

    def test_exception_str_format(self):
        """测试异常字符串格式"""
        from aicmd.exceptions import AICmdException
        
        exc = AICmdException(
            message="Test error",
            error_code="TEST_001",
            recovery_hint="Try again"
        )
        
        str_repr = str(exc)
        
        assert "[TEST_001]" in str_repr
        assert "Test error" in str_repr
        assert "Try again" in str_repr

    def test_exception_to_dict(self):
        """测试异常转换为字典"""
        from aicmd.exceptions import AICmdException
        
        exc = AICmdException(
            message="Test error",
            error_code="TEST_001",
            details={"key": "value"},
            recovery_hint="Try again"
        )
        
        d = exc.to_dict()
        
        assert d["type"] == "AICmdException"
        assert d["message"] == "Test error"
        assert d["error_code"] == "TEST_001"
        assert d["details"] == {"key": "value"}
        assert d["recovery_hint"] == "Try again"


class TestConfigExceptions:
    """配置异常测试"""

    def test_config_not_found_error(self):
        """测试配置文件未找到异常"""
        from aicmd.exceptions import ConfigNotFoundError
        
        exc = ConfigNotFoundError("/path/to/config.json")
        
        assert "配置文件未找到" in exc.message
        assert exc.error_code == "CONFIG_NOT_FOUND"
        assert exc.details["config_path"] == "/path/to/config.json"
        assert "--create-config" in exc.recovery_hint

    def test_config_parse_error(self):
        """测试配置解析异常"""
        from aicmd.exceptions import ConfigParseError
        
        exc = ConfigParseError("/path/to/config.json", "Invalid JSON")
        
        assert "解析失败" in exc.message
        assert exc.error_code == "CONFIG_PARSE_ERROR"

    def test_config_validation_error(self):
        """测试配置验证异常"""
        from aicmd.exceptions import ConfigValidationError
        
        exc = ConfigValidationError("confidence_threshold", 1.5, "Must be between 0 and 1")
        
        assert "验证失败" in exc.message
        assert exc.error_code == "CONFIG_VALIDATION_ERROR"
        assert exc.details["key"] == "confidence_threshold"
        assert exc.details["value"] == 1.5


class TestCacheExceptions:
    """缓存异常测试"""

    def test_cache_read_error(self):
        """测试缓存读取异常"""
        from aicmd.exceptions import CacheReadError
        
        exc = CacheReadError("Database locked", "abc123")
        
        assert "读取失败" in exc.message
        assert exc.error_code == "CACHE_READ_ERROR"
        assert exc.details["query_hash"] == "abc123"

    def test_cache_write_error(self):
        """测试缓存写入异常"""
        from aicmd.exceptions import CacheWriteError
        
        exc = CacheWriteError("Disk full", "test query")
        
        assert "写入失败" in exc.message
        assert exc.error_code == "CACHE_WRITE_ERROR"

    def test_cache_corrupted_error(self):
        """测试缓存损坏异常"""
        from aicmd.exceptions import CacheCorruptedError
        
        exc = CacheCorruptedError("/path/to/cache.db", "Checksum mismatch")
        
        assert "损坏" in exc.message
        assert exc.error_code == "CACHE_CORRUPTED"


class TestDatabaseExceptions:
    """数据库异常测试"""

    def test_database_connection_error(self):
        """测试数据库连接异常"""
        from aicmd.exceptions import DatabaseConnectionError
        
        exc = DatabaseConnectionError("/path/to/db", "Permission denied")
        
        assert "连接失败" in exc.message
        assert exc.error_code == "DB_CONNECTION_ERROR"

    def test_database_query_error(self):
        """测试数据库查询异常"""
        from aicmd.exceptions import DatabaseQueryError
        
        exc = DatabaseQueryError("SELECT * FROM users", "Table not found")
        
        assert "查询失败" in exc.message
        assert exc.error_code == "DB_QUERY_ERROR"


class TestAPIExceptions:
    """API 异常测试"""

    def test_api_connection_error(self):
        """测试 API 连接异常"""
        from aicmd.exceptions import APIConnectionError
        
        exc = APIConnectionError("openrouter", "https://api.openrouter.ai", "Connection refused")
        
        assert "openrouter" in exc.message
        assert exc.error_code == "API_CONNECTION_ERROR"

    def test_api_authentication_error(self):
        """测试 API 认证异常"""
        from aicmd.exceptions import APIAuthenticationError
        
        exc = APIAuthenticationError("openai")
        
        assert "认证失败" in exc.message
        assert exc.error_code == "API_AUTH_ERROR"
        assert "--set-api-key" in exc.recovery_hint

    def test_api_rate_limit_error(self):
        """测试 API 速率限制异常"""
        from aicmd.exceptions import APIRateLimitError
        
        exc = APIRateLimitError("openai", retry_after=60)
        
        assert "速率限制" in exc.message
        assert exc.error_code == "API_RATE_LIMIT"
        assert exc.details["retry_after"] == 60

    def test_api_timeout_error(self):
        """测试 API 超时异常"""
        from aicmd.exceptions import APITimeoutError
        
        exc = APITimeoutError("openai", 30)
        
        assert "超时" in exc.message
        assert exc.error_code == "API_TIMEOUT"

    def test_no_api_key_error(self):
        """测试缺少 API 密钥异常"""
        from aicmd.exceptions import NoAPIKeyError
        
        exc = NoAPIKeyError("deepseek")
        
        assert "未找到" in exc.message
        assert exc.error_code == "NO_API_KEY"


class TestSecurityExceptions:
    """安全异常测试"""

    def test_dangerous_command_error(self):
        """测试危险命令异常"""
        from aicmd.exceptions import DangerousCommandError
        
        exc = DangerousCommandError(
            "rm -rf /",
            "critical",
            ["This command could delete everything"]
        )
        
        assert "危险命令" in exc.message
        assert exc.error_code == "DANGEROUS_COMMAND"
        assert exc.details["danger_level"] == "critical"

    def test_command_rejected_error(self):
        """测试命令拒绝异常"""
        from aicmd.exceptions import CommandRejectedError
        
        exc = CommandRejectedError("rm -rf /", "User cancelled")
        
        assert "拒绝" in exc.message
        assert exc.error_code == "COMMAND_REJECTED"


class TestUtilityFunctions:
    """工具函数测试"""

    def test_format_exception_for_user(self):
        """测试格式化异常"""
        from aicmd.exceptions import AICmdException, format_exception_for_user
        
        exc = AICmdException("Test error", error_code="TEST", recovery_hint="Try again")
        formatted = format_exception_for_user(exc)
        
        assert "Test error" in formatted
        
        # 普通异常
        regular_exc = ValueError("Regular error")
        formatted = format_exception_for_user(regular_exc)
        
        assert "Regular error" in formatted

    def test_is_recoverable(self):
        """测试异常是否可恢复"""
        from aicmd.exceptions import (
            is_recoverable,
            CacheError,
            APIRateLimitError,
            APITimeoutError,
            ConfigError,
            DatabaseError
        )
        
        # 可恢复的异常
        assert is_recoverable(CacheError("test")) is True
        assert is_recoverable(APIRateLimitError("test")) is True
        assert is_recoverable(APITimeoutError("test", 30)) is True
        
        # 不可恢复的异常
        assert is_recoverable(ConfigError("test")) is False
        assert is_recoverable(DatabaseError("test")) is False

    def test_get_recovery_action(self):
        """测试获取恢复操作"""
        from aicmd.exceptions import AICmdException, get_recovery_action
        
        exc = AICmdException("Test", recovery_hint="Do something")
        
        assert get_recovery_action(exc) == "Do something"
        
        exc_no_hint = AICmdException("Test")
        assert get_recovery_action(exc_no_hint) is None
