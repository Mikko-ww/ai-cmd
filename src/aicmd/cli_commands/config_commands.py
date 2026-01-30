"""
Configuration Management Commands

Handles all configuration-related CLI commands.
"""

from ..config_manager import ConfigManager
from .. import __version__, __author__


def show_detailed_configuration():
    """显示详细配置摘要"""
    try:
        config = ConfigManager()
        config.print_config_summary()
    except Exception as e:
        print(f"Error displaying detailed configuration: {e}")


def create_user_configuration(is_force=False):
    """创建用户配置文件"""
    try:
        config = ConfigManager()
        config_file = config.create_user_config(is_force=is_force)

        if not config_file:
            print("✗ Failed to create user configuration file.")

        # if config_file:
        #     print(f"✓ User configuration file created: {config_file}")
        #     print("You can now edit this file to customize your settings.")
        #     print("Run 'aicmd --show-config' to see the current configuration.")
        # else:
        #     print("✗ Failed to create user configuration file.")
    except Exception as e:
        print(f"Error creating user configuration: {e}")


def set_configuration_value(key: str, value: str, degradation_manager):
    """设置配置值"""
    try:
        config = ConfigManager()

        # 验证配置键是否存在于默认配置中
        if not config.is_valid_config_key(key):
            print(f"✗ Invalid configuration key: {key}")
            print("Run 'aicmd --show-config' to see available configuration keys.")
            return

        # 转换值类型
        converted_value = config.convert_config_value(key, value)
        if converted_value is None:
            print(f"✗ Invalid value '{value}' for key '{key}'")
            return

        # 设置配置值
        success = config.set_config(key, converted_value)
        if success:
            print(f"✓ Configuration updated: {key} = {converted_value}")
            print("Changes will take effect on next run.")
        else:
            print(f"✗ Failed to update configuration for key: {key}")

    except Exception as e:
        degradation_manager.logger.error(f"Set config failed: {e}")
        print(f"✗ Failed to set configuration: {e}")


def validate_configuration():
    """验证当前配置"""
    try:
        config = ConfigManager()
        validation_result = config.validate_config()

        print("=== Configuration Validation ===")

        if validation_result["errors"]:
            print("Configuration Errors:")
            for error in validation_result["errors"]:
                print(f"  ✗ {error}")

        if validation_result["warnings"]:
            print("Configuration Warnings:")
            for warning in validation_result["warnings"]:
                print(f"  ⚠ {warning}")

        if not validation_result["errors"] and not validation_result["warnings"]:
            print("✓ Configuration is valid with no issues.")

        print(
            f"\nOverall Status: {'✗ Invalid' if validation_result['errors'] else '✓ Valid'}"
        )

    except Exception as e:
        print(f"Error validating configuration: {e}")


def show_configuration(degradation_manager):
    """显示当前配置信息"""
    try:
        from ..keyring_manager import KeyringManager

        config = ConfigManager()

        print("=== AI Command Tool Configuration ===")
        print(f"Version: {__version__}")
        print(f"Author: {__author__}")

        # 基本配置
        print("\nBasic Configuration:")
        print(f"  Interactive Mode: {config.get('interactive_mode', False)}")
        print(f"  Cache Enabled: {config.get('cache_enabled', True)}")
        print(f"  Auto Copy Threshold: {config.get('auto_copy_threshold', 0.9)}")
        print(
            f"  Manual Confirmation Threshold: {config.get('manual_confirmation_threshold', 0.8)}"
        )

        # API配置 - 从 keyring 读取 API keys
        providers = config.get("providers", {})
        default_provider = config.get("default_provider", "openrouter")

        print("\nAPI Configuration:")
        if providers:
            print(f"  Default Provider: {default_provider}")
            for provider_name, provider_config in providers.items():
                # 从 keyring 获取 API key 状态
                has_api_key = KeyringManager.has_api_key(provider_name)
                model = provider_config.get("model", "")
                print(f"  {provider_name}:")
                print(
                    f"    API Key: {'✓ Set (in keyring)' if has_api_key else '✗ Not set'}"
                )
                print(f"    Model: {model or 'Not set'}")
        else:
            print("  No providers configured")

        # 缓存配置
        print("\nCache Configuration:")
        print(f"  Cache Directory: {config.get('cache_directory', '~/.ai-cmd')}")
        print(f"  Database File: {config.get('database_file', 'cache.db')}")
        print(f"  Max Cache Age (days): {config.get('max_cache_age_days', 30)}")

        # 交互配置
        print("\nInteraction Configuration:")
        print(
            f"  Interaction Timeout (seconds): {config.get('interaction_timeout_seconds', 10)}"
        )
        print(f"  Max Retries: {config.get('max_retries', 3)}")

        # 系统状态
        error_stats = degradation_manager.get_status()
        print("\nSystem Status:")
        print(
            f"  Health Status: {'✓ Healthy' if degradation_manager.is_healthy() else '⚠ Degraded'}"
        )
        print(
            f"  Error Count: {error_stats['error_count']}/{error_stats['max_error_count']}"
        )
        print(f"  Cache Available: {'✓' if error_stats['cache_available'] else '✗'}")
        print(
            f"  Database Available: {'✓' if error_stats['database_available'] else '✗'}"
        )

        # API Key 管理提示
        print("\nAPI Key Management:")
        print("  API keys are stored securely in system keyring")
        print("  Use 'aicmd --set-api-key <provider> <key>' to configure")
        print("  Use 'aicmd --list-api-keys' to see configured providers")

    except Exception as e:
        print(f"Error displaying configuration: {e}")
