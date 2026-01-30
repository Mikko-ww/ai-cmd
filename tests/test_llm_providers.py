"""
LLM Providers 测试
测试所有 6 个 LLM 提供商的基本功能，使用 Mock HTTP 请求
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from aicmd.llm_providers import (
    LLMProvider,
    OpenRouterProvider,
    OpenAIProvider,
    DeepSeekProvider,
    XAIProvider,
    GeminiProvider,
    QwenProvider,
)
from aicmd.api_client import (
    APIClientError,
    APITimeoutError,
    APIRateLimitError,
    APIAuthError,
)


@pytest.fixture
def mock_keyring():
    """Mock keyring manager for testing"""
    with patch("aicmd.llm_providers.KeyringManager") as mock:
        # Setup default return values
        mock.get_api_key.return_value = "test-api-key-123"
        yield mock


@pytest.fixture
def provider_config():
    """Sample provider configuration"""
    return {
        "model": "test-model",
        "base_url": "https://test.api.com/v1/chat/completions",
    }


@pytest.fixture
def mock_successful_response():
    """Mock successful API response"""
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "ls -la"
                }
            }
        ]
    }
    return mock_resp


@pytest.fixture
def mock_gemini_response():
    """Mock successful Gemini API response"""
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "ls -la"
                        }
                    ]
                }
            }
        ]
    }
    return mock_resp


@pytest.fixture
def mock_qwen_response():
    """Mock successful Qwen API response"""
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "output": {
            "choices": [
                {
                    "message": {
                        "content": "ls -la"
                    }
                }
            ]
        }
    }
    return mock_resp


class TestOpenRouterProvider:
    """测试 OpenRouter 提供商"""

    def test_get_api_key(self, mock_keyring, provider_config):
        """测试获取 API Key"""
        provider = OpenRouterProvider(provider_config)
        api_key = provider.get_api_key()
        
        assert api_key == "test-api-key-123"
        mock_keyring.get_api_key.assert_called_with("openrouter")

    def test_get_model(self, mock_keyring, provider_config):
        """测试获取模型名称"""
        provider = OpenRouterProvider(provider_config)
        model = provider.get_model()
        
        assert model == "test-model"

    def test_get_base_url(self, mock_keyring, provider_config):
        """测试获取基础 URL"""
        provider = OpenRouterProvider(provider_config)
        base_url = provider.get_base_url()
        
        assert base_url == "https://test.api.com/v1/chat/completions"

    def test_get_default_base_url(self, mock_keyring):
        """测试获取默认基础 URL"""
        provider = OpenRouterProvider({})
        base_url = provider.get_base_url()
        
        assert "openrouter.ai" in base_url

    def test_build_request_payload(self, mock_keyring, provider_config):
        """测试构建请求载荷"""
        provider = OpenRouterProvider(provider_config)
        payload = provider.build_request_payload("list files", "test-model")
        
        assert payload["model"] == "test-model"
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][1]["content"] == "list files"

    @patch("aicmd.llm_providers.requests.Session")
    def test_send_chat_success(self, mock_session, mock_keyring, provider_config, mock_successful_response):
        """测试成功发送聊天请求"""
        provider = OpenRouterProvider(provider_config)
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.post.return_value = mock_successful_response
        
        result = provider.send_chat("list files")
        
        assert result == "ls -la"
        mock_session_instance.post.assert_called_once()

    @patch("aicmd.llm_providers.requests.Session")
    def test_send_chat_auth_error(self, mock_session, mock_keyring, provider_config):
        """测试认证失败"""
        provider = OpenRouterProvider(provider_config)
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        mock_resp = Mock()
        mock_resp.status_code = 401
        mock_session_instance.post.return_value = mock_resp
        
        with pytest.raises(APIAuthError):
            provider.send_chat("list files")

    @patch("aicmd.llm_providers.requests.Session")
    def test_send_chat_rate_limit(self, mock_session, mock_keyring, provider_config):
        """测试限流错误"""
        provider = OpenRouterProvider(provider_config)
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        mock_resp = Mock()
        mock_resp.status_code = 429
        mock_session_instance.post.return_value = mock_resp
        
        with pytest.raises(APIRateLimitError):
            provider.send_chat("list files")

    @patch("aicmd.llm_providers.requests.Session")
    def test_send_chat_timeout(self, mock_session, mock_keyring, provider_config):
        """测试超时错误"""
        provider = OpenRouterProvider(provider_config)
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.post.side_effect = requests.exceptions.Timeout()
        
        with pytest.raises(APITimeoutError):
            provider.send_chat("list files")

    def test_no_api_key(self, provider_config):
        """测试没有 API Key 的情况"""
        with patch("aicmd.llm_providers.KeyringManager") as mock_keyring:
            mock_keyring.get_api_key.return_value = None
            provider = OpenRouterProvider(provider_config)
            
            with pytest.raises(APIAuthError):
                provider.send_chat("list files")


class TestOpenAIProvider:
    """测试 OpenAI 提供商"""

    def test_get_api_key(self, mock_keyring, provider_config):
        """测试获取 API Key"""
        provider = OpenAIProvider(provider_config)
        api_key = provider.get_api_key()
        
        assert api_key == "test-api-key-123"
        mock_keyring.get_api_key.assert_called_with("openai")

    def test_get_default_model(self, mock_keyring):
        """测试获取默认模型"""
        provider = OpenAIProvider({})
        model = provider.get_model()
        
        assert model == "gpt-3.5-turbo"

    def test_get_base_url(self, mock_keyring, provider_config):
        """测试获取基础 URL"""
        provider = OpenAIProvider(provider_config)
        base_url = provider.get_base_url()
        
        assert base_url == "https://test.api.com/v1/chat/completions"

    @patch("aicmd.llm_providers.requests.Session")
    def test_send_chat_success(self, mock_session, mock_keyring, provider_config, mock_successful_response):
        """测试成功发送请求"""
        provider = OpenAIProvider(provider_config)
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.post.return_value = mock_successful_response
        
        result = provider.send_chat("list files")
        
        assert result == "ls -la"


class TestDeepSeekProvider:
    """测试 DeepSeek 提供商"""

    def test_get_api_key(self, mock_keyring, provider_config):
        """测试获取 API Key"""
        provider = DeepSeekProvider(provider_config)
        api_key = provider.get_api_key()
        
        assert api_key == "test-api-key-123"
        mock_keyring.get_api_key.assert_called_with("deepseek")

    def test_get_default_model(self, mock_keyring):
        """测试获取默认模型"""
        provider = DeepSeekProvider({})
        model = provider.get_model()
        
        assert model == "deepseek-chat"

    def test_get_default_base_url(self, mock_keyring):
        """测试获取默认基础 URL"""
        provider = DeepSeekProvider({})
        base_url = provider.get_base_url()
        
        assert "deepseek.com" in base_url


class TestXAIProvider:
    """测试 xAI (Grok) 提供商"""

    def test_get_api_key(self, mock_keyring, provider_config):
        """测试获取 API Key"""
        provider = XAIProvider(provider_config)
        api_key = provider.get_api_key()
        
        assert api_key == "test-api-key-123"
        mock_keyring.get_api_key.assert_called_with("xai")

    def test_get_default_model(self, mock_keyring):
        """测试获取默认模型"""
        provider = XAIProvider({})
        model = provider.get_model()
        
        assert model == "grok-beta"

    def test_get_default_base_url(self, mock_keyring):
        """测试获取默认基础 URL"""
        provider = XAIProvider({})
        base_url = provider.get_base_url()
        
        assert "x.ai" in base_url


class TestGeminiProvider:
    """测试 Google Gemini 提供商"""

    def test_get_api_key(self, mock_keyring, provider_config):
        """测试获取 API Key"""
        provider = GeminiProvider(provider_config)
        api_key = provider.get_api_key()
        
        assert api_key == "test-api-key-123"
        mock_keyring.get_api_key.assert_called_with("gemini")

    def test_get_default_model(self, mock_keyring):
        """测试获取默认模型"""
        provider = GeminiProvider({})
        model = provider.get_model()
        
        assert model == "gemini-pro"

    def test_get_base_url_with_model(self, mock_keyring, provider_config):
        """测试获取基础 URL（包含模型）"""
        provider = GeminiProvider(provider_config)
        base_url = provider.get_base_url()
        
        # Gemini URL should include model and generateContent
        assert "test-model" in base_url
        assert "generateContent" in base_url

    def test_get_headers_no_auth(self, mock_keyring, provider_config):
        """测试 Gemini 特殊的请求头（不使用 Authorization）"""
        provider = GeminiProvider(provider_config)
        headers = provider.get_headers()
        
        # Gemini 不使用 Authorization 头
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"

    def test_build_request_payload_format(self, mock_keyring, provider_config):
        """测试 Gemini 特殊的请求载荷格式"""
        provider = GeminiProvider(provider_config)
        payload = provider.build_request_payload("list files")
        
        # Gemini 使用 contents 而不是 messages
        assert "contents" in payload
        assert "parts" in payload["contents"][0]

    @patch("aicmd.llm_providers.requests.Session")
    def test_send_chat_success(self, mock_session, mock_keyring, provider_config, mock_gemini_response):
        """测试成功发送请求"""
        provider = GeminiProvider(provider_config)
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.post.return_value = mock_gemini_response
        
        result = provider.send_chat("list files")
        
        assert result == "ls -la"
        # 验证 URL 包含 API key 作为查询参数
        call_args = mock_session_instance.post.call_args
        assert "key=" in call_args[0][0]

    @patch("aicmd.llm_providers.requests.Session")
    def test_parse_response(self, mock_session, mock_keyring, provider_config):
        """测试解析 Gemini 响应"""
        provider = GeminiProvider(provider_config)
        
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "pwd"}]}}
            ]
        }
        
        result = provider.parse_response(mock_resp)
        assert result == "pwd"


class TestQwenProvider:
    """测试通义千问 Qwen 提供商"""

    def test_get_api_key(self, mock_keyring, provider_config):
        """测试获取 API Key"""
        provider = QwenProvider(provider_config)
        api_key = provider.get_api_key()
        
        assert api_key == "test-api-key-123"
        mock_keyring.get_api_key.assert_called_with("qwen")

    def test_get_default_model(self, mock_keyring):
        """测试获取默认模型"""
        provider = QwenProvider({})
        model = provider.get_model()
        
        assert model == "qwen-turbo"

    def test_get_default_base_url(self, mock_keyring):
        """测试获取默认基础 URL"""
        provider = QwenProvider({})
        base_url = provider.get_base_url()
        
        assert "dashscope.aliyuncs.com" in base_url

    def test_get_headers_with_sse(self, mock_keyring, provider_config):
        """测试 Qwen 特殊的请求头"""
        provider = QwenProvider(provider_config)
        headers = provider.get_headers()
        
        # Qwen 使用特殊的 X-DashScope-SSE 头
        assert "X-DashScope-SSE" in headers
        assert headers["X-DashScope-SSE"] == "disable"
        assert "Authorization" in headers

    def test_build_request_payload_format(self, mock_keyring, provider_config):
        """测试 Qwen 特殊的请求载荷格式"""
        provider = QwenProvider(provider_config)
        payload = provider.build_request_payload("list files")
        
        # Qwen 使用 input.messages 结构
        assert "input" in payload
        assert "messages" in payload["input"]
        assert payload["model"] == "test-model"

    @patch("aicmd.llm_providers.requests.Session")
    def test_parse_response(self, mock_session, mock_keyring, provider_config):
        """测试解析 Qwen 响应"""
        provider = QwenProvider(provider_config)
        
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "output": {
                "choices": [
                    {"message": {"content": "echo hello"}}
                ]
            }
        }
        
        result = provider.parse_response(mock_resp)
        assert result == "echo hello"


class TestLLMProviderBase:
    """测试 LLM Provider 基类的通用功能"""

    def test_session_creation(self, mock_keyring, provider_config):
        """测试会话创建和重用"""
        provider = OpenRouterProvider(provider_config)
        
        # 第一次调用创建会话
        session1 = provider._get_session()
        assert session1 is not None
        
        # 第二次调用应该重用同一个会话
        session2 = provider._get_session()
        assert session1 is session2

    def test_close_session(self, mock_keyring, provider_config):
        """测试关闭会话"""
        provider = OpenRouterProvider(provider_config)
        
        # 创建会话
        session = provider._get_session()
        assert provider._session is not None
        
        # 关闭会话
        provider.close()
        assert provider._session is None

    @patch("aicmd.llm_providers.requests.Session")
    def test_send_chat_server_error(self, mock_session, mock_keyring, provider_config):
        """测试服务器错误处理"""
        provider = OpenRouterProvider(provider_config)
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_session_instance.post.return_value = mock_resp
        
        with pytest.raises(APIClientError) as exc_info:
            provider.send_chat("list files")
        
        assert "500" in str(exc_info.value)

    @patch("aicmd.llm_providers.requests.Session")
    def test_send_chat_invalid_response_format(self, mock_session, mock_keyring, provider_config):
        """测试无效响应格式处理"""
        provider = OpenRouterProvider(provider_config)
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"invalid": "format"}
        mock_session_instance.post.return_value = mock_resp
        
        with pytest.raises(APIClientError) as exc_info:
            provider.send_chat("list files")
        
        assert "Invalid API response format" in str(exc_info.value)

    def test_no_model_specified(self, mock_keyring):
        """测试未指定模型时的错误"""
        provider = OpenRouterProvider({})  # 没有配置模型
        
        with pytest.raises(APIClientError) as exc_info:
            provider.send_chat("list files")
        
        assert "Model not specified" in str(exc_info.value)
