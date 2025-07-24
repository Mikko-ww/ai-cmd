import os
import requests
import sys
import pyperclip
from dotenv import load_dotenv

load_dotenv()

def get_shell_command(prompt):
    api_key = os.getenv("AI_CMD_OPENROUTER_API_KEY")
    if not api_key:
        print("Error: AI_CMD_OPENROUTER_API_KEY not found in .env file.")
        return
    model_name = os.getenv("AI_CMD_OPENROUTER_MODEL")

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
        },
        json={
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that provides shell commands based on a user's natural language prompt. Only provide the shell command, with no additional explanation or formatting."},
                {"role": "user", "content": prompt}
            ]
        }
    )

    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        return f"Error: {response.status_code} - {response.text}"

def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        command = get_shell_command(prompt)
        if command:
            print(command)
            pyperclip.copy(command)
            # print("\nCopied to clipboard!")
    else:
        print("Usage: python uv_py/main.py <your natural language prompt>")

if __name__ == "__main__":
    main()
