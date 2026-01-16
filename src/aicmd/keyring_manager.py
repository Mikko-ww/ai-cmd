"""
Keyring Manager - 安全存储和管理 API Keys
使用系统 keyring 来安全存储敏感的 API 密钥
"""

import keyring
from typing import Optional
from .logger import logger


class KeyringManager:
    """Keyring 管理器，负责安全存储和检索 API Keys"""

    # 服务名称，用于在 keyring 中标识此应用
    SERVICE_NAME = "com.aicmd.ww"

    @classmethod
    def set_api_key(cls, provider: str, api_key: str) -> bool:
        """
        设置指定提供商的 API Key

        Args:
            provider: 提供商名称 (如 'openai', 'deepseek' 等)
            api_key: API 密钥

        Returns:
            bool: 是否成功设置
        """
        try:
            keyring.set_password(cls.SERVICE_NAME, provider, api_key)
            logger.info(f"API key set successfully for provider: {provider}")
            return True
        except Exception as e:
            logger.error(f"Failed to set API key for {provider}: {e}")
            return False

    @classmethod
    def get_api_key(cls, provider: str) -> Optional[str]:
        """
        获取指定提供商的 API Key

        Args:
            provider: 提供商名称

        Returns:
            Optional[str]: API 密钥，如果不存在则返回 None
        """
        try:
            api_key = keyring.get_password(cls.SERVICE_NAME, provider)
            if api_key:
                logger.info(f"API key retrieved for provider: {provider}")
            return api_key
        except Exception as e:
            logger.error(f"Failed to get API key for {provider}: {e}")
            return None

    @classmethod
    def delete_api_key(cls, provider: str) -> bool:
        """
        删除指定提供商的 API Key

        Args:
            provider: 提供商名称

        Returns:
            bool: 是否成功删除
        """
        try:
            keyring.delete_password(cls.SERVICE_NAME, provider)
            logger.info(f"API key deleted for provider: {provider}")
            return True
        except keyring.errors.PasswordDeleteError:
            logger.warning(f"No API key found to delete for provider: {provider}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete API key for {provider}: {e}")
            return False

    @classmethod
    def list_providers_with_keys(cls) -> list:
        """
        列出所有已设置 API Key 的提供商

        注意：keyring 不提供列出所有密钥的功能，
        所以我们需要检查已知的提供商列表

        Returns:
            list: 已设置 API Key 的提供商列表
        """
        # 已知的提供商列表
        known_providers = ["openrouter", "openai", "deepseek", "xai", "gemini", "qwen"]

        providers_with_keys = []
        for provider in known_providers:
            if cls.get_api_key(provider):
                providers_with_keys.append(provider)

        return providers_with_keys

    @classmethod
    def has_api_key(cls, provider: str) -> bool:
        """
        检查指定提供商是否已设置 API Key

        Args:
            provider: 提供商名称

        Returns:
            bool: 是否已设置
        """
        return cls.get_api_key(provider) is not None
