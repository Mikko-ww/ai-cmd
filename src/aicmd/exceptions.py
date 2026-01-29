"""
统一异常类模块
定义 AI-CMD 项目的异常类层次结构
"""

from typing import Optional, Dict, Any


class AICmdException(Exception):
    """
    AI-CMD 基础异常类
    所有自定义异常都应该继承此类
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None
    ):
        """
        初始化异常
        
        Args:
            message: 错误消息
            error_code: 错误代码（可选）
            details: 错误详细信息（可选）
            recovery_hint: 恢复建议（可选）
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.recovery_hint = recovery_hint
    
    def __str__(self) -> str:
        result = self.message
        if self.error_code:
            result = f"[{self.error_code}] {result}"
        if self.recovery_hint:
            result = f"{result}\n提示: {self.recovery_hint}"
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "recovery_hint": self.recovery_hint
        }


# =============================================================================
# 配置相关异常
# =============================================================================

class ConfigError(AICmdException):
    """配置相关异常基类"""
    pass


class ConfigNotFoundError(ConfigError):
    """配置文件未找到异常"""
    
    def __init__(self, config_path: str):
        super().__init__(
            message=f"配置文件未找到: {config_path}",
            error_code="CONFIG_NOT_FOUND",
            details={"config_path": config_path},
            recovery_hint="使用 'aicmd --create-config' 创建配置文件"
        )


class ConfigParseError(ConfigError):
    """配置文件解析异常"""
    
    def __init__(self, config_path: str, parse_error: str):
        super().__init__(
            message=f"配置文件解析失败: {parse_error}",
            error_code="CONFIG_PARSE_ERROR",
            details={"config_path": config_path, "parse_error": parse_error},
            recovery_hint="检查配置文件的 JSON 格式是否正确"
        )


class ConfigValidationError(ConfigError):
    """配置验证异常"""
    
    def __init__(self, key: str, value: Any, reason: str):
        super().__init__(
            message=f"配置项 '{key}' 验证失败: {reason}",
            error_code="CONFIG_VALIDATION_ERROR",
            details={"key": key, "value": value, "reason": reason},
            recovery_hint=f"请检查配置项 '{key}' 的值是否正确"
        )


class ConfigKeyError(ConfigError):
    """无效配置键异常"""
    
    def __init__(self, key: str):
        super().__init__(
            message=f"无效的配置键: {key}",
            error_code="CONFIG_KEY_ERROR",
            details={"key": key},
            recovery_hint="使用 'aicmd --show-config' 查看有效的配置项"
        )


# =============================================================================
# 缓存相关异常
# =============================================================================

class CacheError(AICmdException):
    """缓存相关异常基类"""
    pass


class CacheReadError(CacheError):
    """缓存读取异常"""
    
    def __init__(self, reason: str, query_hash: Optional[str] = None):
        super().__init__(
            message=f"缓存读取失败: {reason}",
            error_code="CACHE_READ_ERROR",
            details={"query_hash": query_hash, "reason": reason},
            recovery_hint="缓存可能已损坏，可以尝试使用 'aicmd --cleanup-cache' 清理"
        )


class CacheWriteError(CacheError):
    """缓存写入异常"""
    
    def __init__(self, reason: str, query: Optional[str] = None):
        super().__init__(
            message=f"缓存写入失败: {reason}",
            error_code="CACHE_WRITE_ERROR",
            details={"query": query, "reason": reason},
            recovery_hint="检查磁盘空间是否充足"
        )


class CacheCorruptedError(CacheError):
    """缓存损坏异常"""
    
    def __init__(self, db_path: str, reason: str):
        super().__init__(
            message=f"缓存数据库已损坏: {reason}",
            error_code="CACHE_CORRUPTED",
            details={"db_path": db_path, "reason": reason},
            recovery_hint="可以删除缓存文件并重新运行: rm ~/.ai-cmd/cache.db"
        )


# =============================================================================
# 数据库相关异常
# =============================================================================

class DatabaseError(AICmdException):
    """数据库相关异常基类"""
    pass


class DatabaseConnectionError(DatabaseError):
    """数据库连接异常"""
    
    def __init__(self, db_path: str, reason: str):
        super().__init__(
            message=f"数据库连接失败: {reason}",
            error_code="DB_CONNECTION_ERROR",
            details={"db_path": db_path, "reason": reason},
            recovery_hint="检查数据库文件权限和完整性"
        )


class DatabaseQueryError(DatabaseError):
    """数据库查询异常"""
    
    def __init__(self, query: str, reason: str):
        super().__init__(
            message=f"数据库查询失败: {reason}",
            error_code="DB_QUERY_ERROR",
            details={"query": query, "reason": reason},
            recovery_hint="可能是数据库结构已更改，尝试重建数据库"
        )


class DatabaseInitializationError(DatabaseError):
    """数据库初始化异常"""
    
    def __init__(self, db_path: str, reason: str):
        super().__init__(
            message=f"数据库初始化失败: {reason}",
            error_code="DB_INIT_ERROR",
            details={"db_path": db_path, "reason": reason},
            recovery_hint="检查目录权限并确保有足够的磁盘空间"
        )


# =============================================================================
# API 相关异常
# =============================================================================

class APIError(AICmdException):
    """API 相关异常基类"""
    pass


class APIConnectionError(APIError):
    """API 连接异常"""
    
    def __init__(self, provider: str, url: str, reason: str):
        super().__init__(
            message=f"无法连接到 {provider} API: {reason}",
            error_code="API_CONNECTION_ERROR",
            details={"provider": provider, "url": url, "reason": reason},
            recovery_hint="检查网络连接和 API 端点配置"
        )


class APIAuthenticationError(APIError):
    """API 认证异常"""
    
    def __init__(self, provider: str):
        super().__init__(
            message=f"{provider} API 认证失败",
            error_code="API_AUTH_ERROR",
            details={"provider": provider},
            recovery_hint=f"使用 'aicmd --set-api-key {provider} <your-key>' 设置有效的 API 密钥"
        )


class APIRateLimitError(APIError):
    """API 速率限制异常"""
    
    def __init__(self, provider: str, retry_after: Optional[int] = None):
        super().__init__(
            message=f"{provider} API 速率限制已触发",
            error_code="API_RATE_LIMIT",
            details={"provider": provider, "retry_after": retry_after},
            recovery_hint=f"请等待 {retry_after or '一段时间'} 秒后重试"
        )


class APIResponseError(APIError):
    """API 响应异常"""
    
    def __init__(self, provider: str, status_code: int, response_body: str):
        super().__init__(
            message=f"{provider} API 返回错误 (HTTP {status_code})",
            error_code="API_RESPONSE_ERROR",
            details={
                "provider": provider,
                "status_code": status_code,
                "response_body": response_body
            },
            recovery_hint="检查 API 配置和提供商服务状态"
        )


class APITimeoutError(APIError):
    """API 超时异常"""
    
    def __init__(self, provider: str, timeout: int):
        super().__init__(
            message=f"{provider} API 请求超时 ({timeout}秒)",
            error_code="API_TIMEOUT",
            details={"provider": provider, "timeout": timeout},
            recovery_hint="检查网络连接或增加超时时间配置"
        )


class NoAPIKeyError(APIError):
    """缺少 API 密钥异常"""
    
    def __init__(self, provider: str):
        super().__init__(
            message=f"未找到 {provider} 的 API 密钥",
            error_code="NO_API_KEY",
            details={"provider": provider},
            recovery_hint=f"使用 'aicmd --set-api-key {provider} <your-key>' 设置 API 密钥"
        )


# =============================================================================
# 安全相关异常
# =============================================================================

class SecurityError(AICmdException):
    """安全相关异常基类"""
    pass


class DangerousCommandError(SecurityError):
    """危险命令异常"""
    
    def __init__(self, command: str, danger_level: str, warnings: list):
        super().__init__(
            message=f"检测到危险命令 (危险等级: {danger_level})",
            error_code="DANGEROUS_COMMAND",
            details={
                "command": command,
                "danger_level": danger_level,
                "warnings": warnings
            },
            recovery_hint="请仔细检查命令内容，确认后再执行"
        )


class CommandRejectedError(SecurityError):
    """命令被拒绝异常"""
    
    def __init__(self, command: str, reason: str):
        super().__init__(
            message=f"命令被拒绝: {reason}",
            error_code="COMMAND_REJECTED",
            details={"command": command, "reason": reason}
        )


# =============================================================================
# 输入/输出相关异常
# =============================================================================

class IOError(AICmdException):
    """输入/输出相关异常基类"""
    pass


class InputTimeoutError(IOError):
    """输入超时异常"""
    
    def __init__(self, timeout: int):
        super().__init__(
            message=f"等待用户输入超时 ({timeout}秒)",
            error_code="INPUT_TIMEOUT",
            details={"timeout": timeout},
            recovery_hint="可以通过配置调整超时时间"
        )


class ClipboardError(IOError):
    """剪贴板操作异常"""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"剪贴板{operation}失败: {reason}",
            error_code="CLIPBOARD_ERROR",
            details={"operation": operation, "reason": reason},
            recovery_hint="确保剪贴板服务正常运行"
        )


# =============================================================================
# 提供商相关异常
# =============================================================================

class ProviderError(AICmdException):
    """提供商相关异常基类"""
    pass


class ProviderNotFoundError(ProviderError):
    """提供商未找到异常"""
    
    def __init__(self, provider: str, available_providers: list):
        super().__init__(
            message=f"未找到提供商: {provider}",
            error_code="PROVIDER_NOT_FOUND",
            details={
                "provider": provider,
                "available_providers": available_providers
            },
            recovery_hint=f"可用的提供商: {', '.join(available_providers)}"
        )


class ProviderConfigError(ProviderError):
    """提供商配置异常"""
    
    def __init__(self, provider: str, missing_fields: list):
        super().__init__(
            message=f"提供商 {provider} 配置不完整",
            error_code="PROVIDER_CONFIG_ERROR",
            details={
                "provider": provider,
                "missing_fields": missing_fields
            },
            recovery_hint=f"请配置以下字段: {', '.join(missing_fields)}"
        )


# =============================================================================
# 工具函数
# =============================================================================

def format_exception_for_user(exc: Exception) -> str:
    """
    格式化异常信息用于用户显示
    
    Args:
        exc: 异常实例
        
    Returns:
        格式化后的错误消息
    """
    if isinstance(exc, AICmdException):
        return str(exc)
    else:
        return f"发生错误: {str(exc)}"


def is_recoverable(exc: Exception) -> bool:
    """
    判断异常是否可恢复
    
    Args:
        exc: 异常实例
        
    Returns:
        是否可恢复
    """
    # 可恢复的异常类型
    recoverable_types = (
        CacheError,
        APIRateLimitError,
        APITimeoutError,
        InputTimeoutError,
    )
    
    return isinstance(exc, recoverable_types)


def get_recovery_action(exc: AICmdException) -> Optional[str]:
    """
    获取异常的恢复操作建议
    
    Args:
        exc: AI-CMD 异常实例
        
    Returns:
        恢复操作建议
    """
    return exc.recovery_hint
