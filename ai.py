import os
import requests
import sys
import pyperclip
from dotenv import load_dotenv
from error_handler import GracefulDegradationManager

load_dotenv()

# 全局错误处理管理器
degradation_manager = GracefulDegradationManager()


def get_shell_command(prompt):
    """获取shell命令，集成错误处理和缓存功能"""

    def main_api_operation():
        api_key = os.getenv("AI_CMD_OPENROUTER_API_KEY")
        if not api_key:
            print("Error: AI_CMD_OPENROUTER_API_KEY not found in .env file.")
            return None
        model_name = os.getenv("AI_CMD_OPENROUTER_MODEL")

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that provides shell commands based on a user's natural language prompt. Only provide the shell command, with no additional explanation or formatting.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
        )

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            return f"Error: {response.status_code} - {response.text}"

    def fallback_operation():
        return "Error: Unable to process request due to system issues."

    # 使用错误处理机制保护API调用
    return degradation_manager.with_cache_fallback(
        main_api_operation, fallback_operation, "get_shell_command"
    )


def main():
    """主函数，集成错误处理"""
    try:
        if len(sys.argv) > 1:
            prompt = " ".join(sys.argv[1:])
            command = get_shell_command(prompt)
            if command:
                print(command)
                try:
                    pyperclip.copy(command)
                    # print("\nCopied to clipboard!")
                except Exception as e:
                    degradation_manager.logger.warning(
                        f"Failed to copy to clipboard: {e}"
                    )
                    # 剪贴板失败不应影响核心功能
        else:
            print("Usage: python uv_py/main.py <your natural language prompt>")
    except Exception as e:
        # 捕获所有未处理的异常
        degradation_manager.logger.error(f"Unhandled error in main: {e}")
        print("Error: An unexpected error occurred. Please try again.")

        # 如果错误太多，显示状态信息
        if not degradation_manager.is_healthy():
            status = degradation_manager.get_status()
            print(
                f"System health status: Error count {status['error_count']}/{status['max_error_count']}"
            )
            print("Consider running with --reset-errors to reset error state.")


if __name__ == "__main__":
    main()
