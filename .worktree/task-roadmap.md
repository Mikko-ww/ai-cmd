# AI-CMD 优化任务路线图

> 文档创建时间：2026-01-30
> 预计周期：4-6 周（兼职开发）

---

## 📋 任务总览

| 阶段 | 任务数 | 预计工时 | 状态 |
|------|--------|----------|------|
| Phase 1: 测试补全 | 5 | 10-14h | 🔲 未开始 |
| Phase 2: 架构重构 | 4 | 12-16h | 🔲 未开始 |
| Phase 3: 性能优化 | 3 | 6-8h | ✅ 已完成 |
| Phase 4: 功能增强 | 4 | 8-12h | 🔲 未开始 |
| Phase 5: 工程化 | 3 | 4-6h | 🔲 未开始 |

---

## 🔴 Phase 1: 测试补全（高优先级）

> 目标：将测试覆盖率提升至 80%+

### Task 1.1: LLM 提供商测试
- **文件**：`tests/test_llm_providers.py`
- **预计工时**：3-4h
- **依赖**：无
- **验收标准**：
  - [ ] 覆盖 6 个提供商的基本功能
  - [ ] Mock HTTP 请求，不依赖真实 API
  - [ ] 测试异常处理（超时、认证失败、限流）

### Task 1.2: Keyring Manager 测试
- **文件**：`tests/test_keyring_manager.py`
- **预计工时**：2h
- **依赖**：无
- **验收标准**：
  - [ ] 使用 `AICMD_KEYRING_SERVICE="com.aicmd.ww.test"` 隔离
  - [ ] 测试 CRUD 操作
  - [ ] 测试边界情况（空 key、无效 provider）

### Task 1.3: Interactive Manager 测试
- **文件**：`tests/test_interactive_manager.py`
- **预计工时**：2-3h
- **依赖**：无
- **验收标准**：
  - [ ] Mock 用户输入
  - [ ] 测试超时处理
  - [ ] 测试颜色输出逻辑
  - [ ] 测试统计信息

### Task 1.4: Prompts 模块测试
- **文件**：`tests/test_prompts.py`
- **预计工时**：1h
- **依赖**：无
- **验收标准**：
  - [ ] 测试 `get_system_prompt()` 各类型
  - [ ] 验证提示词内容完整性

### Task 1.5: 集成测试完善
- **文件**：`tests/test_integration.py`
- **预计工时**：3-4h
- **依赖**：Task 1.1-1.4
- **验收标准**：
  - [ ] 端到端流程测试
  - [ ] 多提供商切换测试
  - [ ] 缓存命中/未命中测试

---

## 🟠 Phase 2: 架构重构（高优先级）

> 目标：降低 ai.py 复杂度，提高可维护性

### Task 2.1: 提取 ClipboardManager
- **新建文件**：`src/aicmd/clipboard_manager.py`
- **预计工时**：2h
- **依赖**：无
- **变更范围**：
  - [ ] 创建 `ClipboardManager` 类
  - [ ] 统一剪贴板复制逻辑
  - [ ] 更新 `ai.py` 调用方式
- **验收标准**：
  - [ ] 原有功能不变
  - [ ] `ai.py` 剪贴板相关代码减少 80%+

### Task 2.2: 提取 CommandHandler
- **新建文件**：`src/aicmd/command_handler.py`
- **预计工时**：4-6h
- **依赖**：Task 2.1
- **变更范围**：
  - [ ] 提取 `get_shell_command()` 核心逻辑
  - [ ] 提取 `get_shell_command_original()`
  - [ ] 保持 `ai.py` 仅作为入口
- **验收标准**：
  - [ ] `ai.py` 行数减少至 400 行以下
  - [ ] 所有测试通过
  - [ ] CLI 行为不变

### Task 2.3: CLI 命令分组
- **新建目录**：`src/aicmd/cli_commands/`
- **预计工时**：3-4h
- **依赖**：Task 2.2
- **变更范围**：
  - [ ] `config_commands.py`: 配置管理命令
  - [ ] `cache_commands.py`: 缓存管理命令
  - [ ] `provider_commands.py`: 提供商管理命令
- **验收标准**：
  - [ ] 每个命令文件独立
  - [ ] `ai.py` 仅剩入口和路由逻辑

### Task 2.4: LLM 提供商去重
- **文件**：`src/aicmd/llm_providers.py`
- **预计工时**：2-3h
- **依赖**：Task 1.1（需要测试保障）
- **变更范围**：
  - [ ] 创建 `OpenAICompatibleProvider` 基类
  - [ ] 简化 4 个兼容提供商的实现
  - [ ] 保留 `GeminiProvider` 和 `QwenProvider` 特殊逻辑
- **验收标准**：
  - [ ] 代码行数减少 30%+
  - [ ] 所有提供商测试通过

---

## 🟡 Phase 3: 性能优化（中优先级）

> 目标：优化大缓存场景下的查询性能

### Task 3.1: 数据库索引优化
- **文件**：`src/aicmd/database_manager.py`
- **预计工时**：2h
- **依赖**：无
- **变更范围**：
  - [ ] 添加 `last_used` 索引
  - [ ] 添加 `query_hash` 索引
  - [ ] 实现分页查询方法
- **验收标准**：
  - [ ] 1000 条缓存下查询时间 < 50ms

### Task 3.2: 相似度计算优化
- **文件**：`src/aicmd/query_matcher.py`
- **预计工时**：3-4h
- **依赖**：无
- **变更范围**：
  - [ ] 添加预计算缓存
  - [ ] 实现快速过滤算法
  - [ ] 可选：引入 MinHash LSH
- **验收标准**：
  - [ ] 500 条缓存下相似度计算时间减少 50%+

### Task 3.3: 配置加载优化
- **文件**：`src/aicmd/ai.py`, `src/aicmd/config_manager.py`
- **预计工时**：1-2h
- **依赖**：Task 2.2
- **变更范围**：
  - [ ] `ConfigManager` 支持单例模式
  - [ ] 入口处统一创建，依赖注入
- **验收标准**：
  - [ ] 单次请求配置加载次数 = 1

---

## 🟢 Phase 4: 功能增强（低优先级）

> 目标：提升用户体验

### Task 4.1: --explain 命令解释模式
- **文件**：
  - `src/aicmd/prompts.py`
  - `src/aicmd/ai.py`
- **预计工时**：2-3h
- **依赖**：Phase 2 完成
- **验收标准**：
  - [ ] `aicmd "xxx" --explain` 返回命令 + 解释
  - [ ] 解释内容有意义

### Task 4.2: --history 历史记录
- **文件**：
  - `src/aicmd/cache_manager.py`
  - `src/aicmd/ai.py`
- **预计工时**：2-3h
- **依赖**：无
- **验收标准**：
  - [ ] `aicmd --history` 显示最近 10 条
  - [ ] `aicmd --history -n 20` 自定义数量
  - [ ] `aicmd --history --search "xxx"` 搜索

### Task 4.3: 提示词模板扩展
- **文件**：`src/aicmd/prompts.py`
- **预计工时**：2h
- **依赖**：无
- **验收标准**：
  - [ ] 添加 `explain`, `debug`, `alternative` 模板
  - [ ] `get_system_prompt()` 支持新类型

### Task 4.4: 流式输出支持
- **文件**：`src/aicmd/llm_providers.py`
- **预计工时**：3-4h
- **依赖**：无
- **验收标准**：
  - [ ] 支持 `--stream` 参数
  - [ ] 至少 OpenAI 提供商支持流式

---

## 🔵 Phase 5: 工程化（低优先级）

> 目标：提升代码质量和开发效率

### Task 5.1: 类型提示完善
- **预计工时**：2h
- **变更范围**：
  - [ ] 添加 `mypy` 依赖
  - [ ] 为核心模块添加类型提示
  - [ ] 创建 `py.typed` 标记
- **验收标准**：
  - [ ] `mypy src/aicmd/` 无错误

### Task 5.2: Pre-commit 钩子
- **预计工时**：1h
- **变更范围**：
  - [ ] 创建 `.pre-commit-config.yaml`
  - [ ] 配置 black, flake8, isort
- **验收标准**：
  - [ ] `pre-commit run --all-files` 通过

### Task 5.3: CI/CD 配置
- **文件**：`.github/workflows/test.yml`
- **预计工时**：1-2h
- **依赖**：Phase 1 完成
- **验收标准**：
  - [ ] Push 触发测试
  - [ ] 测试覆盖率报告

---

## 📅 建议执行顺序

```
Week 1-2: Phase 1 (测试补全)
    └── 保障后续重构安全性

Week 3-4: Phase 2 (架构重构)
    └── Task 2.1 → 2.2 → 2.3 → 2.4

Week 5: Phase 3 (性能优化)
    └── 可并行执行

Week 6+: Phase 4 & 5 (功能增强 & 工程化)
    └── 按需选择
```

---

## 📊 进度追踪

### Phase 1 进度

| 任务 | 状态 | 开始日期 | 完成日期 |
|------|------|----------|----------|
| Task 1.1 LLM 提供商测试 | 🔲 | - | - |
| Task 1.2 Keyring Manager 测试 | 🔲 | - | - |
| Task 1.3 Interactive Manager 测试 | 🔲 | - | - |
| Task 1.4 Prompts 模块测试 | 🔲 | - | - |
| Task 1.5 集成测试完善 | 🔲 | - | - |

### Phase 2 进度

| 任务 | 状态 | 开始日期 | 完成日期 |
|------|------|----------|----------|
| Task 2.1 提取 ClipboardManager | 🔲 | - | - |
| Task 2.2 提取 CommandHandler | 🔲 | - | - |
| Task 2.3 CLI 命令分组 | 🔲 | - | - |
| Task 2.4 LLM 提供商去重 | 🔲 | - | - |

### Phase 3 进度

| 任务 | 状态 | 开始日期 | 完成日期 |
|------|------|----------|----------|
| Task 3.1 数据库索引优化 | ✅ | 2026-01-31 | 2026-01-31 |
| Task 3.2 相似度计算优化 | ✅ | 2026-01-31 | 2026-01-31 |
| Task 3.3 配置加载优化 | ✅ | 2026-01-31 | 2026-01-31 |

### Phase 4 进度

| 任务 | 状态 | 开始日期 | 完成日期 |
|------|------|----------|----------|
| Task 4.1 --explain 模式 | 🔲 | - | - |
| Task 4.2 --history 历史 | 🔲 | - | - |
| Task 4.3 提示词扩展 | 🔲 | - | - |
| Task 4.4 流式输出 | 🔲 | - | - |

### Phase 5 进度

| 任务 | 状态 | 开始日期 | 完成日期 |
|------|------|----------|----------|
| Task 5.1 类型提示 | 🔲 | - | - |
| Task 5.2 Pre-commit | 🔲 | - | - |
| Task 5.3 CI/CD | 🔲 | - | - |

---

## 📝 状态图例

- 🔲 未开始
- 🔄 进行中
- ✅ 已完成
- ⏸️ 暂停
- ❌ 取消
