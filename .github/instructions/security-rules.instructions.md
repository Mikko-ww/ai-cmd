---
description: "在处理 API Key、密钥存储、敏感数据、安全检查、危险命令检测、或修改 keyring/safety 相关代码时使用。"
applyTo: "src/aicmd/**/*.py"
---

# 安全规范

## API Key 管理（核心安全策略）
- **必须使用系统 keyring** 存储所有 API Key，通过 `KeyringManager` 操作
- **禁止在配置文件中存储 API Key**，`settings.json` 仅保留 `model`/`base_url` 字段
- 服务名：生产环境 `com.aicmd.ww`，测试环境 `com.aicmd.ww.test`（通过 `AICMD_KEYRING_SERVICE` 环境变量切换）

```python
# 正确 ✓ - 使用 KeyringManager
from .keyring_manager import KeyringManager
api_key = KeyringManager.get_api_key("openai")

# 错误 ✗ - 硬编码或明文存储
api_key = config.get("api_key")  # 已废弃
api_key = "sk-xxxx"  # 绝不允许
```

## Key 显示规则
- 展示 API Key 时只显示前 10 个字符，其余用 `*` 遮盖
- 日志中禁止记录完整 API Key

## 命令安全检查
`CommandSafetyChecker` 负责检测危险命令，返回四级风险等级：
- `safe` — 安全命令，直接执行
- `warning` — 低风险，提醒用户
- `dangerous` — 高风险（`rm -rf`、`chmod 777`、`killall`），需确认
- `critical` — 系统级破坏（`rm -rf /`、`dd of=/dev/`、`shutdown`），强制确认

**规则**：危险命令无论置信度多高，都必须经过用户显式确认。

## 安全编码要点
- 所有外部输入（用户 prompt、API 响应）在使用前进行验证
- 数据库操作使用参数化查询，防止 SQL 注入
- 文件操作使用 `Path` 对象，避免路径注入
