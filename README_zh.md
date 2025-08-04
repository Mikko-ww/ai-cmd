# AI 命令行工具

`ai-cmd` 是一个智能命令行工具，使用 OpenRouter API 将自然语言提示转换为 shell 命令。具备先进的缓存系统、用户交互功能和灵活的配置选项，旨在提升您的工作效率，同时保证安全性和可靠性。

## ✨ 特性

- 🧠 **AI 驱动的命令生成**：使用最先进的 AI 模型将自然语言转换为 shell 命令
- 🚀 **智能缓存系统**：基于置信度的智能命令缓存  
- 🔄 **交互模式**：用户确认系统增强安全性
- ⚙️ **灵活配置**：支持 JSON 文件和环境变量的多层配置
- 📊 **统计分析**：详细的使用统计和性能指标
- 🛡️ **错误恢复**：优雅降级和错误恢复机制
- 📋 **自动剪贴板**：自动剪贴板集成，流畅的工作流程

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/Mikko-ww/ai-cmd.git
cd ai-cmd

# 安装依赖（需要 uv）
uv sync

# 安装工具
uv pip install -e .
```

### 配置

1. **设置 API 密钥：**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件并添加您的 OpenRouter API 密钥
   ```

2. **创建用户配置（可选）：**
   ```bash
   aicmd --create-config
   ```

### 基本使用

```bash
# 生成命令
aicmd "列出当前目录中的所有文件"

# 强制 API 调用（绕过缓存）
aicmd "创建新目录" --force-api

# 禁用交互模式以用于自动化
aicmd "检查磁盘使用情况" --disable-interactive
```

## 📖 文档

### 命令行选项

| 选项 | 描述 |
|------|------|
| `-h, --help` | 显示帮助信息并退出 |
| `-v, --version` | 显示版本信息 |
| `--config` | 显示当前配置 |
| `--show-config` | 显示详细配置摘要 |
| `--create-config` | 创建用户配置文件 |
| `--validate-config` | 验证当前配置 |
| `--force-api` | 强制 API 调用，绕过缓存 |
| `--disable-interactive` | 禁用交互模式 |
| `--stats` | 显示缓存和交互统计 |
| `--reset-errors` | 重置错误状态 |

### 配置系统

`ai-cmd` 支持多层配置，优先级顺序如下：

1. **环境变量**（最高优先级）
2. **JSON 配置文件**
3. **默认值**（备用）

#### 配置文件位置

- 用户配置：`~/.ai-cmd/settings.json`
- 项目配置：`.ai-cmd.json`（在当前目录）

#### 配置选项

```json
{
  "basic": {
    "interactive_mode": false,
    "cache_enabled": true,
    "auto_copy_threshold": 0.9,
    "manual_confirmation_threshold": 0.8
  },
  "api": {
    "timeout_seconds": 30,
    "max_retries": 3
  },
  "cache": {
    "cache_directory": "~/.ai-cmd",
    "database_file": "ai_cmd_cache.db",
    "max_cache_age_days": 30,
    "cache_size_limit": 1000
  },
  "interaction": {
    "interaction_timeout_seconds": 10,
    "positive_weight": 0.2,
    "negative_weight": 0.6,
    "similarity_threshold": 0.7,
    "confidence_threshold": 0.8
  },
  "display": {
    "show_confidence": false,
    "show_source": false,
    "colored_output": true
  }
}
```

### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `AI_CMD_OPENROUTER_API_KEY` | OpenRouter API 密钥 | 必需 |
| `AI_CMD_OPENROUTER_MODEL` | 使用的 AI 模型 | `google/gemma-3-27b-it:free` |
| `AI_CMD_INTERACTIVE_MODE` | 启用交互模式 | `false` |
| `AI_CMD_CACHE_ENABLED` | 启用缓存 | `true` |
| `AI_CMD_AUTO_COPY_THRESHOLD` | 自动复制置信度阈值 | `0.9` |
| `AI_CMD_CONFIDENCE_THRESHOLD` | 手动确认阈值 | `0.8` |

## 🔧 高级功能

### 智能缓存

工具维护命令翻译的本地缓存，具有置信度评分：

- **高置信度（≥0.9）**：命令自动复制到剪贴板
- **中等置信度（0.8-0.9）**：交互模式下需要用户确认
- **低置信度（<0.8）**：始终需要确认或 API 调用

### 交互模式

启用时，交互模式提供：
- 生成命令的用户确认
- 反馈收集以改进未来建议
- 潜在危险操作的安全提示

### 统计和监控

```bash
# 查看详细统计
aicmd --stats

# 查看配置状态
aicmd --show-config

# 验证配置
aicmd --validate-config
```

## 🛠️ 开发

### 要求

- Python 3.9+
- [uv](https://docs.astral.sh/uv/) 用于包管理

### 设置

```bash
# 安装开发依赖
uv sync

# 运行代码检查
uv run black src/
uv run flake8 src/

# 运行测试
uv run python -m pytest
```

### 项目结构

```
ai-cmd/
├── src/aicmd/              # 主包
│   ├── ai.py              # 核心功能
│   ├── config_manager.py  # 配置管理
│   ├── cache_manager.py   # 缓存系统
│   ├── interactive_manager.py  # 用户交互
│   ├── setting_template.json   # 配置模板
│   └── ...
├── pyproject.toml         # 项目配置
└── README.md             # 此文件
```

## 🤝 贡献

1. Fork 仓库
2. 创建功能分支：`git checkout -b feature-name`
3. 进行更改并添加测试
4. 运行测试套件：`uv run python -m pytest`
5. 提交 pull request

## 📄 许可证

此项目在 MIT 许可证下授权 - 有关详细信息，请参阅 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- OpenRouter 提供 AI 模型访问
- 开源社区的灵感和工具

## 🔗 链接

- **GitHub**: [https://github.com/Mikko-ww/ai-cmd](https://github.com/Mikko-ww/ai-cmd)
- **问题反馈**: [https://github.com/Mikko-ww/ai-cmd/issues](https://github.com/Mikko-ww/ai-cmd/issues)
- **文档**: [README.md](README.md)
