import os
import argparse
import pyperclip
from . import __version__, __author__, __email__
from .error_handler import GracefulDegradationManager
from .config_manager import ConfigManager
from .cache_manager import CacheManager
from .confidence_calculator import ConfidenceCalculator
from .query_matcher import QueryMatcher
from .interactive_manager import InteractiveManager, ConfirmationResult
from .multi_provider_api_client import MultiProviderAPIClient
from .safety_checker import CommandSafetyChecker
from .logger import logger

# 全局错误处理管理器
degradation_manager = GracefulDegradationManager()


def get_version_info():
    """获取版本信息字符串"""
    return f"""AI Command Line Tool v{__version__}
Author: {__author__} ({__email__})
Repository: https://github.com/Mikko-ww/ai-cmd
License: MIT"""


def get_shell_command_original(prompt, base_url=None):
    """原始的获取shell命令函数，用于向后兼容和降级"""

    def main_api_operation():
        api_client = MultiProviderAPIClient(
            degradation_manager=degradation_manager, base_url=base_url
        )
        return api_client.send_chat_with_fallback(prompt)

    def fallback_operation():
        return "Error: Unable to process request due to system issues."

    # 使用错误处理机制保护API调用
    return degradation_manager.with_cache_fallback(
        main_api_operation, fallback_operation, "get_shell_command_original"
    )


def get_shell_command(
    prompt,
    force_api=False,
    no_clipboard=False,
    no_color=False,
    json_output=False,
    base_url=None,
):
    """增强的获取shell命令函数，集成缓存、置信度判断和用户交互"""

    # 初始化配置管理器
    config = ConfigManager()

    # 检查是否启用交互模式
    if not config.get("interactive_mode", False) or force_api:
        # 交互模式未启用或强制使用API，使用原始功能
        command = get_shell_command_original(prompt, base_url=base_url)
        if command:
            logger.info(command)

            # 安全检查
            safety_checker = CommandSafetyChecker(config)
            safety_info = safety_checker.get_safety_info(command)

            # 显示安全警告
            if safety_info["is_dangerous"] and safety_info["warnings"]:
                for warning in safety_info["warnings"]:
                    print(warning)

            # 复制到剪贴板（考虑安全和用户选择）
            if not no_clipboard and not safety_info["disable_auto_copy"]:
                try:
                    pyperclip.copy(command)
                    # 在非交互模式下显示复制确认
                    print("✓ Copied to clipboard!")
                except Exception as e:
                    degradation_manager.logger.warning(
                        f"Failed to copy to clipboard: {e}"
                    )
            elif safety_info["disable_auto_copy"]:
                print("⚠️  Automatic clipboard copying disabled for safety reasons")
        return command

    # 初始化所有管理器
    try:
        cache_manager = CacheManager(config, degradation_manager)
        confidence_calc = ConfidenceCalculator(
            config, cache_manager, degradation_manager
        )
        query_matcher = QueryMatcher()
        interactive_manager = InteractiveManager(
            config, degradation_manager, no_color=no_color
        )

        # 查找精确匹配的缓存
        cached_entry = cache_manager.find_exact_match(prompt)

        command = None
        source = "API"
        confidence = 0.0
        similarity = 0.0
        api_command = None

        if cached_entry:
            # 找到缓存条目，计算置信度
            confidence = confidence_calc.calculate_confidence(
                cached_entry.confirmation_count,
                cached_entry.rejection_count,
                cached_entry.created_at,
                cached_entry.last_used,
            )

            # 在做决策前优先展示指标（精确匹配场景按用户期望显示 Similarity: 0.0%）
            interactive_manager.display_metrics(confidence, 0.0)

            # 根据置信度决定处理方式
            auto_copy_threshold = float(config.get("auto_copy_threshold", 0.9) or 0.9)

            # 安全检查（提前进行以影响自动复制决策）
            safety_checker = CommandSafetyChecker(config)
            safety_info = safety_checker.get_safety_info(cached_entry.command or "")

            if (
                confidence >= auto_copy_threshold
                and not safety_info["force_confirmation"]
            ):
                # 高置信度且不强制确认：直接使用缓存并自动复制
                command = cached_entry.command or ""
                source = "Cache (High Confidence)"
                if command:
                    logger.info(command)

                # 显示安全警告（如果有）
                if safety_info["is_dangerous"] and safety_info["warnings"]:
                    print()
                    for warning in safety_info["warnings"]:
                        print(warning)
                    print()

                if not no_clipboard and not safety_info["disable_auto_copy"]:
                    try:
                        pyperclip.copy(command)
                        interactive_manager.display_success_message(
                            command, copied=True
                        )
                    except Exception as e:
                        degradation_manager.logger.warning(
                            f"Failed to copy to clipboard: {e}"
                        )
                        interactive_manager.display_success_message(
                            command, copied=False
                        )
                else:
                    interactive_manager.display_success_message(command, copied=False)
                    if safety_info["disable_auto_copy"]:
                        print("⚠️  Clipboard copying disabled for safety reasons")

                # 更新使用时间和隐式确认
                try:
                    qh = (
                        cached_entry.query_hash
                        or cache_manager.db.generate_query_hash(prompt)
                    )
                    cache_manager.update_last_used(qh)
                    confidence_calc.update_feedback(qh, command or "", True, 1.0)
                except Exception:
                    pass

                return command

            confidence_threshold = float(config.get("confidence_threshold", 0.8) or 0.8)
            if confidence >= confidence_threshold:
                # 中等置信度：使用缓存但询问用户确认
                command = cached_entry.command or ""
                source = "Cache"
                similarity = 1.0  # 精确匹配
            else:
                # 低置信度：调用API获取新命令
                interactive_manager.display_info("API 请求中...", color="blue")
                api_command = get_shell_command_original(prompt, base_url=base_url)
                if not api_command or api_command.startswith("Error:"):
                    # API调用失败，使用缓存作为备选
                    command = cached_entry.command or ""
                    source = "Cache (API Failed)"
                else:
                    command = api_command
                    source = "API"

        else:
            # 没有找到精确匹配，查找相似的缓存
            all_cached_queries = cache_manager.get_all_cached_queries()

            if all_cached_queries:
                similarity_threshold = float(
                    config.get("similarity_threshold", 0.7) or 0.7
                )
                similar_queries = query_matcher.find_similar_queries(
                    prompt, all_cached_queries, threshold=similarity_threshold
                )

                if similar_queries:
                    # 找到相似查询，使用最相似的一个
                    best_match = similar_queries[0]  # 已按相似度排序
                    cached_query, cached_command, similarity = best_match

                    # 获取该缓存条目的详细信息
                    cached_entry = cache_manager.find_exact_match(cached_query)
                    if cached_entry:
                        confidence = confidence_calc.calculate_confidence(
                            cached_entry.confirmation_count,
                            cached_entry.rejection_count,
                            cached_entry.created_at,
                            cached_entry.last_used,
                        )

                        # 结合相似度和置信度
                        combined_confidence = confidence * similarity

                        # 在做决策前优先展示指标（使用当前的 confidence/similarity）
                        interactive_manager.display_metrics(confidence, similarity)

                        confidence_threshold = float(
                            config.get("confidence_threshold", 0.8) or 0.8
                        )
                        if combined_confidence >= confidence_threshold:
                            command = cached_command
                            source = "Similar Cache"
                        else:
                            # 相似度或置信度不够，调用API
                            if api_command is None:
                                interactive_manager.display_info(
                                    "API 请求中...", color="blue"
                                )
                                api_command = get_shell_command_original(prompt)
                            command = api_command
                            source = "API"
                    else:
                        # 相似匹配失败，打印默认指标再请求 API
                        interactive_manager.display_metrics(0.0, 0.0)
                        if api_command is None:
                            interactive_manager.display_info(
                                "API 请求中...", color="blue"
                            )
                            api_command = get_shell_command_original(
                                prompt, base_url=base_url
                            )
                        command = api_command
                        source = "API"
                else:
                    # 没有找到相似查询，打印默认指标再调用API
                    interactive_manager.display_metrics(0.0, 0.0)
                    if api_command is None:
                        interactive_manager.display_info("API 请求中...", color="blue")
                        api_command = get_shell_command_original(
                            prompt, base_url=base_url
                        )
                    command = api_command
                    source = "API"
            else:
                # 没有任何缓存，打印默认指标再调用API
                interactive_manager.display_metrics(0.0, 0.0)
                if api_command is None:
                    interactive_manager.display_info("API 请求中...", color="blue")
                    api_command = get_shell_command_original(prompt, base_url=base_url)
                command = api_command
                source = "API"

        # 验证命令有效性
        if not command or command.startswith("Error:"):
            print(f"Failed to get valid command: {command}")
            return command

        # 安全检查
        safety_checker = CommandSafetyChecker(config)
        safety_info = safety_checker.get_safety_info(command)

        # 显示安全警告
        if safety_info["is_dangerous"] and safety_info["warnings"]:
            print()  # 添加空行提高可读性
            for warning in safety_info["warnings"]:
                print(warning)
            print()  # 添加空行

        # 用户交互确认
        need_confirmation = (
            interactive_manager.should_prompt_for_confirmation(confidence)
            or safety_info["force_confirmation"]
        )

        if need_confirmation:
            # 询问用户确认
            # 为避免重复打印指标，这里不再传入 confidence/similarity
            result, details = interactive_manager.prompt_user_confirmation(
                command, source, None, None
            )

            confirmed = result == ConfirmationResult.CONFIRMED

            if confirmed:
                # 用户确认，复制到剪贴板（考虑安全和用户选择）
                if not no_clipboard and not safety_info["disable_auto_copy"]:
                    try:
                        pyperclip.copy(command)
                        interactive_manager.display_success_message(
                            command, copied=True
                        )
                    except Exception as e:
                        degradation_manager.logger.warning(
                            f"Failed to copy to clipboard: {e}"
                        )
                        interactive_manager.display_success_message(
                            command, copied=False
                        )
                else:
                    interactive_manager.display_success_message(command, copied=False)
                    if safety_info["disable_auto_copy"]:
                        print("⚠️  Clipboard copying disabled for safety reasons")
            else:
                # 用户拒绝
                interactive_manager.display_rejection_message("Command not copied")

            # 超时也视为确认
            if result == ConfirmationResult.TIMEOUT:
                confirmed = True
        else:
            # 不需要确认，直接复制（考虑安全和用户选择）
            confirmed = True
            if not no_clipboard and not safety_info["disable_auto_copy"]:
                try:
                    pyperclip.copy(command)
                    interactive_manager.display_success_message(command, copied=True)
                except Exception as e:
                    degradation_manager.logger.warning(
                        f"Failed to copy to clipboard: {e}"
                    )
                    interactive_manager.display_success_message(command, copied=False)
            else:
                interactive_manager.display_success_message(command, copied=False)
                if safety_info["disable_auto_copy"]:
                    print("⚠️  Clipboard copying disabled for safety reasons")

        # 保存到缓存（如果是新命令）
        if source == "API":
            cache_manager.save_cache_entry(prompt, command)

        # 更新反馈和置信度
        # 使用数据库统一哈希以确保可查到记录
        current_query_hash = cache_manager.db.generate_query_hash(prompt)
        confidence_calc.update_feedback(
            current_query_hash, command, confirmed, similarity
        )

        # 如果请求JSON输出，返回结构化数据
        if json_output:
            import json

            result_data = {
                "command": command,
                "source": source,
                "confidence": confidence,
                "similarity": similarity if similarity is not None else 0.0,
                "dangerous": safety_info.get("is_dangerous", False),
                "confirmed": confirmed,
            }
            print(json.dumps(result_data, indent=2, ensure_ascii=False))
            return result_data

        return command

    except Exception as e:
        # 任何异常都降级到原始功能
        degradation_manager.logger.error(f"Enhanced shell command error: {e}")

        if json_output:
            import json

            fallback_result = get_shell_command_original(prompt, base_url=base_url)
            error_data = {
                "command": fallback_result,
                "source": "FALLBACK",
                "confidence": 0.0,
                "similarity": 0.0,
                "dangerous": False,
                "confirmed": False,
                "warning": "Enhanced features failed, using basic mode",
            }
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
            return error_data
        else:
            print(f"Warning: Enhanced features failed, using basic mode: {e}")
            return get_shell_command_original(prompt, base_url=base_url)


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

        # 解析命令行参数
        args = parser.parse_args()

        # 处理配置显示
        if args.config:
            show_configuration()
            return

        if args.show_config:
            show_detailed_configuration()
            return

        if args.create_config:
            create_user_configuration(is_force=False)
            return

        if args.create_config_force:
            create_user_configuration(is_force=True)
            return

        if args.validate_config:
            validate_configuration()
            return

        if args.set_config:
            set_configuration_value(args.set_config[0], args.set_config[1])
            return

        # 处理特殊命令
        if args.reset_errors:
            degradation_manager.force_reset()
            print("✓ Error state has been reset.")
            return

        if args.status:
            print_system_status()
            return

        if args.recalculate_confidence:
            recalculate_all_confidence_command()
            return

        if args.cleanup_cache:
            cleanup_cache_command()
            return

        if args.list_providers:
            list_providers_command()
            return
            
        if args.test_provider:
            test_provider_command(args.test_provider)
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


def set_configuration_value(key: str, value: str):
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


def cleanup_cache_command():
    """执行缓存清理命令"""
    try:
        from .database_manager import SafeDatabaseManager
        from .config_manager import ConfigManager

        print("=== Cleaning Up Cache ===")

        config = ConfigManager()
        db_manager = SafeDatabaseManager(config_manager=config)

        if not db_manager.is_available:
            print("✗ Database not available for cleanup")
            return

        deleted_count = db_manager.cleanup_old_entries()

        if deleted_count > 0:
            print(f"✓ Cache cleanup completed. Removed {deleted_count} entries.")
        else:
            print("ℹ No entries needed cleanup")

    except Exception as e:
        degradation_manager.logger.error(f"Cache cleanup failed: {e}")
        print(f"✗ Failed to clean up cache: {e}")


def recalculate_all_confidence_command():
    """执行批量置信度重算命令"""
    try:
        from .cache_manager import CacheManager
        from .confidence_calculator import ConfidenceCalculator
        from .config_manager import ConfigManager

        print("=== Recalculating Confidence Scores ===")

        config = ConfigManager()
        cache_manager = CacheManager(
            config_manager=config, degradation_manager=degradation_manager
        )
        confidence_calc = ConfidenceCalculator(
            config_manager=config,
            cache_manager=cache_manager,
            degradation_manager=degradation_manager,
        )

        updated_count = confidence_calc.recalculate_all_confidence()

        if updated_count > 0:
            print(f"✓ Successfully recalculated confidence for {updated_count} entries")
        else:
            print("ℹ No entries found to recalculate")

    except Exception as e:
        degradation_manager.logger.error(f"Confidence recalculation failed: {e}")
        print(f"✗ Failed to recalculate confidence scores: {e}")


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


def show_configuration():
    """显示当前配置信息"""
    try:
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

        # API配置 - 从配置文件读取
        providers = config.get("providers", {})
        default_provider = config.get("default_provider", "openrouter")
        
        print("\nAPI Configuration:")
        if providers:
            print(f"  Default Provider: {default_provider}")
            for provider_name, provider_config in providers.items():
                api_key = provider_config.get("api_key", "")
                model = provider_config.get("model", "")
                print(f"  {provider_name}:")
                print(f"    API Key: {'✓ Set' if api_key else '✗ Not set'}")
                print(f"    Model: {model or 'Not set'}")
        else:
            print("  No providers configured")
        print(f"  use_backup_model: {config.get('use_backup_model', False)}")

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

    except Exception as e:
        print(f"Error displaying configuration: {e}")


def print_system_status():
    """显示系统统计信息"""
    try:
        config = ConfigManager()

        print("=== AI Command Tool Statistics ===")
        print(f"Interactive Mode: {config.get('interactive_mode', False)}")
        print(f"Cache Enabled: {config.get('cache_enabled', True)}")

        # 缓存统计
        try:
            cache_manager = CacheManager(config, degradation_manager)
            cache_stats = cache_manager.get_cache_stats()
            print(f"\nCache Statistics:")
            print(f"  Status: {cache_stats.get('status', 'unknown')}")
            print(f"  Total Entries: {cache_stats.get('total_entries', 0)}")
        except Exception as e:
            print(f"\nCache Statistics: Error - {e}")

        # 置信度统计
        try:
            cache_manager = CacheManager(config, degradation_manager)
            confidence_calc = ConfidenceCalculator(
                config, cache_manager, degradation_manager
            )
            conf_stats = confidence_calc.get_confidence_stats()
            if conf_stats.get("status") == "available":
                print(f"\nConfidence Statistics:")
                print(
                    f"  Average Confidence: {conf_stats.get('avg_confidence', 0):.3f}"
                )
                print(
                    f"  Total Confirmations: {conf_stats.get('total_confirmations', 0)}"
                )
                print(f"  Total Rejections: {conf_stats.get('total_rejections', 0)}")
                print(
                    f"  High Confidence (≥0.9): {conf_stats.get('very_high_confidence_count', 0)}"
                )
                print(
                    f"  Medium Confidence (0.8-0.9): {conf_stats.get('high_confidence_count', 0)}"
                )
        except Exception as e:
            print(f"\nConfidence Statistics: Error - {e}")

        # 交互统计
        try:
            interactive_manager = InteractiveManager(config, degradation_manager)
            int_stats = interactive_manager.get_interaction_stats()
            if int_stats.get("total_prompts", 0) > 0:
                print(f"\nInteraction Statistics:")
                print(f"  Total Prompts: {int_stats.get('total_prompts', 0)}")
                print(
                    f"  Confirmed: {int_stats.get('confirmed', 0)} ({int_stats.get('confirmed_percentage', 0)}%)"
                )
                print(
                    f"  Rejected: {int_stats.get('rejected', 0)} ({int_stats.get('rejected_percentage', 0)}%)"
                )
                print(
                    f"  Timeouts: {int_stats.get('timeouts', 0)} ({int_stats.get('timeouts_percentage', 0)}%)"
                )
            else:
                print(f"\nInteraction Statistics: No interactions yet")
        except Exception as e:
            print(f"\nInteraction Statistics: Error - {e}")

        # 错误处理统计
        error_stats = degradation_manager.get_status()
        print(f"\nError Handler Status:")
        print(
            f"  Health Status: {'Healthy' if degradation_manager.is_healthy() else 'Degraded'}"
        )
        print(
            f"  Error Count: {error_stats['error_count']}/{error_stats['max_error_count']}"
        )
        print(f"  Cache Available: {error_stats['cache_available']}")
        print(f"  Database Available: {error_stats['database_available']}")

    except Exception as e:
        print(f"Error displaying statistics: {e}")


def list_providers_command():
    """列出所有支持的LLM提供商"""
    try:
        from .llm_router import LLMRouter
        
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
        from .llm_router import LLMRouter
        
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
        print(f"  1. Use: aicmd --create-config")
        print(f"  2. Edit your config file (~/.ai-cmd/settings.json)")
        print(f"  3. Set providers.{provider_name}.api_key and providers.{provider_name}.model")
        
    except Exception as e:
        print(f"Error testing provider: {e}")


if __name__ == "__main__":
    main()
