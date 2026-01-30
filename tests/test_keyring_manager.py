"""
Keyring Manager 测试
测试 API Key 的安全存储和管理，使用测试环境隔离
"""

import pytest
import keyring
from unittest.mock import patch, Mock
from aicmd.keyring_manager import KeyringManager


@pytest.fixture(autouse=True)
def ensure_test_service():
    """确保使用测试服务名称"""
    import os
    # 确认测试环境变量已设置（在 conftest.py 中设置）
    assert os.environ.get("AICMD_KEYRING_SERVICE") == "com.aicmd.ww.test"
    yield


@pytest.fixture
def clean_keyring():
    """清理测试 keyring 数据"""
    # 清理所有已知提供商的测试密钥
    providers = ["openrouter", "openai", "deepseek", "xai", "gemini", "qwen", "test_provider"]
    for provider in providers:
        try:
            keyring.delete_password(KeyringManager.SERVICE_NAME, provider)
        except Exception:
            pass  # 忽略不存在的密钥
    
    yield
    
    # 测试后再次清理
    for provider in providers:
        try:
            keyring.delete_password(KeyringManager.SERVICE_NAME, provider)
        except Exception:
            pass


class TestKeyringManager:
    """测试 Keyring Manager 的基本功能"""

    def test_service_name_from_env(self):
        """测试从环境变量读取服务名称"""
        # 应该使用测试服务名
        assert KeyringManager.SERVICE_NAME == "com.aicmd.ww.test"
        assert KeyringManager.SERVICE_NAME != KeyringManager._BASE_SERVICE_NAME

    def test_set_api_key_success(self, clean_keyring):
        """测试成功设置 API Key"""
        result = KeyringManager.set_api_key("test_provider", "test-key-123")
        
        assert result is True
        
        # 验证密钥已存储
        stored_key = keyring.get_password(KeyringManager.SERVICE_NAME, "test_provider")
        assert stored_key == "test-key-123"

    def test_get_api_key_success(self, clean_keyring):
        """测试成功获取 API Key"""
        # 先设置密钥
        KeyringManager.set_api_key("test_provider", "my-secret-key")
        
        # 获取密钥
        api_key = KeyringManager.get_api_key("test_provider")
        
        assert api_key == "my-secret-key"

    def test_get_api_key_not_found(self, clean_keyring):
        """测试获取不存在的 API Key"""
        api_key = KeyringManager.get_api_key("nonexistent_provider")
        
        assert api_key is None

    def test_delete_api_key_success(self, clean_keyring):
        """测试成功删除 API Key"""
        # 先设置密钥
        KeyringManager.set_api_key("test_provider", "key-to-delete")
        
        # 删除密钥
        result = KeyringManager.delete_api_key("test_provider")
        
        assert result is True
        
        # 验证密钥已删除
        api_key = KeyringManager.get_api_key("test_provider")
        assert api_key is None

    def test_delete_api_key_not_found(self, clean_keyring):
        """测试删除不存在的 API Key"""
        # 直接删除不存在的密钥
        result = KeyringManager.delete_api_key("nonexistent_provider")
        
        # 应该返回 False（警告但不报错）
        assert result is False

    def test_has_api_key_true(self, clean_keyring):
        """测试检查存在的 API Key"""
        KeyringManager.set_api_key("test_provider", "existing-key")
        
        assert KeyringManager.has_api_key("test_provider") is True

    def test_has_api_key_false(self, clean_keyring):
        """测试检查不存在的 API Key"""
        assert KeyringManager.has_api_key("nonexistent_provider") is False

    def test_list_providers_with_keys_empty(self, clean_keyring):
        """测试列出提供商（空列表）"""
        providers = KeyringManager.list_providers_with_keys()
        
        assert isinstance(providers, list)
        assert len(providers) == 0

    def test_list_providers_with_keys_multiple(self, clean_keyring):
        """测试列出多个提供商"""
        # 设置多个提供商的密钥
        KeyringManager.set_api_key("openai", "openai-key")
        KeyringManager.set_api_key("deepseek", "deepseek-key")
        KeyringManager.set_api_key("gemini", "gemini-key")
        
        providers = KeyringManager.list_providers_with_keys()
        
        assert "openai" in providers
        assert "deepseek" in providers
        assert "gemini" in providers
        assert len(providers) == 3

    def test_list_providers_with_keys_partial(self, clean_keyring):
        """测试列出部分配置的提供商"""
        # 只设置部分提供商
        KeyringManager.set_api_key("openrouter", "openrouter-key")
        KeyringManager.set_api_key("qwen", "qwen-key")
        
        providers = KeyringManager.list_providers_with_keys()
        
        assert "openrouter" in providers
        assert "qwen" in providers
        assert "openai" not in providers  # 未设置
        assert "xai" not in providers  # 未设置


class TestKeyringManagerEdgeCases:
    """测试边界情况"""

    def test_set_empty_api_key(self, clean_keyring):
        """测试设置空 API Key"""
        result = KeyringManager.set_api_key("test_provider", "")
        
        # 应该成功（keyring 允许空字符串）
        assert result is True
        
        api_key = KeyringManager.get_api_key("test_provider")
        assert api_key == ""

    def test_set_very_long_api_key(self, clean_keyring):
        """测试设置非常长的 API Key"""
        long_key = "x" * 1000  # 1000 字符的密钥
        
        result = KeyringManager.set_api_key("test_provider", long_key)
        
        assert result is True
        
        api_key = KeyringManager.get_api_key("test_provider")
        assert api_key == long_key
        assert len(api_key) == 1000

    def test_set_special_characters_in_key(self, clean_keyring):
        """测试包含特殊字符的 API Key"""
        special_key = "key!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        
        result = KeyringManager.set_api_key("test_provider", special_key)
        
        assert result is True
        
        api_key = KeyringManager.get_api_key("test_provider")
        assert api_key == special_key

    def test_overwrite_existing_key(self, clean_keyring):
        """测试覆盖已存在的密钥"""
        # 设置初始密钥
        KeyringManager.set_api_key("test_provider", "old-key")
        
        # 覆盖密钥
        result = KeyringManager.set_api_key("test_provider", "new-key")
        
        assert result is True
        
        # 验证是新密钥
        api_key = KeyringManager.get_api_key("test_provider")
        assert api_key == "new-key"
        assert api_key != "old-key"

    def test_provider_name_case_sensitive(self, clean_keyring):
        """测试提供商名称大小写敏感性"""
        KeyringManager.set_api_key("TestProvider", "key1")
        KeyringManager.set_api_key("testprovider", "key2")
        
        # 应该是不同的密钥
        key1 = KeyringManager.get_api_key("TestProvider")
        key2 = KeyringManager.get_api_key("testprovider")
        
        assert key1 == "key1"
        assert key2 == "key2"


class TestKeyringManagerErrorHandling:
    """测试错误处理"""

    @patch("aicmd.keyring_manager.keyring.set_password")
    def test_set_api_key_exception(self, mock_set_password, clean_keyring):
        """测试设置密钥时的异常处理"""
        mock_set_password.side_effect = Exception("Keyring error")
        
        result = KeyringManager.set_api_key("test_provider", "test-key")
        
        # 应该捕获异常并返回 False
        assert result is False

    @patch("aicmd.keyring_manager.keyring.get_password")
    def test_get_api_key_exception(self, mock_get_password, clean_keyring):
        """测试获取密钥时的异常处理"""
        mock_get_password.side_effect = Exception("Keyring error")
        
        api_key = KeyringManager.get_api_key("test_provider")
        
        # 应该捕获异常并返回 None
        assert api_key is None

    @patch("aicmd.keyring_manager.keyring.delete_password")
    def test_delete_api_key_general_exception(self, mock_delete_password, clean_keyring):
        """测试删除密钥时的一般异常处理"""
        mock_delete_password.side_effect = Exception("Unexpected error")
        
        result = KeyringManager.delete_api_key("test_provider")
        
        # 应该捕获异常并返回 False
        assert result is False


class TestKeyringManagerIntegration:
    """测试与真实 keyring 的集成（隔离环境）"""

    def test_multiple_operations_sequence(self, clean_keyring):
        """测试一系列操作的完整流程"""
        provider = "integration_test"
        
        # 1. 初始状态：密钥不存在
        assert KeyringManager.has_api_key(provider) is False
        assert KeyringManager.get_api_key(provider) is None
        
        # 2. 设置密钥
        assert KeyringManager.set_api_key(provider, "test-key-1") is True
        assert KeyringManager.has_api_key(provider) is True
        
        # 3. 获取密钥
        api_key = KeyringManager.get_api_key(provider)
        assert api_key == "test-key-1"
        
        # 4. 更新密钥
        assert KeyringManager.set_api_key(provider, "test-key-2") is True
        api_key = KeyringManager.get_api_key(provider)
        assert api_key == "test-key-2"
        
        # 5. 删除密钥
        assert KeyringManager.delete_api_key(provider) is True
        assert KeyringManager.has_api_key(provider) is False
        
        # 6. 再次尝试删除（应该返回 False）
        assert KeyringManager.delete_api_key(provider) is False

    def test_all_known_providers(self, clean_keyring):
        """测试所有已知提供商"""
        known_providers = ["openrouter", "openai", "deepseek", "xai", "gemini", "qwen"]
        
        # 为所有提供商设置密钥
        for provider in known_providers:
            result = KeyringManager.set_api_key(provider, f"{provider}-key")
            assert result is True
        
        # 验证所有提供商都在列表中
        providers_with_keys = KeyringManager.list_providers_with_keys()
        for provider in known_providers:
            assert provider in providers_with_keys
        
        # 验证可以获取所有密钥
        for provider in known_providers:
            api_key = KeyringManager.get_api_key(provider)
            assert api_key == f"{provider}-key"
        
        # 删除所有密钥
        for provider in known_providers:
            result = KeyringManager.delete_api_key(provider)
            assert result is True
        
        # 验证所有密钥已删除
        providers_with_keys = KeyringManager.list_providers_with_keys()
        assert len(providers_with_keys) == 0
