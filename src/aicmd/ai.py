import os
import argparse
from . import __version__, __author__, __email__
from .error_handler import GracefulDegradationManager
from .config_manager import ConfigManager
from .cache_manager import CacheManager
from .confidence_calculator import ConfidenceCalculator
from .interactive_manager import InteractiveManager, ConfirmationResult
from .command_handler import CommandHandler
from .logger import logger
from .cli_commands import config_commands, cache_commands, provider_commands

# 全局错误处理管理器
degradation_manager = GracefulDegradationManager()

# 全局命令处理器
command_handler = CommandHandler(degradation_manager)


def get_version_info():
    """获取版本信息字符串"""
    return f"""AI Command Line Tool v{__version__}
Author: {__author__} ({__email__})
Repository: https://github.com/Mikko-ww/ai-cmd
License: MIT"""


def get_shell_command_original(prompt, base_url=None):
    """原始的获取shell命令函数，用于向后兼容和降级"""
    return command_handler.get_command_original(prompt, base_url)


def get_shell_command(
    prompt,
    force_api=False,
    no_clipboard=False,
    no_color=False,
    json_output=False,
    base_url=None,
):
    """增强的获取shell命令函数，集成缓存、置信度判断和用户交互"""
    return command_handler.get_command(
        prompt, force_api, no_clipboard, no_color, json_output, base_url
    )


def main():
    """主函数，集成智能缓存和用户交互功能"""
    try:
        # 创建ArgumentParser实例
        parser = argparse.ArgumentParser(
            description=f"AI Command Line Tool v{__version__} - Convert natural language to shell commands",
            prog="aicmd",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  aicmd "list all files"
  aicmd "create new directory" --force-api
  aicmd --status
  aicmd --config
            """,
        )

        # 添加版本信息选项
        parser.add_argument(
            "-v",
            "--version",
            action="version",
            version=get_version_info(),
            help="Show version information",
        )

        # 添加配置管理选项
        parser.add_argument(
            "--config", action="store_true", help="Show current configuration"
        )
        parser.add_argument(
            "--show-config",
            action="store_true",
            help="Show detailed configuration summary",
        )
        parser.add_argument(
            "--create-config",
            action="store_true",
            help="Create user configuration file",
        )

        parser.add_argument(
            "--create-config-force",
            action="store_true",
            help="Force create user configuration file",
        )

        parser.add_argument(
            "--validate-config",
            action="store_true",
            help="Validate current configuration",
        )

        # 添加设置配置选项
        parser.add_argument(
            "--set-config",
            nargs=2,
            metavar=("KEY", "VALUE"),
            help="Set a configuration key to a specific value (e.g., --set-config interactive_mode true)",
        )

        # 添加现有的所有参数
        parser.add_argument(
            "prompt", nargs="*", help="Natural language prompt for command generation"
        )
        parser.add_argument(
            "--force-api", action="store_true", help="Force API call, bypass cache"
        )
        parser.add_argument(
            "--disable-interactive",
            action="store_true",
            help="Disable interactive mode for this request",
        )
        parser.add_argument(
            "--status",
            action="store_true",
            help="Show cache and interaction statistics",
        )
        parser.add_argument(
            "--reset-errors", action="store_true", help="Reset error state"
        )
        parser.add_argument(
            "--no-color", action="store_true", help="Disable colored output"
        )
        parser.add_argument(
            "--log-level",
            type=str,
            help="Override console log level (e.g., DEBUG, INFO, WARNING, ERROR)",
        )
        parser.add_argument(
            "--file-log-level",
            type=str,
            help="Override file log level (e.g., DEBUG, INFO, WARNING, ERROR)",
        )
        parser.add_argument(
            "--log-dir",
            type=str,
            help="Override log directory (e.g., ~/.ai-cmd/logs)",
        )
        parser.add_argument(
            "--no-clipboard", action="store_true", help="Disable clipboard integration"
        )
        parser.add_argument(
            "--recalculate-confidence",
            action="store_true",
            help="Recalculate confidence scores for all cached commands",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output results in JSON format with detailed metadata",
        )
        parser.add_argument(
            "--base-url", type=str, help="Override API base URL (useful for proxies)"
        )
        parser.add_argument(
            "--cleanup-cache",
            action="store_true",
            help="Clean up expired and oversized cache entries",
        )

        # Provider management options
        parser.add_argument(
            "--list-providers",
            action="store_true",
            help="List all supported LLM providers",
        )

        parser.add_argument(
            "--test-provider",
            type=str,
            help="Test configuration for a specific provider",
        )

        # API Key management options
        parser.add_argument(
            "--set-api-key",
            nargs=2,
            metavar=("PROVIDER", "API_KEY"),
            help="Set API key for a provider (stored securely in system keyring)",
        )

        parser.add_argument(
            "--get-api-key",
            type=str,
            metavar="PROVIDER",
            help="Check if API key is set for a provider (does not display the key)",
        )

        parser.add_argument(
            "--delete-api-key",
            type=str,
            metavar="PROVIDER",
            help="Delete API key for a provider from keyring",
        )

        parser.add_argument(
            "--list-api-keys",
            action="store_true",
            help="List all providers with API keys configured",
        )

        # 解析命令行参数
        args = parser.parse_args()

        # 配置日志（CLI > 环境变量 > 配置文件 > 默认值）
        try:
            config_for_logging = ConfigManager()
            logger.configure(
                log_dir=args.log_dir,
                console_level=args.log_level,
                file_level=args.file_log_level,
                config={
                    "log_level": config_for_logging.get("log_level"),
                    "file_log_level": config_for_logging.get("file_log_level"),
                    "log_dir": config_for_logging.get("log_dir"),
                },
                use_color=not args.no_color,
            )
        except Exception as e:
            print(f"Warning: Failed to configure logger from config: {e}")

        # 处理配置显示
        if args.config:
            config_commands.show_configuration(degradation_manager)
            return

        if args.show_config:
            config_commands.show_detailed_configuration()
            return

        if args.create_config:
            config_commands.create_user_configuration(is_force=False)
            return

        if args.create_config_force:
            config_commands.create_user_configuration(is_force=True)
            return

        if args.validate_config:
            config_commands.validate_configuration()
            return

        if args.set_config:
            config_commands.set_configuration_value(
                args.set_config[0], args.set_config[1], degradation_manager
            )
            return

        # 处理特殊命令
        if args.reset_errors:
            degradation_manager.force_reset()
            print("✓ Error state has been reset.")
            return

        if args.status:
            cache_commands.print_system_status(degradation_manager)
            return

        if args.recalculate_confidence:
            cache_commands.recalculate_all_confidence_command(degradation_manager)
            return

        if args.cleanup_cache:
            cache_commands.cleanup_cache_command(degradation_manager)
            return

        if args.list_providers:
            provider_commands.list_providers_command()
            return

        if args.test_provider:
            provider_commands.test_provider_command(args.test_provider)
            return

        # API Key management commands
        if args.set_api_key:
            provider_commands.set_api_key_command(args.set_api_key[0], args.set_api_key[1])
            return

        if args.get_api_key:
            provider_commands.get_api_key_command(args.get_api_key)
            return

        if args.delete_api_key:
            provider_commands.delete_api_key_command(args.delete_api_key)
            return

        if args.list_api_keys:
            provider_commands.list_api_keys_command()
            return

        # 检查是否有实际的查询
        if not args.prompt:
            print("Error: No query provided. Use --help for usage information.")
            return

        prompt = " ".join(args.prompt)

        # 临时禁用交互模式
        force_api = args.force_api
        if args.disable_interactive:
            force_api = True

        # 获取命令
        command = get_shell_command(
            prompt,
            force_api=force_api,
            no_clipboard=args.no_clipboard,
            no_color=args.no_color,
            json_output=args.json,
            base_url=args.base_url,
        )
        if not command:
            if args.json:
                import json

                error_data = {"error": "No command generated", "command": None}
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
            else:
                print("Error: No command generated.")

    except KeyboardInterrupt:
        print("\n✗ Operation cancelled by user.")
    except Exception as e:
        # 捕获所有未处理的异常
        degradation_manager.logger.error(f"Unhandled error in main: {e}")
        print("Error: An unexpected error occurred. Please try again.")

        # 如果错误太多，显示状态信息
        if not degradation_manager.is_healthy():
            status = degradation_manager.get_status()
            print(
                f"System health status: Error count {status['error_count']}/{status['max_error_count']}"
            )
            print("Consider running with --reset-errors to reset error state.")


if __name__ == "__main__":
    main()
