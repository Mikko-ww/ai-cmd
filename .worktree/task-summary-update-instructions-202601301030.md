# 任务摘要：更新 AI Agent Instructions

## 任务目标
根据项目最新架构变更，深度更新 `.github/copilot-instructions.md` 和 `AGENTS.md` 文件。

## 实施过程

1. **代码库调研**：通过 subagent 深入研究 `ai.py`、`llm_providers.py`、`llm_router.py`、`keyring_manager.py`、`config_manager.py`、`error_handler.py`、`conftest.py` 等核心文件

2. **发现的关键架构变更**：
   - 多提供商 LLM 系统：从单一 OpenRouter 扩展到 6 个提供商（openrouter/openai/deepseek/xai/gemini/qwen）
   - API Key 安全存储：从配置文件迁移到系统 keyring
   - 新增 CLI 命令：`--set-api-key`、`--list-providers`、`--test-provider` 等
   - 完整测试套件：pytest 框架，含 fixture 和测试标记

3. **更新内容**：
   - **copilot-instructions.md**：全面重写，添加多提供商架构、API Key 管理、测试规范、调试命令等
   - **AGENTS.md**：补充 Multi-Provider LLM Commands、测试 fixtures、测试标记

## 结果

两个文件已更新，更准确地反映项目当前状态：
- 中文化描述（符合项目 commit 历史风格）
- 添加完整的 CLI 命令参考
- 明确 Keyring 隔离测试规范
- 链接关键参考文件
