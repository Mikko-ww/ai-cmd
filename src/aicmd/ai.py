import os
import argparse
import pyperclip
from dotenv import load_dotenv
from . import __version__, __author__, __email__
from .error_handler import GracefulDegradationManager
from .config_manager import ConfigManager
from .cache_manager import CacheManager
from .confidence_calculator import ConfidenceCalculator
from .query_matcher import QueryMatcher
from .interactive_manager import InteractiveManager, ConfirmationResult
from .api_client import OpenRouterAPIClient
from .safety_checker import CommandSafetyChecker
from .logger import logger

load_dotenv()

# 全局错误处理管理器
degradation_manager = GracefulDegradationManager()


def get_version_info():
    """获取版本信息字符串"""
    return f"""AI Command Line Tool v{__version__}
Author: {__author__} ({__email__})
Repository: https://github.com/Mikko-ww/ai-cmd
License: MIT"""


def get_shell_command_original(prompt):
    """原始的获取shell命令函数，用于向后兼容和降级"""
    
    def main_api_operation():
        api_client = OpenRouterAPIClient(degradation_manager=degradation_manager)
        return api_client.send_chat_with_fallback(prompt)

    def fallback_operation():
        return "Error: Unable to process request due to system issues."

    # 使用错误处理机制保护API调用
    return degradation_manager.with_cache_fallback(
        main_api_operation, fallback_operation, "get_shell_command_original"
    )


def get_shell_command(prompt, force_api=False, no_clipboard=False, no_color=False):
    """增强的获取shell命令函数，集成缓存、置信度判断和用户交互"""

    # 初始化配置管理器
    config = ConfigManager()

    # 检查是否启用交互模式
    if not config.get("interactive_mode", False) or force_api:
        # 交互模式未启用或强制使用API，使用原始功能
        command = get_shell_command_original(prompt)
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
        interactive_manager = InteractiveManager(config, degradation_manager, no_color=no_color)

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
            auto_copy_threshold = float(
                config.get("auto_copy_threshold", 0.9) or 0.9
            )
            
            # 安全检查（提前进行以影响自动复制决策）
            safety_checker = CommandSafetyChecker(config)
            safety_info = safety_checker.get_safety_info(cached_entry.command or "")
            
            if confidence >= auto_copy_threshold and not safety_info["force_confirmation"]:
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

                # 更新使用时间和隐式确认
                try:
                    qh = cached_entry.query_hash or cache_manager.db.generate_query_hash(
                        prompt
                    )
                    cache_manager.update_last_used(qh)
                    confidence_calc.update_feedback(qh, command or "", True, 1.0)
                except Exception:
                    pass

                return command

            confidence_threshold = float(
                config.get("confidence_threshold", 0.8) or 0.8
            )
            if confidence >= confidence_threshold:
                # 中等置信度：使用缓存但询问用户确认
                command = cached_entry.command or ""
                source = "Cache"
                similarity = 1.0  # 精确匹配
            else:
                # 低置信度：调用API获取新命令
                interactive_manager.display_info("API 请求中...", color="blue")
                api_command = get_shell_command_original(prompt)
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
                                interactive_manager.display_info("API 请求中...", color="blue")
                                api_command = get_shell_command_original(prompt)
                            command = api_command
                            source = "API"
                    else:
                        # 相似匹配失败，打印默认指标再请求 API
                        interactive_manager.display_metrics(0.0, 0.0)
                        if api_command is None:
                            interactive_manager.display_info("API 请求中...", color="blue")
                            api_command = get_shell_command_original(prompt)
                        command = api_command
                        source = "API"
                else:
                    # 没有找到相似查询，打印默认指标再调用API
                    interactive_manager.display_metrics(0.0, 0.0)
                    if api_command is None:
                        interactive_manager.display_info("API 请求中...", color="blue")
                        api_command = get_shell_command_original(prompt)
                    command = api_command
                    source = "API"
            else:
                # 没有任何缓存，打印默认指标再调用API
                interactive_manager.display_metrics(0.0, 0.0)
                if api_command is None:
                    interactive_manager.display_info("API 请求中...", color="blue")
                    api_command = get_shell_command_original(prompt)
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
        need_confirmation = interactive_manager.should_prompt_for_confirmation(
            confidence
        ) or safety_info["force_confirmation"]

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

        return command

    except Exception as e:
        # 任何异常都降级到原始功能
        degradation_manager.logger.error(f"Enhanced shell command error: {e}")
        print(f"Warning: Enhanced features failed, using basic mode: {e}")
        return get_shell_command_original(prompt)


def main():
    """主函数，集成智能缓存和用户交互功能"""
    try:
        # 创建ArgumentParser实例
        parser = argparse.ArgumentParser(
            description="AI Command Line Tool v0.3.0 - Convert natural language to shell commands",
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

        # # 添加设置配置选项
        # parser.add_argument(
        #     "--set-config",
        #     nargs=2,
        #     metavar=("KEY", "VALUE"),
        #     help="Set a configuration key to a specific value (e.g., --set-config interactive_mode true)",
        # )

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
            "--status", action="store_true", help="Show cache and interaction statistics"
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
        
        # if args.set_config:
        #     key, value = args.set_config
        #     logger.error(f"Setting config: {key} = {value}")
        #     config = ConfigManager()
        #     config.set_config(key, value)
        #     return

        # 处理特殊命令
        if args.reset_errors:
            degradation_manager.force_reset()
            print("✓ Error state has been reset.")
            return

        if args.status:
            print_system_status()
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
        command = get_shell_command(prompt, force_api=force_api, no_clipboard=args.no_clipboard, no_color=args.no_color)
        if not command:
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

        # API配置
        api_key = os.getenv("AI_CMD_OPENROUTER_API_KEY")
        model_name = os.getenv("AI_CMD_OPENROUTER_MODEL", "Not set")
        model_name_backup = os.getenv("AI_CMD_OPENROUTER_MODEL_BACKUP", "Not set")
        print("\nAPI Configuration:")
        print(f"  API Key: {'✓ Set' if api_key else '✗ Not found'}")
        print(f"  Model: {model_name}")
        print(f"  Backup Model: {model_name_backup}")
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
            confidence_calc = ConfidenceCalculator(config, cache_manager, degradation_manager)
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


if __name__ == "__main__":
    main()
