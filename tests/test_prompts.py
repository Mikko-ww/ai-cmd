"""
Prompts 模块测试
测试系统提示词的生成和管理
"""

import pytest
from aicmd.prompts import (
    get_system_prompt,
    AICMD_DEF_SYSTEM_PROMPT,
)


class TestGetSystemPrompt:
    """测试 get_system_prompt 函数"""

    def test_get_default_prompt(self):
        """测试获取默认提示词"""
        prompt = get_system_prompt("default")
        
        assert prompt == AICMD_DEF_SYSTEM_PROMPT
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_get_default_prompt_no_argument(self):
        """测试不带参数获取默认提示词"""
        prompt = get_system_prompt()
        
        assert prompt == AICMD_DEF_SYSTEM_PROMPT

    def test_get_unknown_prompt_type(self):
        """测试获取未知类型的提示词（应返回默认）"""
        prompt = get_system_prompt("unknown_type")
        
        # 未知类型应该返回默认提示词
        assert prompt == AICMD_DEF_SYSTEM_PROMPT

    def test_get_nonexistent_prompt_type(self):
        """测试获取不存在的提示词类型"""
        prompt = get_system_prompt("explain")
        
        # 当前 explain 类型尚未实现，应该返回默认提示词
        assert prompt == AICMD_DEF_SYSTEM_PROMPT

    def test_get_debug_prompt_type(self):
        """测试获取 debug 类型提示词"""
        prompt = get_system_prompt("debug")
        
        # debug 类型尚未实现，应该返回默认提示词
        assert prompt == AICMD_DEF_SYSTEM_PROMPT


class TestDefaultSystemPrompt:
    """测试默认系统提示词内容"""

    def test_prompt_is_non_empty(self):
        """测试提示词非空"""
        assert len(AICMD_DEF_SYSTEM_PROMPT) > 0

    def test_prompt_contains_key_instructions(self):
        """测试提示词包含关键指令"""
        prompt = AICMD_DEF_SYSTEM_PROMPT
        
        # 应该包含关键指令
        assert "shell command" in prompt.lower()
        assert "only provide" in prompt.lower() or "only return" in prompt.lower()

    def test_prompt_mentions_no_formatting(self):
        """测试提示词提到不要格式化"""
        prompt = AICMD_DEF_SYSTEM_PROMPT
        
        # 应该明确说明不要格式化
        assert "no additional" in prompt.lower() or "no explanation" in prompt.lower()
        assert "formatting" in prompt.lower() or "markdown" in prompt.lower()

    def test_prompt_mentions_no_code_blocks(self):
        """测试提示词提到不要代码块"""
        prompt = AICMD_DEF_SYSTEM_PROMPT
        
        # 应该说明不要使用代码块
        assert "code blocks" in prompt.lower() or "code fences" in prompt.lower()
        assert "backticks" in prompt.lower() or "```" not in prompt

    def test_prompt_mentions_parameters(self):
        """测试提示词提到参数处理"""
        prompt = AICMD_DEF_SYSTEM_PROMPT
        
        # 应该说明如何处理参数
        assert "parameter" in prompt.lower()
        assert "angle brackets" in prompt.lower() or "<parameter" in prompt

    def test_prompt_is_string_type(self):
        """测试提示词是字符串类型"""
        assert isinstance(AICMD_DEF_SYSTEM_PROMPT, str)

    def test_prompt_no_leading_trailing_whitespace(self):
        """测试提示词没有多余的前后空格"""
        prompt = AICMD_DEF_SYSTEM_PROMPT
        
        # 提示词应该已经被 strip 过
        assert prompt == prompt.strip(), "Prompt should not have leading or trailing whitespace"

    def test_prompt_has_complete_sentences(self):
        """测试提示词包含完整句子"""
        prompt = AICMD_DEF_SYSTEM_PROMPT
        
        # 应该包含句号（完整句子的标志）
        assert "." in prompt


class TestPromptConsistency:
    """测试提示词的一致性"""

    def test_same_prompt_for_same_type(self):
        """测试相同类型返回相同提示词"""
        prompt1 = get_system_prompt("default")
        prompt2 = get_system_prompt("default")
        
        assert prompt1 == prompt2

    def test_prompt_not_modified_between_calls(self):
        """测试多次调用不会修改提示词"""
        prompts = [get_system_prompt("default") for _ in range(5)]
        
        # 所有提示词应该相同
        assert all(p == prompts[0] for p in prompts)

    def test_constant_matches_function_return(self):
        """测试常量与函数返回值匹配"""
        from_constant = AICMD_DEF_SYSTEM_PROMPT
        from_function = get_system_prompt("default")
        
        assert from_constant == from_function


class TestPromptQuality:
    """测试提示词质量"""

    def test_prompt_length_reasonable(self):
        """测试提示词长度合理"""
        prompt = AICMD_DEF_SYSTEM_PROMPT
        
        # 提示词应该有足够长度包含有用信息
        assert len(prompt) >= 100
        # 但也不应该太长
        assert len(prompt) <= 1000

    def test_prompt_uses_clear_language(self):
        """测试提示词使用清晰的语言"""
        prompt = AICMD_DEF_SYSTEM_PROMPT.lower()
        
        # 应该使用明确的动词
        clear_verbs = ["provide", "return", "do not", "enclose"]
        assert any(verb in prompt for verb in clear_verbs)

    def test_prompt_has_specific_instructions(self):
        """测试提示词有具体指令"""
        prompt = AICMD_DEF_SYSTEM_PROMPT.lower()
        
        # 应该有具体的"不要做"指令
        negative_instructions = ["do not", "no additional", "no explanation"]
        assert any(instr in prompt for instr in negative_instructions)

    def test_prompt_addresses_common_issues(self):
        """测试提示词解决常见问题"""
        prompt = AICMD_DEF_SYSTEM_PROMPT.lower()
        
        # 应该解决常见的格式化问题
        common_issues = ["backticks", "markdown", "formatting", "code"]
        assert sum(issue in prompt for issue in common_issues) >= 2


class TestPromptFunctionParameters:
    """测试 get_system_prompt 函数参数处理"""

    def test_accepts_string_argument(self):
        """测试接受字符串参数"""
        try:
            prompt = get_system_prompt("default")
            assert isinstance(prompt, str)
        except Exception as e:
            pytest.fail(f"Should accept string argument: {e}")

    def test_returns_string(self):
        """测试返回字符串"""
        prompt = get_system_prompt()
        assert isinstance(prompt, str)

    def test_handles_empty_string(self):
        """测试处理空字符串"""
        prompt = get_system_prompt("")
        # 空字符串应该返回默认提示词
        assert prompt == AICMD_DEF_SYSTEM_PROMPT

    def test_handles_none_gracefully(self):
        """测试优雅处理 None"""
        # 如果传入 None，应该使用默认值
        try:
            # 这可能会使用默认参数
            prompt = get_system_prompt(None)
            assert isinstance(prompt, str)
        except TypeError:
            # 如果不接受 None，应该有明确的类型检查
            pass


class TestPromptExtensibility:
    """测试提示词的可扩展性"""

    def test_prompt_type_structure_exists(self):
        """测试提示词类型结构存在"""
        # 验证 get_system_prompt 内部有类型字典
        # 这通过功能测试来验证
        default_prompt = get_system_prompt("default")
        unknown_prompt = get_system_prompt("unknown")
        
        # 应该能处理不同的类型
        assert isinstance(default_prompt, str)
        assert isinstance(unknown_prompt, str)

    def test_future_prompt_types_structure(self):
        """测试未来提示词类型的结构"""
        # 即使这些类型还未实现，函数也应该能处理
        future_types = ["explain", "debug", "alternative", "verbose"]
        
        for prompt_type in future_types:
            prompt = get_system_prompt(prompt_type)
            assert isinstance(prompt, str)
            assert len(prompt) > 0


class TestPromptDocumentation:
    """测试提示词相关的文档"""

    def test_function_has_docstring(self):
        """测试函数有文档字符串"""
        assert get_system_prompt.__doc__ is not None
        assert len(get_system_prompt.__doc__) > 0

    def test_docstring_describes_parameters(self):
        """测试文档字符串描述参数"""
        docstring = get_system_prompt.__doc__.lower()
        
        assert "prompt_type" in docstring or "type" in docstring

    def test_docstring_describes_return(self):
        """测试文档字符串描述返回值"""
        docstring = get_system_prompt.__doc__.lower()
        
        assert "return" in docstring or "提示词" in docstring


class TestPromptIntegration:
    """测试提示词与其他模块的集成"""

    def test_prompt_can_be_used_in_api_request(self):
        """测试提示词可以用于 API 请求"""
        prompt = get_system_prompt("default")
        
        # 模拟 API 请求结构
        api_request = {
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": "list files"}
            ]
        }
        
        assert api_request["messages"][0]["content"] == prompt
        assert len(api_request["messages"]) == 2

    def test_prompt_compatible_with_json(self):
        """测试提示词兼容 JSON 编码"""
        import json
        
        prompt = get_system_prompt("default")
        
        # 应该能被 JSON 编码
        try:
            json_str = json.dumps({"prompt": prompt})
            assert isinstance(json_str, str)
            
            # 应该能被解码回来
            decoded = json.loads(json_str)
            assert decoded["prompt"] == prompt
        except Exception as e:
            pytest.fail(f"Prompt should be JSON-compatible: {e}")
