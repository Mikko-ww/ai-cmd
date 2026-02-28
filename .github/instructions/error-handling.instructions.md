---
description: "在编写错误处理、异常捕获、try/except 逻辑、或实现新功能降级策略时使用。覆盖 GracefulDegradationManager 模式和异常层次结构。"
applyTo: "src/aicmd/**/*.py"
---

# 错误处理与优雅降级模式

## 核心原则：优雅降级
所有增强功能（缓存、置信度、交互）必须包装在 `GracefulDegradationManager` 中，任何失败自动降级到基础 API 模式，绝不阻断用户流程。

## GracefulDegradationManager 用法
```python
from .error_handler import GracefulDegradationManager

# 保护缓存操作
result = degradation_manager.with_cache_fallback(
    cache_operation=lambda: cache.get(query),      # 主操作
    fallback_operation=lambda: api_client.send(query),  # 降级操作
    operation_name="get_cached_command"
)
```

- 错误计数超限（默认 3 次）自动禁用缓存
- 成功操作会逐步递减错误计数
- 可通过 `--reset-errors` CLI 标志手动重置

## 异常层次结构
```
AICmdException (基类，包含 error_code/details/recovery_hint)
├── ConfigError / ConfigNotFoundError / ConfigParseError / ConfigValidationError
├── CacheError / CacheReadError / CacheWriteError / CacheCorruptedError
├── DatabaseError / DatabaseConnectionError / DatabaseQueryError
└── APIClientError / APITimeoutError / APIRateLimitError / APIAuthError
```

## try/except 规范
- 捕获特定异常类型，避免裸 `except Exception`
- 异常处理内记录日志后降级，而非直接抛出
- 返回安全默认值（`None`、`False`、空集合）保持流程继续

```python
# 正确 ✓
try:
    keyring.set_password(cls.SERVICE_NAME, provider, api_key)
    logger.info(f"API key set for: {provider}")
    return True
except Exception as e:
    logger.error(f"Failed to set API key for {provider}: {e}")
    return False  # 降级返回

# 错误 ✗ - 不处理直接抛出，中断流程
try:
    keyring.set_password(...)
except:
    raise  # 这会阻断用户操作
```
