---
applyTo: "**/*.py"
---

# Python 编码规范

## 命名约定
- 模块/函数/变量：`lower_snake_case`（如 `config_manager.py`、`get_api_key()`）
- 类名：`PascalCase`（如 `LLMProvider`、`ConfigManager`）
- 常量：`UPPER_SNAKE_CASE`（如 `DEFAULT_LOG_LEVEL`、`SERVICE_NAME`）
- 私有成员：单下划线前缀（如 `_instance`、`_session`、`_get_session()`）

## 导入顺序（PEP 8）
```python
# 1. 标准库
import os
import json
from typing import Optional, Dict, Any

# 2. 第三方库
import requests
import keyring

# 3. 项目内部（使用相对导入）
from .config_manager import ConfigManager
from .logger import logger
```

## 类型标注
- 所有函数参数和返回值必须添加类型标注
- 使用 `typing` 模块：`Optional`、`Dict`、`List`、`Tuple`、`Any`
- 示例：`def get_api_key(self, provider: str) -> Optional[str]:`

## 文档字符串（Google 风格，中英双语）
```python
"""
中文简述

Args:
    query: 查询字符串
    command: shell 命令

Returns:
    缓存条目 ID 或 None
"""
```

- 模块级文档字符串放在文件最顶部，用中文描述模块职责
- 类的文档字符串用中文说明用途和设计意图
- 注释解释「为什么」而非「是什么」

## 格式化工具
- 使用 Black 格式化：`uv run black src/`
- 使用 Flake8 检查：`uv run flake8 src/`
- 4 空格缩进，Python 3.9+ 语法

## 日志规范
- 使用项目 logger（`from .logger import logger`），禁止在 src/ 代码中使用 `print` 做诊断输出
- 日志级别：`logger.debug()` 调试信息、`logger.info()` 正常操作、`logger.warning()` 警告、`logger.error()` 错误
