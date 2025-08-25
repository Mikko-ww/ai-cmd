# 项目优化方案与实施计划

> 基于当前代码（v0.3.0）与文档梳理形成，按优先级推进，确保在不破坏既有功能的前提下提升稳定性、可维护性与可扩展性。

## 优先级路线图
- P0（立即修复）
  - 修复 `src/aicmd/confidence_calculator.py` 末尾未完成的函数 `recalculate_all_confidence`（导入失败风险）。
  - 统一默认值：`negative_weight`（`ConfigManager`=0.6 vs `ConfidenceCalculator`=0.5），以配置为准或文档一致。
  - 明确/移除未使用的 `manual_confirmation_threshold`，避免误导。
- P1（稳定性与结构）
  - 抽离 API 客户端为 `src/aicmd/api_client.py`（建议 `httpx`），集中处理超时、重试与错误分类。
  - 日志统一到标准 `logging`（旋转文件 + 控制台），配置可覆盖日志路径与级别。
  - 交互层跨平台超时（替代仅 Unix 的 SIGALRM），新增 `--no-color`、`--no-clipboard` 开关。
  - 危险命令防护：识别高风险模式（如 `rm -rf`），强制人工确认并禁用自动复制。
- P2（可扩展与体验）
  - 缓存 TTL：按 `max_cache_age_days` 淘汰，新增 `created_at` 相关索引。
  - 可选哈希策略：`hash_strategy: simple|normalized`，减少同义表达重复缓存。
  - 维护命令：完成 `recalculate_all_confidence()` 并提供 `aicmd --recalculate-confidence`。
  - 机器可读输出：`aicmd --json` 返回 `{command, source, confidence, similarity}`。
  - 配置管理增强：恢复 `--set-config <key> <value>`，新增 `--base-url` 兼容代理。

## 实施细节（要点与验收）
- 语法与配置一致性（P0）
  - 修改/完成 `recalculate_all_confidence`；单测覆盖导入与基本路径执行。
  - 对齐 `negative_weight` 默认值；更新 `README/USAGE` 与 `setting_template.json`。
  - 若保留 `manual_confirmation_threshold`：在 `InteractiveManager` 中落地逻辑；否则从模板与校验移除。
- 架构与可靠性（P1）
  - `api_client.py`：封装 `send_chat(prompt, model, timeout)`；集中重试与异常到统一错误类型；`ai.py` 中仅聚合与回退。
  - 日志：使用 `logging` + `RotatingFileHandler`（默认 `~/.ai-cmd/logs/`），自定义颜色仅用于 CLI 友好输出。
  - 交互：用线程/定时器实现跨平台超时；`--no-color`、`--no-clipboard` 控制显示与复制。
  - 风险防护：提供可配置的危险正则清单，触发强制确认；在 `--json` 模式输出 `dangerous: true`。
- 缓存与置信度（P2）
  - TTL 清理：写入与启动时机执行；`created_at` 索引支持高效清理；打印清理数量。
  - 哈希策略：默认 `simple`（兼容）；`normalized` 通过 `QueryMatcher.normalize_query` 参与哈希；配置可切换。
  - 置信度维护：实现批量重算；在 `--status` 展示平均置信度与分布（已有基础）。
- CLI 与集成（P2）
  - `--json` 输出：标准化字段与错误结构；`--status` 增加 DB 路径、大小、最近 N 条反馈摘要。
  - 配置设置：校验 key 与类型，失败时返回清晰提示，支持嵌套（如 `cache.cache_size_limit`）。

## 测试与质量
- 单测（pytest）
  - 覆盖：`hash_utils`、`query_matcher`、`config_manager.validate_config`、`database/cache`（临时目录）、`ConfidenceCalculator.calculate_confidence`（含时间衰减）、API 客户端（mock 传输）。
  - 交互层：模拟超时/确认/拒绝分支；危险命令策略。
- 工具链
  - 引入 `ruff`（替代 flake8，含 isort 规则）与 `mypy`；保留 `black`。
  - 预提交：`.pre-commit-config.yaml` 集成 black/ruff/mypy 基础门槛。

## CI/CD 与文档
- GitHub Actions：在 py3.9-3.12 运行 black/ruff/mypy/pytest；缓存 `uv` 依赖；PR 必须绿灯。
- 文档同步：更新 `USAGE.md` 与 `README.md`，新增参数说明（`--json`、`--no-color`、`--no-clipboard`、维护命令）。

## 可扩展项
- 同义词扩展：支持在用户配置中自定义 `synonyms` 并合并到 `QueryMatcher`。
- 指标可观测：在 `--status` 输出更细粒度的错误分布与近期交互摘要。

## 里程碑与时间预估
- M1（1–2 天）：P0 全量修复 + 基础单测绿灯。
- M2（3–5 天）：P1 架构拆分、日志统一、交互跨平台、风险防护 + 文档。
- M3（3–5 天）：P2 功能完成（TTL、哈希策略、--json、配置设置）+ CI 完整流水线。

## 回滚策略
- 按模块拆分提交与小步发布；新功能默认关闭（配置开关）。
- 保持兼容路径（默认 `simple` 哈希；`logger` 输出不改变用户体验）。
- 任一模块异常可通过 `GracefulDegradationManager` 回退到安全路径。

---
如需，我可先提交 M1 改动（修复语法/配置一致性 + 基础单测）并开 PR。
