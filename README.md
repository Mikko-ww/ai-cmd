# ai-cmd

`ai-cmd` is a command-line tool that converts natural language prompts into shell commands using the OpenRouter API.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/ai-cmd.git
    cd ai-cmd
    ```

2.  **Install dependencies:**
    This project uses [uv](https://docs.astral.sh/uv/) for package management.
    ```bash
    uv sync
    ```

## Configuration

1.  **Create a `.env` file:**
    Copy the example file:
    ```bash
    cp .env.example .env
    ```

2.  **Add your API key:**
    Open the `.env` file and add your OpenRouter API key:
    ```
    AI_CMD_OPENROUTER_API_KEY="your_api_key_here"
    AI_CMD_OPENROUTER_MODEL="google/gemma-3-12b-it:free"
    ```

## Usage

Run the tool with your natural language prompt:

```bash
aicmd list all files in the current directory
```

The tool will output the corresponding shell command and copy it to your clipboard.
