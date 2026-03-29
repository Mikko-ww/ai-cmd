"""
Keyring Manager - 安全存储和管理 API Keys
使用系统 keyring 来安全存储敏感的 API 密钥

在 keyring 不可用的环境（如 WSL、无 D-Bus 的 Linux）中，
自动回退到环境变量：AICMD_API_KEY_<PROVIDER_UPPER>
例如：AICMD_API_KEY_OPENAI, AICMD_API_KEY_DEEPSEEK
"""

import os
from typing import Optional
from .logger import logger

# 尝试导入 keyring，在不可用时优雅降级
try:
    import keyring
    import keyring.errors

    # 验证 keyring 后端是否真正可用（WSL 等环境可能安装了包但没有可用后端）
    def _check_keyring_backend() -> bool:
        try:
            backend = keyring.get_keyring()
            backend_name = type(backend).__name__
            # 'fail.Keyring' 和 'NullKeyring' 表示没有可用后端
            if backend_name in ("Keyring", "NullKeyring"):
                # 进一步检查完整类名
                full_name = f"{type(backend).__module__}.{backend_name}"
                if "fail" in full_name or "null" in full_name.lower():
                    return False
            # 尝试简单的读操作验证后端真正可用
            keyring.get_password("__aicmd_backend_check__", "__probe__")
            return True
        except Exception:
            return False

    _KEYRING_AVAILABLE = _check_keyring_backend()

except ImportError:
    keyring = None  # type: ignore[assignment]
    _KEYRING_AVAILABLE = False

if not _KEYRING_AVAILABLE:
    logger.warning(
        "keyring 后端不可用（常见于 WSL/无图形界面的 Linux 环境）。"
        "API Key 将从环境变量读取：AICMD_API_KEY_<PROVIDER_UPPER>。"
        "例如：export AICMD_API_KEY_OPENAI=your_key"
    )


def _env_var_name(provider: str) -> str:
    """将提供商名称转换为对应的环境变量名"""
    return f"AICMD_API_KEY_{provider.upper()}"


class KeyringManager:
    """Keyring 管理器，负责安全存储和检索 API Keys

    优先使用系统 keyring；当 keyring 不可用时（如 WSL 环境），
    自动回退到环境变量 AICMD_API_KEY_<PROVIDER_UPPER>。
    """

    # 服务名称，用于在 keyring 中标识此应用
    # 可通过环境变量 AICMD_KEYRING_SERVICE 覆盖，用于测试环境隔离
    _BASE_SERVICE_NAME = "com.aicmd.ww"
    SERVICE_NAME = os.getenv("AICMD_KEYRING_SERVICE", _BASE_SERVICE_NAME)

    @classmethod
    def is_keyring_available(cls) -> bool:
        """检查系统 keyring 是否可用"""
        return _KEYRING_AVAILABLE

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
        if not _KEYRING_AVAILABLE:
            env_var = _env_var_name(provider)
            logger.warning(
                f"keyring 不可用，无法持久化保存 API Key。"
                f"请将密钥设置为环境变量：export {env_var}={api_key}"
            )
            return False

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

        优先从 keyring 读取；keyring 不可用时从环境变量读取。

        Args:
            provider: 提供商名称

        Returns:
            Optional[str]: API 密钥，如果不存在则返回 None
        """
        # 优先尝试 keyring
        if _KEYRING_AVAILABLE:
            try:
                api_key = keyring.get_password(cls.SERVICE_NAME, provider)
                if api_key is not None:
                    return api_key
            except Exception as e:
                logger.error(f"Failed to get API key from keyring for {provider}: {e}")

        # 回退到环境变量
        env_var = _env_var_name(provider)
        env_key = os.environ.get(env_var)
        if env_key:
            return env_key

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
        if not _KEYRING_AVAILABLE:
            env_var = _env_var_name(provider)
            logger.warning(
                f"keyring 不可用，无法删除持久化的 API Key。"
                f"请手动取消环境变量：unset {env_var}"
            )
            return False

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
