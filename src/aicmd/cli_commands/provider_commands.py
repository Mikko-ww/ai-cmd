"""
Provider Management Commands

Handles all LLM provider-related CLI commands.
"""


def list_providers_command():
    """列出所有支持的LLM提供商"""
    try:
        from ..llm_router import LLMRouter

        router = LLMRouter()
        providers = router.list_providers()
        current_provider = router.get_current_provider()

        print("=== Supported LLM Providers ===")
        print(f"Current default provider: {current_provider}")
        print("\nAvailable providers:")

        for provider in providers:
            marker = " (current)" if provider == current_provider else ""
            print(f"  • {provider}{marker}")

        print(f"\nTotal: {len(providers)} providers supported")
        print("\nTo set a provider as default, use:")
        print("  aicmd --set-config default_provider <provider_name>")
        print("\nTo test a provider configuration, use:")
        print("  aicmd --test-provider <provider_name>")

    except Exception as e:
        print(f"Error listing providers: {e}")


def test_provider_command(provider_name: str):
    """测试指定提供商的配置"""
    try:
        from ..llm_router import LLMRouter

        router = LLMRouter()
        supported_providers = router.list_providers()

        if provider_name not in supported_providers:
            print(f"✗ Unknown provider: {provider_name}")
            print(f"Supported providers: {', '.join(supported_providers)}")
            return

        print(f"=== Testing Provider: {provider_name} ===")

        validation_result = router.validate_provider_config(provider_name)

        if validation_result["valid"]:
            print("✓ Provider configuration is valid")
            config = validation_result["config"]
            print(f"  API Key: {config['api_key']}")
            print(f"  Model: {config['model']}")
            print(f"  Base URL: {config['base_url']}")

            # Try a simple test request
            print("\nTesting API connection...")
            try:
                result = router.send_chat("echo hello", provider_name=provider_name)
                if result and not result.startswith("Error:"):
                    print("✓ API connection successful")
                    print(f"Response: {result[:50]}{'...' if len(result) > 50 else ''}")
                else:
                    print(f"✗ API test failed: {result}")
            except Exception as api_e:
                print(f"✗ API test failed: {api_e}")

        else:
            print("✗ Provider configuration is invalid")
            if "error" in validation_result:
                print(f"Error: {validation_result['error']}")
            if "issues" in validation_result:
                print("Issues:")
                for issue in validation_result["issues"]:
                    print(f"  • {issue}")

        print(f"\nTo configure {provider_name}:")
        print(f"  1. Set API key: aicmd --set-api-key {provider_name} <your_api_key>")
        print(
            f"  2. Edit config file to set model: aicmd --set-config providers.{provider_name}.model <model_name>"
        )

    except Exception as e:
        print(f"Error testing provider: {e}")


def set_api_key_command(provider: str, api_key: str):
    """设置提供商的 API Key"""
    try:
        from ..keyring_manager import KeyringManager, _env_var_name
        from ..llm_router import LLMRouter

        router = LLMRouter()
        supported_providers = router.list_providers()

        if provider not in supported_providers:
            print(f"✗ Unknown provider: {provider}")
            print(f"Supported providers: {', '.join(supported_providers)}")
            return

        if not KeyringManager.is_keyring_available():
            env_var = _env_var_name(provider)
            print("⚠ System keyring is not available in this environment (e.g. WSL).")
            print("  Please set the API key via environment variable instead:")
            print(f"    export {env_var}={api_key}")
            print("  To make it permanent, add the above line to your ~/.bashrc or ~/.zshrc.")
            print("\nNext steps:")
            print(
                f"  1. Set this as default provider: aicmd --set-config default_provider {provider}"
            )
            print(
                f"  2. Configure model: aicmd --set-config providers.{provider}.model <model_name>"
            )
            print(f"  3. Test the configuration: aicmd --test-provider {provider}")
            return

        success = KeyringManager.set_api_key(provider, api_key)

        if success:
            print(f"✓ API key set successfully for provider: {provider}")
            print("  The key is stored securely in your system keyring")
            print("\nNext steps:")
            print(
                f"  1. Set this as default provider: aicmd --set-config default_provider {provider}"
            )
            print(
                f"  2. Configure model: aicmd --set-config providers.{provider}.model <model_name>"
            )
            print(f"  3. Test the configuration: aicmd --test-provider {provider}")
        else:
            env_var = _env_var_name(provider)
            print(f"✗ Failed to set API key for provider: {provider}")
            print("  If keyring is unavailable, use environment variable instead:")
            print(f"    export {env_var}=<your_api_key>")

    except Exception as e:
        print(f"Error setting API key: {e}")


def get_api_key_command(provider: str):
    """检查提供商是否已设置 API Key"""
    try:
        from ..keyring_manager import KeyringManager
        from ..llm_router import LLMRouter

        router = LLMRouter()
        supported_providers = router.list_providers()

        if provider not in supported_providers:
            print(f"✗ Unknown provider: {provider}")
            print(f"Supported providers: {', '.join(supported_providers)}")
            return

        api_key = KeyringManager.get_api_key(provider)

        if api_key:
            # 显示前10字符，key小于 10 则显示前三个
            masked_key_len = 10 if len(api_key) > 10 else 3
            if len(api_key) > masked_key_len:
                masked_key = api_key[:masked_key_len] + "*" * (len(api_key) - masked_key_len)
            else:
                masked_key = "*" * len(api_key)

            print(f"✓ API key is configured for provider: {provider}")
            print(f"  Key preview: {masked_key}")
        else:
            print(f"✗ No API key configured for provider: {provider}")
            print(f"  Use: aicmd --set-api-key {provider} <your_api_key>")

    except Exception as e:
        print(f"Error checking API key: {e}")


def delete_api_key_command(provider: str):
    """删除提供商的 API Key"""
    try:
        from ..keyring_manager import KeyringManager
        from ..llm_router import LLMRouter

        router = LLMRouter()
        supported_providers = router.list_providers()

        if provider not in supported_providers:
            print(f"✗ Unknown provider: {provider}")
            print(f"Supported providers: {', '.join(supported_providers)}")
            return

        success = KeyringManager.delete_api_key(provider)

        if success:
            print(f"✓ API key deleted for provider: {provider}")
        else:
            print(f"⚠ No API key found for provider: {provider}")

    except Exception as e:
        print(f"Error deleting API key: {e}")


def list_api_keys_command():
    """列出所有已配置 API Key 的提供商"""
    try:
        from ..keyring_manager import KeyringManager, _env_var_name
        from ..llm_router import LLMRouter

        providers_with_keys = KeyringManager.list_providers_with_keys()
        known_providers = LLMRouter().list_providers()

        print("=== Configured API Keys ===")

        if not KeyringManager.is_keyring_available():
            print("⚠ System keyring is not available. Reading from environment variables.")
            print(
                "  Set keys via: export AICMD_API_KEY_<PROVIDER_UPPER>=<your_key>"
            )
            print()

        if providers_with_keys:
            print("Providers with API keys configured:")
            for provider in providers_with_keys:
                source = "(env var)" if not KeyringManager.is_keyring_available() else "(keyring)"
                print(f"  ✓ {provider} {source}")
            print(f"\nTotal: {len(providers_with_keys)} provider(s)")
        else:
            print("No API keys configured yet")
            print("\nTo set an API key:")
            if KeyringManager.is_keyring_available():
                print("  aicmd --set-api-key <provider> <your_api_key>")
            else:
                print("  System keyring is not available. Use environment variables:")
                for p in known_providers:
                    print(f"    export {_env_var_name(p)}=<your_key>")
            print("\nSupported providers:")
            print(f"  {', '.join(known_providers)}")

    except Exception as e:
        print(f"Error listing API keys: {e}")
