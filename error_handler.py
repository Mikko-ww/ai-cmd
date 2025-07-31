"""
错误处理和优雅降级机制模块
确保缓存功能的任何异常都不会影响原有的 API 调用功能
"""

import logging
import os
from datetime import datetime
from typing import Callable, Any, Optional, Dict
from functools import wraps


class GracefulDegradationManager:
    """优雅降级管理器，处理各种异常情况并确保系统稳定性"""

    def __init__(self, max_error_count: int = 3, error_reset_interval: int = 300):
        """
        初始化优雅降级管理器

        Args:
            max_error_count: 最大错误次数，超过后禁用缓存
            error_reset_interval: 错误计数重置间隔（秒）
        """
        self.cache_available = True
        self.database_available = True
        self.config_available = True

        self.error_count = 0
        self.max_error_count = max_error_count
        self.error_reset_interval = error_reset_interval
        self.last_error_time = None
        self.last_reset_time = datetime.now()

        # 错误统计
        self.error_stats = {
            "database_errors": 0,
            "config_errors": 0,
            "cache_errors": 0,
            "network_errors": 0,
            "unknown_errors": 0,
        }

        # 设置基础日志
        self._setup_logging()

    def _setup_logging(self):
        """设置基础日志配置"""
        try:
            log_dir = os.path.expanduser("~/.ai-cmd/logs")
            os.makedirs(log_dir, exist_ok=True)

            log_file = os.path.join(log_dir, "error_handler.log")

            logging.basicConfig(
                level=logging.WARNING,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
            )

            self.logger = logging.getLogger(__name__)
        except Exception:
            # 如果日志设置失败，使用基础日志
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.StreamHandler())

    def with_cache_fallback(
        self,
        cache_operation: Callable,
        fallback_operation: Callable,
        operation_name: str = "cache_operation",
    ) -> Any:
        """
        执行缓存操作，如果失败则回退到备用操作

        Args:
            cache_operation: 缓存相关操作
            fallback_operation: 备用操作（通常是原有功能）
            operation_name: 操作名称，用于日志记录

        Returns:
            操作结果
        """
        # 检查是否需要重置错误计数
        self._maybe_reset_error_count()

        # 如果缓存已被禁用，直接执行备用操作
        if not self.cache_available:
            self.logger.info(f"Cache disabled, using fallback for {operation_name}")
            return self._safe_execute(fallback_operation, operation_name + "_fallback")

        try:
            # 尝试执行缓存操作
            result = cache_operation()
            # 操作成功，重置部分错误计数
            if self.error_count > 0:
                self.error_count = max(0, self.error_count - 1)
            return result

        except Exception as e:
            # 记录并处理缓存错误
            self._handle_cache_error(e, operation_name)

            # 执行备用操作
            return self._safe_execute(fallback_operation, operation_name + "_fallback")

    def _safe_execute(self, operation: Callable, operation_name: str) -> Any:
        """安全执行操作，捕获所有异常"""
        try:
            return operation()
        except Exception as e:
            self.logger.error(f"Error in {operation_name}: {str(e)}")
            self._classify_and_count_error(e)
            return None

    def _handle_cache_error(self, error: Exception, operation_name: str):
        """处理缓存相关错误"""
        self.error_count += 1
        self.last_error_time = datetime.now()

        # 记录详细错误信息
        error_msg = "Cache error in {}: {}".format(operation_name, str(error))
        self.logger.warning(error_msg)

        # 分类并统计错误
        self._classify_and_count_error(error)

        # 决定是否禁用缓存
        if self.error_count >= self.max_error_count:
            self.cache_available = False
            self.logger.error(
                f"Cache disabled after {self.error_count} errors. Last error: {error}"
            )
            print("Warning: Cache functionality disabled due to repeated errors.")

        # 根据错误类型采取特定行动
        self._handle_specific_error_type(error)

    def _classify_and_count_error(self, error: Exception):
        """分类错误并更新统计"""
        error_msg = str(error).lower()

        if "database" in error_msg or "sqlite" in error_msg or "sql" in error_msg:
            self.error_stats["database_errors"] += 1
            self.database_available = False
        elif "config" in error_msg or "environment" in error_msg:
            self.error_stats["config_errors"] += 1
            self.config_available = False
        elif "cache" in error_msg:
            self.error_stats["cache_errors"] += 1
        elif (
            "network" in error_msg
            or "connection" in error_msg
            or "timeout" in error_msg
        ):
            self.error_stats["network_errors"] += 1
        else:
            self.error_stats["unknown_errors"] += 1

    def _handle_specific_error_type(self, error: Exception):
        """根据错误类型采取特定的处理措施"""
        error_msg = str(error).lower()

        if "permission" in error_msg:
            self.logger.error(
                "Permission error detected. Check file/directory permissions."
            )
        elif "disk" in error_msg or "space" in error_msg:
            self.logger.error("Disk space error detected. Check available storage.")
        elif "memory" in error_msg:
            self.logger.error("Memory error detected. System may be under heavy load.")

    def _maybe_reset_error_count(self):
        """如果超过重置间隔，重置错误计数"""
        now = datetime.now()
        if (now - self.last_reset_time).seconds > self.error_reset_interval:
            old_count = self.error_count
            self.error_count = max(0, self.error_count // 2)  # 减半重置
            self.last_reset_time = now

            # 如果错误计数降低，尝试重新启用功能
            if old_count > 0 and self.error_count < self.max_error_count:
                if not self.cache_available:
                    self.cache_available = True
                    self.logger.info("Cache re-enabled after error count reset")
                    print("Info: Cache functionality re-enabled.")

    def force_reset(self):
        """强制重置所有错误状态"""
        self.error_count = 0
        self.cache_available = True
        self.database_available = True
        self.config_available = True
        self.last_error_time = None
        self.last_reset_time = datetime.now()

        # 重置错误统计
        for key in self.error_stats:
            self.error_stats[key] = 0

        self.logger.info("Error handler state forcefully reset")

    def get_status(self) -> Dict[str, Any]:
        """获取当前错误处理器状态"""
        return {
            "cache_available": self.cache_available,
            "database_available": self.database_available,
            "config_available": self.config_available,
            "error_count": self.error_count,
            "max_error_count": self.max_error_count,
            "last_error_time": (
                self.last_error_time.isoformat() if self.last_error_time else None
            ),
            "error_stats": self.error_stats.copy(),
            "uptime_minutes": (datetime.now() - self.last_reset_time).seconds // 60,
        }

    def is_healthy(self) -> bool:
        """检查系统是否健康"""
        return (
            self.error_count < self.max_error_count
            and self.cache_available
            and self.error_stats["unknown_errors"] < 5
        )


def safe_cache_operation(
    degradation_manager: Optional[GracefulDegradationManager] = None,
):
    """
    装饰器：为缓存操作提供安全保护
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if degradation_manager is None:
                # 如果没有提供降级管理器，直接执行
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logging.warning(f"Error in {func.__name__}: {str(e)}")
                    return None

            # 使用降级管理器保护执行
            def cache_op():
                return func(*args, **kwargs)

            def fallback_op():
                return None

            return degradation_manager.with_cache_fallback(
                cache_op, fallback_op, func.__name__
            )

        return wrapper

    return decorator


# 全局降级管理器实例
_global_degradation_manager = None


def get_degradation_manager() -> GracefulDegradationManager:
    """获取全局降级管理器实例"""
    global _global_degradation_manager
    if _global_degradation_manager is None:
        _global_degradation_manager = GracefulDegradationManager()
    return _global_degradation_manager


def safe_import(module_name: str, fallback_value: Any = None) -> Any:
    """安全导入模块，失败时返回备用值"""
    try:
        if "." in module_name:
            # 处理 from module import class 的情况
            parts = module_name.split(".")
            module = __import__(".".join(parts[:-1]), fromlist=[parts[-1]])
            return getattr(module, parts[-1])
        else:
            return __import__(module_name)
    except Exception as e:
        degradation_manager = get_degradation_manager()
        degradation_manager.logger.warning(f"Failed to import {module_name}: {str(e)}")
        return fallback_value


def create_safe_function(
    func: Callable, fallback_result: Any = None, operation_name: Optional[str] = None
) -> Callable:
    """创建一个安全版本的函数，异常时返回备用结果"""
    operation_name = operation_name or func.__name__

    def safe_func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            degradation_manager = get_degradation_manager()
            degradation_manager.logger.warning(f"Error in {operation_name}: {str(e)}")
            degradation_manager._classify_and_count_error(e)
            return fallback_result

    return safe_func
