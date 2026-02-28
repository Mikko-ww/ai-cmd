---
description: "在添加新 LLM 提供商、修改提供商实现、调整路由逻辑、或调试 API 调用时使用。覆盖 LLMProvider 抽象层和 LLMRouter 路由模式。"
---

# LLM 提供商开发规范

## 提供商架构
```
LLMRouter（路由器）
  └── LLMProvider（抽象基类）
        └── OpenAICompatibleProvider（OpenAI 格式基类）
              ├── OpenRouterProvider
              ├── OpenAIProvider
              ├── DeepSeekProvider
              ├── XAIProvider
              ├── GeminiProvider（自定义 parse_response）
              └── QwenProvider（自定义 parse_response）
```

## 添加新提供商步骤

### 1. 在 `llm_providers.py` 中实现提供商类
```python
class NewProvider(OpenAICompatibleProvider):
    def get_provider_name(self) -> str:
        return "newprovider"  # 小写，作为 keyring 和配置的 key

    def get_default_model(self) -> str:
        return "default-model-name"

    def get_default_base_url(self) -> str:
        return "https://api.newprovider.com/v1/chat/completions"

    # 若 API 响应格式非标准 OpenAI 格式，需覆盖 parse_response()
```

### 2. 在 `llm_router.py` 注册
```python
PROVIDERS = {
    # ... 现有提供商
    "newprovider": NewProvider,
}
```

### 3. 在 `setting_template.json` 添加配置模板
```json
"newprovider": {
    "model": "",
    "base_url": "https://api.newprovider.com/v1/chat/completions"
}
```

### 4. 编写测试
在 `tests/test_llm_providers.py` 中添加对应的测试用例，使用 mock keyring 和 mock response。

## 关键约束
- API Key 通过 `KeyringManager.get_api_key(provider_name)` 获取，不从配置读取
- 所有提供商共用 `send_chat()` 基础实现，仅需实现抽象方法
- `build_request_payload()` 中使用 `get_system_prompt("default")` 获取系统提示词
- 超时时间从配置 `api_timeout_seconds` 读取，默认 30 秒
