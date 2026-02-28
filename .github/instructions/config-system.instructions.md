---
description: "在修改配置加载逻辑、添加新配置项、使用 ConfigManager、或调整配置优先级时使用。覆盖多层配置系统和单例模式。"
---

# 配置系统规范

## 配置优先级（从高到低）
1. **CLI 参数**：`--log-level DEBUG`、`--force-api` 等
2. **环境变量**：`AICMD_LOG_LEVEL`、`AICMD_KEYRING_SERVICE` 等前缀 `AICMD_*`
3. **JSON 配置文件**：用户配置 `~/.ai-cmd/settings.json` > 项目配置 `./.ai-cmd.json`
4. **默认值**：代码中硬编码

新增配置项时必须在所有 4 层都有对应处理。

## ConfigManager 单例模式
```python
class ConfigManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```
- 应用内仅一个实例，避免重复加载
- 测试中通过 `ConfigManager.reset_instance()` 重置
- 新增管理器类考虑是否需要单例

## 配置结构（setting_template.json）
```json
{
  "version": "1.0.2",
  "basic": { "interactive_mode", "cache_enabled", "auto_copy_threshold" },
  "api": { "timeout_seconds", "max_retries", "default_provider" },
  "providers": { "<provider_name>": { "model", "base_url" } },
  "cache": { "cache_directory", "database_file" },
  "confidence": { "confidence_threshold", "similarity_threshold" },
  "logging": { "log_level", "file_log_level", "log_dir" }
}
```

## 关键阈值
| 配置项 | 默认值 | 作用 |
|--------|--------|------|
| `auto_copy_threshold` | 0.9 → 1.0 | 高置信度自动复制到剪贴板 |
| `confidence_threshold` | 0.8 | 使用缓存结果的最低置信度 |
| `similarity_threshold` | 0.7 | 模糊匹配查询的截断线 |

## 添加新配置项清单
1. 在 `setting_template.json` 对应分组中添加字段
2. 在 `ConfigManager` 的 `default_config` 中设置默认值
3. 在 `_flatten_json_config()` 中处理 JSON 映射
4. 如需 CLI 支持，在 `ai.py` 的 `argparse` 中添加参数
5. 如需环境变量支持，在相关 `resolve_*` 函数中处理 `AICMD_` 前缀变量
