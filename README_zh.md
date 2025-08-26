# AI Command（aicmd）

一个将自然语言转换为 Shell 命令的智能 CLI，内置缓存、危险命令安全检查与交互式确认，基于 OpenRouter 提供能力。

为什么值得一用
- 自然语言直接生成命令（只输出命令，不加解释）
- 带置信度学习与时间衰减的智能缓存
- 交互式确认，包含安全预警与自动复制到剪贴板
- 相似查询复用，减少重复 API 调用
- JSON 输出，便于脚本与自动化集成
- 优雅降级：即使缓存/数据库异常，核心 API 流仍可用

快速开始
1）安装依赖与命令行

- 推荐使用 uv
  - `uv sync`
  - `uv pip install -e .`

2）配置 API 密钥（必需）

- `export AI_CMD_OPENROUTER_API_KEY=sk-...`
- 可选模型：`AI_CMD_OPENROUTER_MODEL`、`AI_CMD_OPENROUTER_MODEL_BACKUP`

3）运行一个提示

- `aicmd "递归列出所有文件"`

4）启用交互模式（可选）

- 运行 `aicmd --create-config`，然后在 `~/.ai-cmd/settings.json` 中将 `basic.interactive_mode` 设置为 `true`
- 或使用 `aicmd --show-config` 查看配置

命令速览
- 基本：`aicmd "<你的提示>"`
- 仅使用 API：`--force-api`
- 本次禁用交互：`--disable-interactive`
- 输出 JSON：`--json`
- 关闭剪贴板/颜色：`--no-clipboard`、`--no-color`
- 状态与维护：`--status`、`--reset-errors`、`--cleanup-cache`、`--recalculate-confidence`
- 配置相关：`--config`、`--show-config`、`--create-config`、`--create-config-force`、`--validate-config`、`--set-config KEY VALUE`
- 网络代理：`--base-url https://proxy.example/api/v1/chat/completions`

配置说明
- 位置（优先级从低到高，后写覆盖前写）
  - 用户配置：`~/.ai-cmd/settings.json`
  - 项目配置：`./.ai-cmd.json`
  - 环境变量（覆盖部分键）
  - 内置默认值

- 生成配置模板
  - `aicmd --create-config`（或使用 `--create-config-force` 覆盖）

- 查看与校验
  - `aicmd --show-config`
  - `aicmd --validate-config`

- 更新单个键
  - `aicmd --set-config interactive_mode true`

- 配置示例（节选）
```
{
  "version": "0.4.0",
  "basic": {
    "interactive_mode": true,
    "cache_enabled": true,
    "auto_copy_threshold": 1.0,
    "manual_confirmation_threshold": 0.7
  },
  "api": { "use_backup_model": false, "timeout_seconds": 30, "max_retries": 3 },
  "cache": { "cache_directory": "~/.ai-cmd", "database_file": "cache.db", "max_cache_age_days": 30, "cache_size_limit": 1000 },
  "interaction": { "interaction_timeout_seconds": 30, "positive_weight": 0.3, "negative_weight": 0.6, "similarity_threshold": 0.6, "confidence_threshold": 0.75 },
  "display": { "show_confidence": false, "show_source": false, "colored_output": true }
}
```

工作机制与流程
- 模式
  - 基础模式：`interactive_mode` 为 false，或使用 `--force-api`/`--disable-interactive`，直接调用 API 并复制命令（除非显式禁用）。
  - 交互模式：展示置信度/相似度，进行安全检查，并基于阈值询问确认，同时从你的反馈中学习。

- 缓存与学习
  - SQLite 数据库：`~/.ai-cmd/cache.db`（路径/文件名可配置）
  - 精确匹配时，基于确认/拒绝和时间衰减计算置信度
  - 无精确匹配时，会用相似度（Jaccard + 序列相似度）寻找可复用命令
  - 维护：`--cleanup-cache`（按 TTL/大小清理）、`--recalculate-confidence`（批量重算置信度）

- 安全检查
  - 检测潜在危险命令（如 `rm -rf`、`dd of=/dev/...` 等）
  - 对风险命令可强制确认并禁用自动复制

- JSON 输出
  - 使用 `--json` 输出：`{ command, source, confidence, similarity, dangerous, confirmed }`

环境变量
- 必需：`AI_CMD_OPENROUTER_API_KEY`
- 可选：`AI_CMD_OPENROUTER_MODEL`、`AI_CMD_OPENROUTER_MODEL_BACKUP`
- 可选调参（覆盖部分配置）：`AI_CMD_INTERACTIVE_MODE`、`AI_CMD_CONFIDENCE_THRESHOLD`、`AI_CMD_AUTO_COPY_THRESHOLD`、`AI_CMD_POSITIVE_WEIGHT`、`AI_CMD_NEGATIVE_WEIGHT`、`AI_CMD_SIMILARITY_THRESHOLD`、`AI_CMD_CACHE_ENABLED`、`AI_CMD_CACHE_SIZE_LIMIT`、`AI_CMD_CACHE_DIR`

问题排查
- “找不到 API key”：设置 `AI_CMD_OPENROUTER_API_KEY`
- “未指定模型”：设置 `AI_CMD_OPENROUTER_MODEL` 或在配置中启用备用模型
- “限流/超时”：客户端带重试；稍后再试或设置备用模型
- 缓存被禁用：执行 `aicmd --reset-errors`，并查看日志 `~/.ai-cmd/logs/`

开发
- 安装依赖：`uv sync`
- 本地运行：`uv run aicmd "列出所有文件"`
- 格式/检查：`uv run black src/`、`uv run flake8 src/`
- 测试：`uv run python -m pytest`

许可
- MIT。详见仓库。

