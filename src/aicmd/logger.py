"""
增强的日志模块
使用标准Python logging库，支持文件轮转、彩色输出、结构化日志和可配置日志级别
"""

import sys
import os
import json
import logging
import logging.handlers
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime
from contextlib import contextmanager


# =============================================================================
# 日志配置常量
# =============================================================================

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_FILE_LOG_LEVEL = "DEBUG"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5MB
DEFAULT_BACKUP_COUNT = 5
DEFAULT_LOG_DIR = "~/.ai-cmd/logs"


def get_log_level_from_env() -> str:
    """从环境变量获取日志级别"""
    return os.environ.get("AICMD_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()


def get_file_log_level_from_env() -> str:
    """从环境变量获取文件日志级别"""
    return os.environ.get("AICMD_FILE_LOG_LEVEL", DEFAULT_FILE_LOG_LEVEL).upper()


# =============================================================================
# 格式化器
# =============================================================================

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI颜色码
    COLORS = {
        'DEBUG': '\033[96m',    # 青色
        'INFO': '\033[94m',     # 蓝色
        'WARNING': '\033[93m',  # 黄色
        'ERROR': '\033[91m',    # 红色
        'CRITICAL': '\033[95m', # 紫色
        'RESET': '\033[0m'      # 重置
    }
    
    def __init__(self, use_color: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_color = use_color and self._supports_color()
    
    def _supports_color(self) -> bool:
        """检查终端是否支持颜色"""
        # 检查 NO_COLOR 环境变量
        if os.environ.get("NO_COLOR"):
            return False
        return (
            hasattr(sys.stdout, "isatty")
            and sys.stdout.isatty()
            and os.environ.get("TERM", "").lower() != "dumb"
            and os.name != 'nt'  # Windows Terminal 支持有限
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        if self.use_color and record.levelname in self.COLORS:
            # 添加颜色
            levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            # 临时替换levelname用于格式化
            original_levelname = record.levelname
            record.levelname = levelname
            formatted = super().format(record)
            # 恢复原始levelname
            record.levelname = original_levelname
            return formatted
        else:
            return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON 结构化日志格式化器"""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加请求 ID（如果存在）
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # 添加额外字段
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in (
                    "name", "msg", "args", "created", "filename", "funcName",
                    "levelname", "levelno", "lineno", "module", "msecs",
                    "pathname", "process", "processName", "relativeCreated",
                    "stack_info", "exc_info", "exc_text", "thread", "threadName",
                    "message", "request_id"
                ):
                    try:
                        json.dumps(value)  # 确保值可序列化
                        extra_fields[key] = value
                    except (TypeError, ValueError):
                        extra_fields[key] = str(value)
            
            if extra_fields:
                log_data["extra"] = extra_fields
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class AICommandLogger:
    """AI Command工具的增强日志管理器"""
    
    # 类级别的请求 ID（用于跟踪）
    _current_request_id: Optional[str] = None
    
    def __init__(
        self, 
        name: str = "aicmd", 
        log_dir: Optional[str] = None,
        use_color: bool = True,
        console_level: Optional[str] = None,
        file_level: Optional[str] = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        backup_count: int = DEFAULT_BACKUP_COUNT,
        enable_json_file: bool = False
    ):
        """
        初始化日志管理器
        
        Args:
            name: 日志器名称
            log_dir: 日志目录路径，None表示使用默认路径
            use_color: 是否在控制台使用颜色
            console_level: 控制台日志级别（默认从环境变量或 INFO）
            file_level: 文件日志级别（默认从环境变量或 DEBUG）
            max_bytes: 单个日志文件最大字节数
            backup_count: 日志备份数量
            enable_json_file: 是否启用 JSON 格式的日志文件
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # 设置为最低级别，由handler控制
        
        # 清除现有handlers
        self.logger.handlers.clear()
        
        # 使用环境变量或参数
        console_level = console_level or get_log_level_from_env()
        file_level = file_level or get_file_log_level_from_env()
        
        # 设置日志目录
        if log_dir is None:
            log_dir = os.environ.get("AICMD_LOG_DIR", DEFAULT_LOG_DIR)
        self.log_dir = Path(log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存配置
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # 添加控制台处理器
        self._setup_console_handler(use_color, console_level)
        
        # 添加文件处理器
        self._setup_file_handler(file_level)
        
        # 可选：添加 JSON 文件处理器
        if enable_json_file:
            self._setup_json_file_handler(file_level)
        
        # 防止重复日志
        self.logger.propagate = False
        
        # 性能指标收集
        self._metrics: Dict[str, Any] = {
            "api_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_response_time_ms": 0,
        }
    
    def _setup_console_handler(self, use_color: bool, level: str):
        """设置控制台日志处理器"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # 简化的控制台格式（用户友好）
        console_formatter = ColoredFormatter(
            use_color=use_color,
            fmt='%(message)s'  # 只显示消息内容
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def _setup_file_handler(self, level: str):
        """设置文件日志处理器（支持轮转）"""
        log_file = self.log_dir / "aicmd.log"
        
        # 使用RotatingFileHandler支持文件轮转
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        
        # 详细的文件格式（调试友好）
        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
    
    def _setup_json_file_handler(self, level: str):
        """设置 JSON 格式的日志文件处理器"""
        json_log_file = self.log_dir / "aicmd.json.log"
        
        json_handler = logging.handlers.RotatingFileHandler(
            json_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        json_handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        json_handler.setFormatter(JSONFormatter(include_extra=True))
        self.logger.addHandler(json_handler)
    
    def _add_request_id(self, extra: Optional[Dict] = None) -> Dict:
        """添加请求 ID 到日志额外信息"""
        extra = extra or {}
        if self._current_request_id:
            extra["request_id"] = self._current_request_id
        return extra
    
    @classmethod
    def set_request_id(cls, request_id: Optional[str] = None) -> str:
        """设置当前请求 ID"""
        cls._current_request_id = request_id or str(uuid.uuid4())[:8]
        return cls._current_request_id
    
    @classmethod
    def clear_request_id(cls):
        """清除当前请求 ID"""
        cls._current_request_id = None
    
    @classmethod
    @contextmanager
    def request_context(cls, request_id: Optional[str] = None):
        """请求上下文管理器"""
        rid = cls.set_request_id(request_id)
        try:
            yield rid
        finally:
            cls.clear_request_id()
    
    def info(self, msg: str, **kwargs):
        """信息日志"""
        extra = self._add_request_id(kwargs.get("extra"))
        self.logger.info(msg, extra=extra)
    
    def success(self, msg: str, **kwargs):
        """成功日志（以INFO级别记录）"""
        extra = self._add_request_id(kwargs.get("extra"))
        self.logger.info(f"✓ {msg}", extra=extra)
    
    def warning(self, msg: str, **kwargs):
        """警告日志"""
        extra = self._add_request_id(kwargs.get("extra"))
        self.logger.warning(msg, extra=extra)
    
    def error(self, msg: str, **kwargs):
        """错误日志"""
        extra = self._add_request_id(kwargs.get("extra"))
        self.logger.error(msg, extra=extra)
    
    def debug(self, msg: str, **kwargs):
        """调试日志"""
        extra = self._add_request_id(kwargs.get("extra"))
        self.logger.debug(msg, extra=extra)
    
    def critical(self, msg: str, **kwargs):
        """严重错误日志"""
        extra = self._add_request_id(kwargs.get("extra"))
        self.logger.critical(msg, extra=extra)
    
    def print(self, msg: str):
        """普通打印（不经过日志系统）"""
        print(msg)
    
    # =========================================================================
    # 结构化日志方法
    # =========================================================================
    
    def log_api_call(
        self,
        provider: str,
        model: str,
        query: str,
        response_time_ms: float,
        success: bool,
        error: Optional[str] = None
    ):
        """记录 API 调用"""
        self._metrics["api_calls"] += 1
        self._metrics["total_response_time_ms"] += response_time_ms
        
        extra = self._add_request_id({
            "event_type": "api_call",
            "provider": provider,
            "model": model,
            "query_preview": query[:50] + "..." if len(query) > 50 else query,
            "response_time_ms": round(response_time_ms, 2),
            "success": success,
            "error": error
        })
        
        if success:
            self.logger.info(
                f"API call to {provider}/{model} completed in {response_time_ms:.0f}ms",
                extra=extra
            )
        else:
            self.logger.error(
                f"API call to {provider}/{model} failed: {error}",
                extra=extra
            )
    
    def log_cache_operation(
        self,
        operation: str,  # "hit", "miss", "save", "delete"
        query_hash: Optional[str] = None,
        confidence: Optional[float] = None
    ):
        """记录缓存操作"""
        if operation == "hit":
            self._metrics["cache_hits"] += 1
        elif operation == "miss":
            self._metrics["cache_misses"] += 1
        
        extra = self._add_request_id({
            "event_type": "cache_operation",
            "operation": operation,
            "query_hash": query_hash,
            "confidence": confidence
        })
        
        self.logger.debug(
            f"Cache {operation}" + (f" (hash: {query_hash[:8]}...)" if query_hash else ""),
            extra=extra
        )
    
    def log_user_action(
        self,
        action: str,  # "confirm", "reject", "edit", "cancel"
        command: Optional[str] = None
    ):
        """记录用户操作"""
        extra = self._add_request_id({
            "event_type": "user_action",
            "action": action,
            "command_preview": command[:30] + "..." if command and len(command) > 30 else command
        })
        
        self.logger.info(f"User action: {action}", extra=extra)
    
    def log_safety_check(
        self,
        command: str,
        is_dangerous: bool,
        danger_level: str,
        warnings: list
    ):
        """记录安全检查"""
        extra = self._add_request_id({
            "event_type": "safety_check",
            "command_preview": command[:50] + "..." if len(command) > 50 else command,
            "is_dangerous": is_dangerous,
            "danger_level": danger_level,
            "warning_count": len(warnings)
        })
        
        if is_dangerous:
            self.logger.warning(
                f"Dangerous command detected (level: {danger_level})",
                extra=extra
            )
        else:
            self.logger.debug("Safety check passed", extra=extra)
    
    # =========================================================================
    # 指标和状态
    # =========================================================================
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        metrics = self._metrics.copy()
        
        # 计算缓存命中率
        total_cache_ops = metrics["cache_hits"] + metrics["cache_misses"]
        if total_cache_ops > 0:
            metrics["cache_hit_rate"] = round(
                metrics["cache_hits"] / total_cache_ops * 100, 2
            )
        else:
            metrics["cache_hit_rate"] = 0.0
        
        # 计算平均响应时间
        if metrics["api_calls"] > 0:
            metrics["avg_response_time_ms"] = round(
                metrics["total_response_time_ms"] / metrics["api_calls"], 2
            )
        else:
            metrics["avg_response_time_ms"] = 0.0
        
        return metrics
    
    def reset_metrics(self):
        """重置性能指标"""
        self._metrics = {
            "api_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_response_time_ms": 0,
        }
    
    def get_log_info(self) -> Dict[str, Any]:
        """获取日志配置信息"""
        return {
            "log_dir": str(self.log_dir),
            "log_file": str(self.log_dir / "aicmd.log"),
            "handlers": len(self.logger.handlers),
            "level": self.logger.level,
            "exists": (self.log_dir / "aicmd.log").exists(),
            "max_bytes": self.max_bytes,
            "backup_count": self.backup_count,
        }
    
    def set_level(self, console_level: Optional[str] = None, file_level: Optional[str] = None):
        """动态设置日志级别"""
        if console_level and self.logger.handlers:
            # 假设第一个handler是控制台handler
            console_handler = self.logger.handlers[0]
            console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
        
        if file_level and len(self.logger.handlers) > 1:
            # 假设第二个handler是文件handler
            file_handler = self.logger.handlers[1]
            file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))


# 为了保持向后兼容，创建一个兼容的Logger类
class Logger:
    """向后兼容的Logger类，内部使用AICommandLogger"""
    
    def __init__(self, use_color: bool = True):
        self._enhanced_logger = AICommandLogger(use_color=use_color)
    
    def info(self, msg: str):
        self._enhanced_logger.info(msg)
    
    def success(self, msg: str):
        self._enhanced_logger.success(msg)
    
    def warning(self, msg: str):
        self._enhanced_logger.warning(msg)
    
    def error(self, msg: str):
        self._enhanced_logger.error(msg)
    
    def bold(self, msg: str):
        # bold被映射为info，因为标准logging没有bold级别
        self._enhanced_logger.info(f"**{msg}**")
    
    def print(self, msg: str):
        self._enhanced_logger.print(msg)


# 创建全局logger实例（向后兼容）
logger = Logger()

# 创建增强的logger实例
enhanced_logger = AICommandLogger()