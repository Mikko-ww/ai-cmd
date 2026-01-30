# AI Command Line Tool - AI Agent Instructions

## Project Architecture

智能 CLI 工具：将自然语言转换为 shell 命令，支持 6 个 LLM 提供商（openrouter/openai/deepseek/xai/gemini/qwen），具备缓存、置信度评分和用户交互功能。

### 核心架构模式
- **优雅降级**：所有增强功能（缓存、置信度、交互）包装在 `get_shell_command_original()` 周围，任何失败自动降级到基础模式
- **多层配置**：CLI 参数 > 环境变量 `AI_CMD_*` > JSON 配置 > 默认值
- **多提供商路由**：`LLMRouter` → `LLMProvider` 抽象基类 → 具体提供商实现

### 关键组件

| 文件 | 职责 |
|------|------|
| [ai.py](src/aicmd/ai.py) | CLI 入口、主编排流程 |
| [llm_providers.py](src/aicmd/llm_providers.py) | 6 个 LLM 提供商实现 |
| [llm_router.py](src/aicmd/llm_router.py) | 提供商路由与回退 |
| [keyring_manager.py](src/aicmd/keyring_manager.py) | API Key 系统级安全存储 |
| [config_manager.py](src/aicmd/config_manager.py) | 多源配置加载 |
| [error_handler.py](src/aicmd/error_handler.py) | `GracefulDegradationManager` 错误管理 |

### API Key 管理（安全关键）
- **必须使用 keyring**：`aicmd --set-api-key <provider> <key>` 存入系统钥匙串
- **配置文件 `api_key` 已废弃**：仅保留 `model`/`base_url` 字段
- **服务名隔离**：通过 `AICMD_KEYRING_SERVICE` 环境变量切换（测试用 `com.aicmd.ww.test`）

## Development Commands

```bash
uv sync                                    # 安装依赖
uv pip install -e .                        # 可编辑安装
uv run python -m pytest                    # 运行测试
uv run black src/ && uv run flake8 src/    # 格式化 + lint
```

### 调试命令
```bash
aicmd --list-providers                # 查看支持的提供商
aicmd --test-provider openai          # 测试提供商配置
aicmd --show-config                   # 查看生效配置
aicmd --status                        # 缓存/置信度统计
aicmd "list files" --force-api        # 绕过缓存测试 API
```

## 测试规范

- 框架：`pytest`，测试文件在 `tests/test_*.py`
- **Keyring 隔离必须**：`conftest.py` 设置 `AICMD_KEYRING_SERVICE="com.aicmd.ww.test"`
- Mock 对象：使用 `mock_config_manager`、`mock_database_manager`、`mock_cache_manager` fixture
- 脚本位置：测试脚本放 `./tmp/` 目录，禁止使用 `/tmp/`

## 项目特定模式

### 错误处理
- 所有增强功能使用 `GracefulDegradationManager.with_cache_fallback()`
- 异常层级见 [exceptions.py](src/aicmd/exceptions.py)：`AICmdException` → 分类子异常
- 错误计数超限（默认 3）自动禁用缓存

### 安全系统
- `CommandSafetyChecker` 与置信度评分集成
- 危险命令强制确认，即使高置信度

### 配置阈值
| 配置项 | 默认值 | 作用 |
|--------|--------|------|
| `auto_copy_threshold` | 0.9 | 高置信度自动复制 |
| `confidence_threshold` | 0.8 | 使用缓存最低置信度 |
| `similarity_threshold` | 0.7 | 模糊匹配截断 |

## 关键参考文件

- [setting_template.json](src/aicmd/setting_template.json)：完整配置结构（版本 1.0.2）
- [AGENTS.md](AGENTS.md)：开发规范与工作流详情
- [conftest.py](tests/conftest.py)：测试 fixture 模式