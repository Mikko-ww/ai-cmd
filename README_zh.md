# ai-cmd

`ai-cmd` 是一个命令行工具，它使用 OpenRouter API 将自然语言提示转换为 shell 命令。

## 安装

1.  **克隆仓库：**
    ```bash
    git clone https://github.com/your-username/ai-cmd.git
    cd ai-cmd
    ```

2.  **安装依赖：**
    本项目使用 [Rye](https://rye-up.com/) 进行包管理。
    ```bash
    rye sync
    ```

## 配置

1.  **创建 `.env` 文件：**
    复制示例文件：
    ```bash
    cp .env.example .env
    ```

2.  **添加您的 API 密钥：**
    打开 `.env` 文件并添加您的 OpenRouter API 密钥：
    ```
    AI_CMD_OPENROUTER_API_KEY="your_api_key_here"
    AI_CMD_OPENROUTER_MODEL="google/gemma-3-12b-it:free"
    ```

## 使用

使用您的自然语言提示运行该工具：

```bash
aicmd 列出当前目录中的所有文件
```

该工具将输出相应的 shell 命令并将其复制到剪贴板。
