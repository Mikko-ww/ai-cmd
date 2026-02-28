# 任务总结：创建项目 Copilot Instructions

## 任务目标
深度阅读 ai-cmd 项目全部源码，提炼项目编码模式和约定，创建结构化的 `.instructions.md` 文件，指导 AI Agent 按照项目规范编写代码。

## 实施过程
1. 加载 `agent-customization` Skill，理解 instructions 文件的最佳实践（一个关注点一个文件、关键字丰富的 description、精确的 applyTo 模式）
2. 通过子代理深度探索项目所有源文件（20+ 个模块），分析 10 个维度的编码模式
3. 审查现有 instructions 文件（仅有 `copilot-task-record.instructions.md`），确定缺口
4. 按照"一个关注点一个文件"原则，创建 6 个聚焦的 instructions 文件

## 创建的文件
| 文件 | 触发方式 | 覆盖内容 |
|------|----------|----------|
| `python-coding-style.instructions.md` | `applyTo: **/*.py` | 命名、导入、类型标注、文档字符串、日志规范 |
| `error-handling.instructions.md` | `applyTo` + `description` | GracefulDegradationManager 模式、异常层次、try/except 规范 |
| `testing-guidelines.instructions.md` | `applyTo: tests/**/*.py` | Keyring 隔离、Fixtures、Mock 模式、测试脚本位置 |
| `security-rules.instructions.md` | `applyTo` + `description` | Keyring API Key 管理、危险命令检测、安全编码 |
| `llm-provider-development.instructions.md` | `description` 按需发现 | 提供商架构、添加新提供商步骤、关键约束 |
| `config-system.instructions.md` | `description` 按需发现 | 配置优先级、单例模式、添加配置项清单 |

## 结果
共创建 6 个 instructions 文件，加上原有的 1 个，项目现有 7 个 instructions 文件，覆盖了项目的核心编码规范和架构模式。
