"""
系统提示词模块
集中管理所有AI交互的系统提示词，方便统一调整和维护
"""

# 默认系统提示词 - 用于生成shell命令
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant that provides shell commands based on a user's "
    "natural language prompt. Only provide the shell command itself, with no additional "
    "explanation, formatting, or markdown code blocks. Do not wrap the command in "
    "backticks, code fences, or any other formatting. Return only the raw command text. "
    "For any parameters that require user input, enclose them in angle brackets, "
    "like so: <parameter_name>."
)


def get_system_prompt(prompt_type: str = "default") -> str:
    """
    获取指定类型的系统提示词
    
    Args:
        prompt_type: 提示词类型，默认为 "default"
        
    Returns:
        对应的系统提示词字符串
    """
    prompts = {
        "default": DEFAULT_SYSTEM_PROMPT,
        # 未来可以在这里添加更多类型的提示词
        # "explain": EXPLAIN_PROMPT,
        # "debug": DEBUG_PROMPT,
    }
    
    return prompts.get(prompt_type, DEFAULT_SYSTEM_PROMPT)
