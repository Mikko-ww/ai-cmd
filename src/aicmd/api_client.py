"""
API客户端模块
集中处理与OpenRouter API的通信，包括超时、重试和错误处理
"""

import os
import requests
from typing import Optional
from .config_manager import ConfigManager
from .error_handler import GracefulDegradationManager
from .logger import logger


class APIClientError(Exception):
    """API客户端异常基类"""

    pass


class APITimeoutError(APIClientError):
    """API超时异常"""

    pass


class APIRateLimitError(APIClientError):
    """API限流异常"""

    pass


class APIAuthError(APIClientError):
    """API认证异常"""

    pass


class OpenRouterAPIClient:
    """OpenRouter API客户端，负责与AI模型通信"""

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        degradation_manager: Optional[GracefulDegradationManager] = None,
        base_url: Optional[str] = None,
    ):
        """初始化API客户端"""
        self.config = config_manager or ConfigManager()
        self.degradation_manager = degradation_manager or GracefulDegradationManager()

        # API配置
        self.base_url = base_url or "https://openrouter.ai/api/v1/chat/completions"
        self.api_key = os.getenv("AI_CMD_OPENROUTER_API_KEY")
        self.model = os.getenv("AI_CMD_OPENROUTER_MODEL")
        self.model_backup = os.getenv("AI_CMD_OPENROUTER_MODEL_BACKUP")

        # 请求配置
        self.timeout = self.config.get("api_timeout_seconds", 30)
        self.max_retries = self.config.get("max_retries", 3)

        # 系统提示词
        self.system_prompt = (
            "You are a helpful assistant that provides shell commands based on a user's "
            "natural language prompt. Only provide the shell command itself, with no additional "
            "explanation, formatting, or markdown code blocks. Do not wrap the command in "
            "backticks, code fences, or any other formatting. Return only the raw command text. "
            "For any parameters that require user input, enclose them in angle brackets, "
            "like so: <parameter_name>."
        )

        # 初始化session
        self._session = None

    def _get_session(self) -> requests.Session:
        """获取或创建HTTP会话"""
        if self._session is None:
            self._session = requests.Session()
            try:
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry

                retry_strategy = Retry(
                    total=self.max_retries,
                    backoff_factor=0.5,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["POST"],
                )
                adapter = HTTPAdapter(max_retries=retry_strategy)
                self._session.mount("https://", adapter)
                self._session.mount("http://", adapter)
            except Exception as e:
                self.degradation_manager.logger.warning(
                    f"Failed to setup retry strategy: {e}"
                )

        return self._session

    def send_chat(
        self, prompt: str, model: Optional[str] = None, timeout: Optional[int] = None
    ) -> str:
        """
        发送聊天请求到OpenRouter API

        Args:
            prompt: 用户输入的提示词
            model: 使用的模型名称（可选，默认使用配置中的模型）
            timeout: 请求超时时间（可选，默认使用配置中的超时时间）

        Returns:
            AI生成的命令字符串

        Raises:
            APIClientError: API请求相关错误
        """
        if not self.api_key:
            raise APIAuthError("AI_CMD_OPENROUTER_API_KEY not found in environment")

        # 确定使用的模型
        is_use_backup_model = self.config.get("use_backup_model", False)
        target_model = model or (
            self.model_backup if is_use_backup_model else self.model
        )

        if not target_model:
            raise APIClientError("No model specified in configuration")

        # 构建请求载荷
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
        }

        headers = {"Authorization": f"Bearer {self.api_key}"}
        request_timeout = timeout or self.timeout

        try:
            session = self._get_session()
            response = session.post(
                url=self.base_url,
                headers=headers,
                json=payload,
                timeout=request_timeout,
            )

            # 检查响应状态
            if response.status_code == 200:
                try:
                    result = response.json()
                    return result["choices"][0]["message"]["content"].strip()
                except (KeyError, IndexError, ValueError) as e:
                    raise APIClientError(f"Invalid API response format: {e}")
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
            raise APITimeoutError(f"API request timed out after {request_timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise APIClientError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            raise APIClientError(f"Request error: {e}")

    def send_chat_with_fallback(self, prompt: str) -> str:
        """
        带有后备模型的聊天请求

        Args:
            prompt: 用户输入的提示词

        Returns:
            AI生成的命令字符串或错误信息
        """

        def main_api_operation():
            try:
                # 尝试主模型
                return self.send_chat(prompt)
            except (APIClientError, APITimeoutError, APIRateLimitError) as e:
                # 如果主模型失败且有备用模型，尝试备用模型
                if self.model_backup and not self.config.get("use_backup_model", False):
                    try:
                        logger.warning(f"Main model failed ({e}), trying backup model")
                        return self.send_chat(prompt, model=self.model_backup)
                    except APIClientError as backup_e:
                        logger.error(f"Backup model also failed: {backup_e}")
                        return f"Error: {backup_e}"
                else:
                    return f"Error: {e}"

        def fallback_operation():
            return "Error: Unable to process request due to system issues."

        # 使用错误处理机制保护API调用
        return self.degradation_manager.with_cache_fallback(
            main_api_operation, fallback_operation, "send_chat_with_fallback"
        )

    def close(self):
        """关闭HTTP会话"""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
