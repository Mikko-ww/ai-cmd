"""
Cache Management Commands

Handles all cache-related CLI commands.
"""

from ..config_manager import ConfigManager
from ..cache_manager import CacheManager
from ..confidence_calculator import ConfidenceCalculator
from ..interactive_manager import InteractiveManager


def cleanup_cache_command(degradation_manager):
    """执行缓存清理命令"""
    try:
        from ..database_manager import SafeDatabaseManager

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


def recalculate_all_confidence_command(degradation_manager):
    """执行批量置信度重算命令"""
    try:
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


def print_system_status(degradation_manager):
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
