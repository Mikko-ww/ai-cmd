"""
集成测试
测试端到端流程和模块协作
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestEndToEndCacheFlow:
    """端到端缓存流程测试"""

    def test_save_find_update_delete_flow(self, mock_cache_manager):
        """测试完整的 CRUD 流程"""
        if not mock_cache_manager.db.is_available:
            pytest.skip("Database not available")
        
        # 1. 保存缓存条目
        query = "integration test query"
        command = "integration test command"
        
        query_hash = mock_cache_manager.save_cache_entry(query, command)
        assert query_hash is not None
        
        # 2. 查找缓存条目
        entry = mock_cache_manager.find_exact_match(query)
        assert entry is not None
        assert entry.query == query
        assert entry.command == command
        
        # 3. 更新最后使用时间
        result = mock_cache_manager.update_last_used(query_hash)
        assert result is True
        
        # 4. 删除缓存条目
        result = mock_cache_manager.delete_cache_entry(query_hash)
        assert result is True
        
        # 5. 验证已删除
        entry = mock_cache_manager.find_exact_match(query)
        assert entry is None


class TestQueryMatchingIntegration:
    """查询匹配集成测试"""

    def test_similar_query_matching(self, mock_cache_manager):
        """测试相似查询匹配"""
        from aicmd.query_matcher import QueryMatcher
        
        if not mock_cache_manager.db.is_available:
            pytest.skip("Database not available")
        
        # 保存多个缓存条目
        queries = [
            ("list all files in directory", "ls -la"),
            ("show directory contents", "ls"),
            ("display files", "ls -la"),
        ]
        
        for query, command in queries:
            mock_cache_manager.save_cache_entry(query, command)
        
        # 获取所有缓存查询
        cached_queries = mock_cache_manager.get_all_cached_queries()
        
        # 使用 QueryMatcher 查找相似查询
        matcher = QueryMatcher()
        similar = matcher.find_similar_queries(
            "show all files",
            cached_queries,
            threshold=0.4
        )
        
        # 应该找到相似的查询
        assert len(similar) > 0


class TestConfidenceUpdateIntegration:
    """置信度更新集成测试"""

    def test_confidence_update_with_feedback(self, mock_cache_manager):
        """测试通过反馈更新置信度"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        if not mock_cache_manager.db.is_available:
            pytest.skip("Database not available")
        
        calculator = ConfidenceCalculator(cache_manager=mock_cache_manager)
        
        # 保存缓存条目
        query = "confidence test query"
        command = "confidence test command"
        
        query_hash = mock_cache_manager.save_cache_entry(query, command)
        
        if query_hash:
            # 更新正面反馈
            success, new_confidence = calculator.update_feedback(
                query_hash, command, confirmed=True
            )
            
            # 应该成功更新
            if success:
                # 验证置信度已更新
                entry = mock_cache_manager.find_exact_match(query)
                assert entry is not None
                assert entry.confirmation_count >= 1


class TestSafetyCheckIntegration:
    """安全检查集成测试"""

    def test_safety_check_with_confidence(self):
        """测试安全检查与置信度的集成"""
        from aicmd.safety_checker import CommandSafetyChecker
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        checker = CommandSafetyChecker()
        calculator = ConfidenceCalculator()
        
        # 危险命令
        dangerous_cmd = "rm -rf /"
        
        # 安全检查
        safety_info = checker.get_safety_info(dangerous_cmd)
        
        # 即使置信度高，危险命令也应该被标记
        assert safety_info["is_dangerous"] is True
        assert safety_info["force_confirmation"] is True
        
        # 安全命令
        safe_cmd = "ls -la"
        safety_info = checker.get_safety_info(safe_cmd)
        
        assert safety_info["is_dangerous"] is False
        assert safety_info["force_confirmation"] is False


class TestConfigurationIntegration:
    """配置集成测试"""

    def test_config_affects_behavior(self, temp_config_dir):
        """测试配置对行为的影响"""
        from aicmd.config_manager import ConfigManager
        from aicmd.confidence_calculator import ConfidenceCalculator
        import json
        
        # 创建自定义配置
        config_data = {
            "basic": {
                "cache_enabled": True,
                "auto_copy_threshold": 0.95,  # 更高的阈值
            },
            "interaction": {
                "confidence_threshold": 0.85,
                "positive_weight": 0.3,
                "negative_weight": 0.7,
            }
        }
        
        config_file = temp_config_dir / "settings.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)
        
        with patch.object(Path, "home", return_value=temp_config_dir.parent):
            config = ConfigManager()
            calculator = ConfidenceCalculator(config_manager=config)
            
            # 验证阈值已更新
            thresholds = calculator.get_confidence_thresholds()
            assert thresholds["auto_copy_threshold"] == 0.95
            assert thresholds["confidence_threshold"] == 0.85


class TestDatabaseIntegration:
    """数据库集成测试"""

    def test_database_with_multiple_operations(self, temp_db_path, mock_config_manager, monkeypatch):
        """测试数据库多重操作"""
        from aicmd.database_manager import SafeDatabaseManager
        
        monkeypatch.setattr(
            SafeDatabaseManager,
            "_get_database_path",
            lambda self: str(temp_db_path)
        )
        
        db = SafeDatabaseManager(mock_config_manager)
        
        if not db.is_available:
            pytest.skip("Database not available")
        
        # 批量插入
        for i in range(10):
            db.execute_query(
                """
                INSERT INTO enhanced_cache 
                (query, query_hash, command, confidence_score)
                VALUES (?, ?, ?, ?)
                """,
                (f"query{i}", f"hash{i}", f"command{i}", 0.5 + i * 0.05)
            )
        
        # 查询验证
        result = db.execute_query(
            "SELECT COUNT(*) FROM enhanced_cache",
            fetch=True
        )
        assert result[0][0] == 10
        
        # 获取统计
        stats = db.get_database_stats()
        assert stats["cache_entries"] == 10


class TestErrorHandlingIntegration:
    """错误处理集成测试"""

    def test_graceful_degradation_on_db_failure(self, mock_config_manager):
        """测试数据库失败时的优雅降级"""
        from aicmd.cache_manager import CacheManager
        from aicmd.error_handler import GracefulDegradationManager
        
        degradation_manager = GracefulDegradationManager()
        cache_manager = CacheManager(
            config_manager=mock_config_manager,
            degradation_manager=degradation_manager
        )
        
        # 模拟数据库不可用
        cache_manager.db.is_available = False
        
        # 操作应该不会抛出异常
        result = cache_manager.save_cache_entry("test", "test")
        assert result is None
        
        result = cache_manager.find_exact_match("test")
        assert result is None
        
        stats = cache_manager.get_cache_stats()
        assert stats["status"] in ["unavailable", "error"]


@pytest.mark.integration
class TestFullWorkflow:
    """完整工作流程测试"""

    def test_query_to_command_workflow(self, mock_cache_manager):
        """测试从查询到命令的完整工作流程"""
        from aicmd.query_matcher import QueryMatcher
        from aicmd.confidence_calculator import ConfidenceCalculator
        from aicmd.safety_checker import CommandSafetyChecker
        
        if not mock_cache_manager.db.is_available:
            pytest.skip("Database not available")
        
        # 初始化组件
        matcher = QueryMatcher()
        calculator = ConfidenceCalculator(cache_manager=mock_cache_manager)
        checker = CommandSafetyChecker()
        
        # 1. 保存一个已知的查询-命令对
        known_query = "list files in current directory"
        known_command = "ls -la"
        
        mock_cache_manager.save_cache_entry(known_query, known_command)
        
        # 2. 模拟用户输入相似查询
        user_query = "show files in directory"
        
        # 3. 尝试精确匹配
        exact_match = mock_cache_manager.find_exact_match(user_query)
        
        if exact_match is None:
            # 4. 尝试相似匹配
            cached_queries = mock_cache_manager.get_all_cached_queries()
            similar = matcher.find_similar_queries(user_query, cached_queries, threshold=0.5)
            
            if similar:
                # 找到相似查询
                matched_query, matched_command, similarity = similar[0]
                
                # 5. 安全检查
                safety_info = checker.get_safety_info(matched_command)
                
                assert safety_info["is_dangerous"] is False
                assert matched_command == known_command
