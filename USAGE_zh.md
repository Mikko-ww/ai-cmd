# aicmd – 使用指南

本指南详细说明如何有效使用 aicmd：选项、工作流程、配置、缓存行为和安全性。

快速开始
- 使用 uv 安装
  - `uv sync`
  - `uv pip install -e .`
- 配置 API 密钥
  - `aicmd --create-config` 生成 `~/.ai-cmd/settings.json`
  - 安全设置 API 密钥：`aicmd --set-api-key <提供商> <你的API密钥>`
  - 示例：`aicmd --set-api-key openrouter sk-or-v1-...`
- 首次运行
  - `aicmd "list all files"`
  - 如需要，在设置中启用交互模式

基本用法
- `aicmd "<提示>"` 将您的提示转换为 shell 命令。
- 支持多词提示；建议使用引号。
- 默认情况下，如果禁用交互模式，命令会被打印并复制到剪贴板（除非使用 `--no-clipboard`）。

CLI 选项
- `-v, --version`：显示版本信息。
- `--config`：显示当前配置摘要。
- `--show-config`：显示详细配置及其来源。
- `--create-config`：在 `~/.ai-cmd/settings.json` 创建用户配置文件。
- `--create-config-force`：创建（覆盖）用户配置文件。
- `--validate-config`：验证当前配置值和范围。
- `--set-config KEY VALUE`：更新配置键（例如 `--set-config interactive_mode true`）。
- `--force-api`：强制进行新的 API 调用（绕过缓存和交互流程）。
- `--disable-interactive`：为此次运行禁用交互模式。
- `--status`：显示缓存和交互统计信息。
- `--reset-errors`：重置内部错误状态，如果缓存被禁用则重新启用。
- `--no-color`：禁用彩色输出。
- `--no-clipboard`：不将结果复制到剪贴板。
- `--recalculate-confidence`：重新计算所有缓存条目的置信度分数。
- `--json`：输出 JSON 对象而不是纯文本。
- `--base-url URL`：覆盖 API 基础 URL（对代理有用）。
- `--cleanup-cache`：清理过期/超大的缓存条目（TTL 和大小限制）。

API 密钥管理
- `--set-api-key 提供商 密钥`：为提供商设置 API 密钥（安全存储在系统密钥环中）。
- `--get-api-key 提供商`：检查提供商是否已配置 API 密钥（显示掩码预览）。
- `--delete-api-key 提供商`：从密钥环中删除提供商的 API 密钥。
- `--list-api-keys`：列出所有已配置 API 密钥的提供商。

提供商管理
- `--list-providers`：列出所有支持的 LLM 提供商及当前默认提供商。
- `--test-provider 提供商`：测试指定提供商的配置（验证配置并测试 API 连接）。

交互模式 vs 基本模式
- 基本模式
  - 当 `interactive_mode` 为 false 或使用 `--force-api`/`--disable-interactive` 时激活。
  - 直接调用 API 并打印命令，除非被禁用或被认为不安全，否则复制到剪贴板。
- 交互模式
  - 通过在配置中设置 `basic.interactive_mode: true` 启用。
  - 在可用时显示置信度和相似性指标。
  - 执行安全检查，可能强制确认或禁用危险命令的自动复制。
  - 基于阈值要求确认：`confidence_threshold`、`manual_confirmation_threshold`、`auto_copy_threshold`。

JSON 输出
- 使用 `--json` 接收结构化输出：
```
{
  "command": "ls -la",
  "source": "API | Cache | Similar Cache | FALLBACK",
  "confidence": 0.83,
  "similarity": 0.92,
  "dangerous": false,
  "confirmed": true
}
```

配置
- 来源和优先级
  - 用户文件：`~/.ai-cmd/settings.json`
  - 项目文件：`./.ai-cmd.json`
  - 内置默认值填充其余部分。
- 创建模板：`aicmd --create-config`（或 `--create-config-force`）
- 检查：`aicmd --show-config`
- 验证：`aicmd --validate-config`
- 更新：`aicmd --set-config KEY VALUE`
- 关键配置项（完整结构见 README）
  - `basic`：`interactive_mode`、`cache_enabled`，阈值：`auto_copy_threshold`、`manual_confirmation_threshold`
  - `api`：`timeout_seconds`、`max_retries`、`default_provider`
  - `providers`：为 OpenRouter、OpenAI、DeepSeek、xAI、Gemini、Qwen 配置模型和基础 URL（API 密钥存储在密钥环中）
  - `cache`：`cache_directory`、`database_file`、`max_cache_age_days`、`cache_size_limit`
  - `interaction`：`interaction_timeout_seconds`、`positive_weight`、`negative_weight`、`similarity_threshold`、`confidence_threshold`
  - `display`：`colored_output`、`show_confidence`、`show_source`

缓存和置信度
- 存储：默认在 `~/.ai-cmd/cache.db` 的 SQLite（可配置路径和文件）。
- 精确匹配：置信度根据确认/拒绝情况计算，带有时间衰减。
- 相似匹配：Jaccard + 序列相似性；如果高于 `similarity_threshold` 则考虑最佳匹配。
- 阈值逻辑
  - `auto_copy_threshold`：达到或超过此置信度时自动复制，除非安全性阻止。
  - `manual_confirmation_threshold`：需要明确确认的置信度范围。
  - `confidence_threshold`：使用缓存 vs 调用 API 的最低置信度。
- 维护
  - `aicmd --cleanup-cache`（通过 `max_cache_age_days` 的 TTL 和通过 `cache_size_limit` 的大小）。
  - `aicmd --recalculate-confidence` 批量重新计算分数。

安全性
- 检测危险模式（`rm -rf`、`dd of=/dev/...`、文件系统格式化、批量删除等）。
- 可能强制确认并禁用危险命令的自动剪贴板复制。
- 运行命令前请务必检查。

API 密钥管理
- 为提供商设置 API 密钥
  - `aicmd --set-api-key openrouter sk-or-v1-your-key-here`
  - `aicmd --set-api-key openai sk-your-openai-key`
- 检查已配置的 API 密钥
  - `aicmd --list-api-keys`（显示所有有密钥的提供商）
  - `aicmd --get-api-key openrouter`（显示掩码预览）
- 删除 API 密钥
  - `aicmd --delete-api-key openrouter`

提供商管理
- 列出支持的提供商
  - `aicmd --list-providers`
- 测试提供商配置
  - `aicmd --test-provider openrouter`（验证配置并测试 API）
- 设置默认提供商
  - `aicmd --set-config default_provider openai`
- 配置提供商模型
  - `aicmd --set-config providers.openai.model gpt-4`

示例
- 强制获取新结果和 JSON 输出
  - `aicmd "show open ports" --force-api --json`
- 在脚本中非交互式工作
  - `aicmd "list large files" --disable-interactive --no-clipboard`
- 使用代理基础 URL
  - `aicmd "download file" --base-url https://proxy.example/api/v1/chat/completions`
- 设置新提供商
  - `aicmd --set-api-key deepseek your-deepseek-key`
  - `aicmd --set-config default_provider deepseek`
  - `aicmd --test-provider deepseek`

故障排除
- 缺少 API 密钥：使用 `aicmd --set-api-key <提供商> <密钥>` 将 API 密钥安全存储在系统密钥环中。
- 未配置模型：使用 `aicmd --set-config providers.<提供商>.model <模型名称>` 设置模型。
- 速率限制/超时：启用了自动重试；稍后重试或配置备用提供商。
- 错误后缓存被禁用：`aicmd --reset-errors` 并检查 `~/.ai-cmd/logs/` 下的日志。
- 提供商问题：使用 `aicmd --test-provider <提供商>` 诊断配置问题。
- 配置验证：使用 `aicmd --validate-config` 检查配置问题。