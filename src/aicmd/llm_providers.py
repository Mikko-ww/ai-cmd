"""
LLM Provider abstraction and implementations
支持多个大语言模型提供商的抽象接口和具体实现
"""

import os
import requests
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from .logger import logger
from .api_client import APIClientError, APITimeoutError, APIRateLimitError, APIAuthError


class LLMProvider(ABC):
    """大语言模型提供商抽象基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化提供商"""
        self.config = config or {}
        self._session = None
    
    @abstractmethod
    def get_api_key(self) -> str:
        """获取API密钥"""
        pass
    
    @abstractmethod
    def get_model(self) -> str:
        """获取模型名称"""
        pass
    
    @abstractmethod
    def get_base_url(self) -> str:
        """获取API基础URL"""
        pass
    
    @abstractmethod
    def build_request_payload(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        """构建请求载荷"""
        pass
    
    @abstractmethod
    def parse_response(self, response: requests.Response) -> str:
        """解析API响应"""
        pass
    
    def get_headers(self) -> Dict[str, str]:
        """获取请求头，子类可以重写"""
        api_key = self.get_api_key()
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    
    def _get_session(self, max_retries: int = 3) -> requests.Session:
        """获取或创建HTTP会话"""
        if self._session is None:
            self._session = requests.Session()
            try:
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry

                retry_strategy = Retry(
                    total=max_retries,
                    backoff_factor=0.5,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["POST"],
                )
                adapter = HTTPAdapter(max_retries=retry_strategy)
                self._session.mount("https://", adapter)
                self._session.mount("http://", adapter)
            except Exception as e:
                logger.warning(f"Failed to setup retry strategy: {e}")

        return self._session
    
    def send_chat(self, prompt: str, model: Optional[str] = None, timeout: int = 30) -> str:
        """发送聊天请求"""
        api_key = self.get_api_key()
        if not api_key:
            raise APIAuthError(f"API key not found for {self.__class__.__name__}")
        
        model = model or self.get_model()
        if not model:
            raise APIClientError(f"Model not specified for {self.__class__.__name__}")
        
        session = self._get_session()
        headers = self.get_headers()
        payload = self.build_request_payload(prompt, model)
        
        try:
            response = session.post(
                self.get_base_url(),
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                return self.parse_response(response)
            elif response.status_code == 401:
                raise APIAuthError("API key authentication failed")
            elif response.status_code == 429:
                raise APIRateLimitError("API rate limit exceeded")
            elif response.status_code >= 500:
                raise APIClientError(f"API server error: {response.status_code}")
            else:
                raise APIClientError(
                    f"API request failed: {response.status_code} - {response.text}"
                )
        
        except requests.exceptions.Timeout:
            raise APITimeoutError(f"API request timed out after {timeout}s")
    
    def close(self):
        """关闭HTTP会话"""
        if self._session:
            self._session.close()
            self._session = None


class OpenRouterProvider(LLMProvider):
    """OpenRouter 提供商实现"""
    
    def get_api_key(self) -> str:
        return self.config.get("api_key") or os.getenv("AI_CMD_OPENROUTER_API_KEY", "")
    
    def get_model(self) -> str:
        return (
            self.config.get("model") 
            or os.getenv("AI_CMD_OPENROUTER_MODEL", "")
        )
    
    def get_base_url(self) -> str:
        return (
            self.config.get("base_url") 
            or "https://openrouter.ai/api/v1/chat/completions"
        )
    
    def build_request_payload(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        return {
            "model": model or self.get_model(),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that provides shell commands based on a user's "
                        "natural language prompt. Only provide the shell command, with no additional "
                        "explanation or formatting. For any parameters that require user input, "
                        "enclose them in angle brackets, like so: <parameter_name>."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
    
    def parse_response(self, response: requests.Response) -> str:
        try:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as e:
            raise APIClientError(f"Invalid API response format: {e}")


class OpenAIProvider(LLMProvider):
    """OpenAI 提供商实现"""
    
    def get_api_key(self) -> str:
        return self.config.get("api_key") or os.getenv("AI_CMD_OPENAI_API_KEY", "")
    
    def get_model(self) -> str:
        return (
            self.config.get("model") 
            or os.getenv("AI_CMD_OPENAI_MODEL", "gpt-3.5-turbo")
        )
    
    def get_base_url(self) -> str:
        return (
            self.config.get("base_url") 
            or "https://api.openai.com/v1/chat/completions"
        )
    
    def build_request_payload(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        return {
            "model": model or self.get_model(),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that provides shell commands based on a user's "
                        "natural language prompt. Only provide the shell command, with no additional "
                        "explanation or formatting. For any parameters that require user input, "
                        "enclose them in angle brackets, like so: <parameter_name>."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
    
    def parse_response(self, response: requests.Response) -> str:
        try:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as e:
            raise APIClientError(f"Invalid API response format: {e}")


class DeepSeekProvider(LLMProvider):
    """DeepSeek 提供商实现"""
    
    def get_api_key(self) -> str:
        return self.config.get("api_key") or os.getenv("AI_CMD_DEEPSEEK_API_KEY", "")
    
    def get_model(self) -> str:
        return (
            self.config.get("model") 
            or os.getenv("AI_CMD_DEEPSEEK_MODEL", "deepseek-chat")
        )
    
    def get_base_url(self) -> str:
        return (
            self.config.get("base_url") 
            or "https://api.deepseek.com/v1/chat/completions"
        )
    
    def build_request_payload(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        return {
            "model": model or self.get_model(),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that provides shell commands based on a user's "
                        "natural language prompt. Only provide the shell command, with no additional "
                        "explanation or formatting. For any parameters that require user input, "
                        "enclose them in angle brackets, like so: <parameter_name>."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
    
    def parse_response(self, response: requests.Response) -> str:
        try:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as e:
            raise APIClientError(f"Invalid API response format: {e}")


class XAIProvider(LLMProvider):
    """xAI (Grok) 提供商实现"""
    
    def get_api_key(self) -> str:
        return self.config.get("api_key") or os.getenv("AI_CMD_XAI_API_KEY", "")
    
    def get_model(self) -> str:
        return (
            self.config.get("model") 
            or os.getenv("AI_CMD_XAI_MODEL", "grok-beta")
        )
    
    def get_base_url(self) -> str:
        return (
            self.config.get("base_url") 
            or "https://api.x.ai/v1/chat/completions"
        )
    
    def build_request_payload(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        return {
            "model": model or self.get_model(),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that provides shell commands based on a user's "
                        "natural language prompt. Only provide the shell command, with no additional "
                        "explanation or formatting. For any parameters that require user input, "
                        "enclose them in angle brackets, like so: <parameter_name>."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
    
    def parse_response(self, response: requests.Response) -> str:
        try:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as e:
            raise APIClientError(f"Invalid API response format: {e}")


class GeminiProvider(LLMProvider):
    """Google Gemini 提供商实现"""
    
    def get_api_key(self) -> str:
        return self.config.get("api_key") or os.getenv("AI_CMD_GEMINI_API_KEY", "")
    
    def get_model(self) -> str:
        return (
            self.config.get("model") 
            or os.getenv("AI_CMD_GEMINI_MODEL", "gemini-pro")
        )
    
    def get_base_url(self) -> str:
        base_url = (
            self.config.get("base_url") 
            or "https://generativelanguage.googleapis.com/v1beta/models"
        )
        model = self.get_model()
        return f"{base_url}/{model}:generateContent"
    
    def get_headers(self) -> Dict[str, str]:
        """Gemini使用查询参数而不是Authorization头"""
        return {
            "Content-Type": "application/json",
        }
    
    def build_request_payload(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        system_prompt = (
            "You are a helpful assistant that provides shell commands based on a user's "
            "natural language prompt. Only provide the shell command, with no additional "
            "explanation or formatting. For any parameters that require user input, "
            "enclose them in angle brackets, like so: <parameter_name>."
        )
        
        return {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\nUser: {prompt}"}
                    ]
                }
            ]
        }
    
    def send_chat(self, prompt: str, model: Optional[str] = None, timeout: int = 30) -> str:
        """重写发送方法以支持Gemini的API密钥传递方式"""
        api_key = self.get_api_key()
        if not api_key:
            raise APIAuthError(f"API key not found for {self.__class__.__name__}")
        
        session = self._get_session()
        headers = self.get_headers()
        payload = self.build_request_payload(prompt, model)
        
        # Gemini使用查询参数传递API密钥
        url = f"{self.get_base_url()}?key={api_key}"
        
        try:
            response = session.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                return self.parse_response(response)
            elif response.status_code == 401:
                raise APIAuthError("API key authentication failed")
            elif response.status_code == 429:
                raise APIRateLimitError("API rate limit exceeded")
            elif response.status_code >= 500:
                raise APIClientError(f"API server error: {response.status_code}")
            else:
                raise APIClientError(
                    f"API request failed: {response.status_code} - {response.text}"
                )
        
        except requests.exceptions.Timeout:
            raise APITimeoutError(f"API request timed out after {timeout}s")
    
    def parse_response(self, response: requests.Response) -> str:
        try:
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, ValueError) as e:
            raise APIClientError(f"Invalid API response format: {e}")


class QwenProvider(LLMProvider):
    """通义千问 Qwen 提供商实现"""
    
    def get_api_key(self) -> str:
        return self.config.get("api_key") or os.getenv("AI_CMD_QWEN_API_KEY", "")
    
    def get_model(self) -> str:
        return (
            self.config.get("model") 
            or os.getenv("AI_CMD_QWEN_MODEL", "qwen-turbo")
        )
    
    def get_base_url(self) -> str:
        return (
            self.config.get("base_url") 
            or "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        )
    
    def get_headers(self) -> Dict[str, str]:
        """千问使用X-DashScope-SSE和Authorization头"""
        api_key = self.get_api_key()
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "disable",
        }
    
    def build_request_payload(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        return {
            "model": model or self.get_model(),
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that provides shell commands based on a user's "
                            "natural language prompt. Only provide the shell command, with no additional "
                            "explanation or formatting. For any parameters that require user input, "
                            "enclose them in angle brackets, like so: <parameter_name>."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ]
            },
        }
    
    def parse_response(self, response: requests.Response) -> str:
        try:
            result = response.json()
            return result["output"]["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as e:
            raise APIClientError(f"Invalid API response format: {e}")