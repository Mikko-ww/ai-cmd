"""
CacheManager 单元测试
测试缓存 CRUD 操作
"""

import pytest
from unittest.mock import MagicMock, patch


class TestCacheEntry:
    """CacheEntry 数据模型测试"""

    def test_create_cache_entry(self):
        """测试创建 CacheEntry"""
        from aicmd.cache_manager import CacheEntry
        
        entry = CacheEntry(
            cache_id=1,
            query="list all files",
            query_hash="abc123",
            command="ls -la",
            confidence_score=0.85,
            confirmation_count=3,
            rejection_count=0,
        )
        
        assert entry.id == 1
        assert entry.query == "list all files"
        assert entry.query_hash == "abc123"
        assert entry.command == "ls -la"
        assert entry.confidence_score == 0.85
        assert entry.confirmation_count == 3
        assert entry.rejection_count == 0

    def test_cache_entry_from_db_row(self):
        """测试从数据库行创建 CacheEntry"""
        from aicmd.cache_manager import CacheEntry
        
        row = [
            1, "list files", "hash123", "ls", 0.9, 5, 1,
            "2024-01-01 12:00:00", "2024-01-01 10:00:00", "Linux", "bash"
        ]
        
        entry = CacheEntry.from_db_row(row)
        
        assert entry.id == 1
        assert entry.query == "list files"
        assert entry.query_hash == "hash123"
        assert entry.command == "ls"
        assert entry.confidence_score == 0.9
        assert entry.confirmation_count == 5
        assert entry.rejection_count == 1
        assert entry.os_type == "Linux"
        assert entry.shell_type == "bash"

    def test_cache_entry_from_empty_row(self):
        """测试从空行创建 CacheEntry"""
        from aicmd.cache_manager import CacheEntry
        
        entry = CacheEntry.from_db_row(None)
        assert entry is None
        
        entry = CacheEntry.from_db_row([])
        assert entry is None

    def test_cache_entry_to_dict(self):
        """测试 CacheEntry 转换为字典"""
        from aicmd.cache_manager import CacheEntry
        
        entry = CacheEntry(
            cache_id=1,
            query="test query",
            query_hash="test_hash",
            command="test_cmd",
            confidence_score=0.8,
        )
        
        d = entry.to_dict()
        
        assert d["id"] == 1
        assert d["query"] == "test query"
        assert d["query_hash"] == "test_hash"
        assert d["command"] == "test_cmd"
        assert d["confidence_score"] == 0.8


class TestCacheManager:
    """CacheManager 测试类"""

    def test_cache_manager_init(self, mock_config_manager):
        """测试 CacheManager 初始化"""
        from aicmd.cache_manager import CacheManager
        from aicmd.error_handler import GracefulDegradationManager
        
        degradation_manager = GracefulDegradationManager()
        cache_manager = CacheManager(
            config_manager=mock_config_manager,
            degradation_manager=degradation_manager
        )
        
        assert cache_manager.config is not None
        assert cache_manager.degradation_manager is not None

    def test_compare_commands(self, mock_config_manager):
        """测试命令比较"""
        from aicmd.cache_manager import CacheManager
        
        cache_manager = CacheManager(config_manager=mock_config_manager)
        
        # 相同命令
        assert cache_manager.compare_commands("ls -la", "ls -la") is True
        
        # 带空格的相同命令
        assert cache_manager.compare_commands("ls  -la", "ls -la") is True
        
        # 带占位符的命令
        assert cache_manager.compare_commands("git commit -m <message>", "git commit -m") is True
        
        # 不同命令
        assert cache_manager.compare_commands("ls -la", "pwd") is False
        
        # None 处理
        assert cache_manager.compare_commands(None, None) is True
        assert cache_manager.compare_commands("ls", None) is False

    def test_save_and_find_exact_match(self, mock_cache_manager, monkeypatch):
        """测试保存和查找精确匹配"""
        # 保存缓存条目
        query = "show all files"
        command = "ls -la"
        
        query_hash = mock_cache_manager.save_cache_entry(query, command)
        
        if mock_cache_manager.db.is_available:
            assert query_hash is not None
            
            # 查找精确匹配
            entry = mock_cache_manager.find_exact_match(query)
            
            assert entry is not None
            assert entry.query == query
            assert entry.command == command

    def test_update_last_used(self, mock_cache_manager):
        """测试更新最后使用时间"""
        # 先保存一个条目
        query = "test query"
        command = "test command"
        
        query_hash = mock_cache_manager.save_cache_entry(query, command)
        
        if mock_cache_manager.db.is_available and query_hash:
            # 更新最后使用时间
            result = mock_cache_manager.update_last_used(query_hash)
            assert result is True

    def test_delete_cache_entry(self, mock_cache_manager):
        """测试删除缓存条目"""
        # 先保存一个条目
        query = "delete test query"
        command = "delete test command"
        
        query_hash = mock_cache_manager.save_cache_entry(query, command)
        
        if mock_cache_manager.db.is_available and query_hash:
            # 删除条目
            result = mock_cache_manager.delete_cache_entry(query_hash)
            assert result is True
            
            # 验证已删除
            entry = mock_cache_manager.find_exact_match(query)
            assert entry is None

    def test_get_cache_stats(self, mock_cache_manager):
        """测试获取缓存统计"""
        stats = mock_cache_manager.get_cache_stats()
        
        assert "status" in stats
        if stats["status"] == "available":
            assert "total_entries" in stats

    def test_get_all_cached_queries(self, mock_cache_manager):
        """测试获取所有缓存查询"""
        # 保存一些缓存条目
        mock_cache_manager.save_cache_entry("query1", "command1")
        mock_cache_manager.save_cache_entry("query2", "command2")
        
        queries = mock_cache_manager.get_all_cached_queries()
        
        if mock_cache_manager.db.is_available:
            assert isinstance(queries, list)


class TestCacheManagerErrorHandling:
    """CacheManager 错误处理测试"""

    def test_cache_unavailable_graceful_degradation(self, mock_config_manager):
        """测试数据库不可用时的优雅降级"""
        from aicmd.cache_manager import CacheManager
        from aicmd.error_handler import GracefulDegradationManager
        
        degradation_manager = GracefulDegradationManager()
        cache_manager = CacheManager(
            config_manager=mock_config_manager,
            degradation_manager=degradation_manager
        )
        
        # 模拟数据库不可用
        cache_manager.db.is_available = False
        
        # 操作应该优雅降级，返回默认值
        result = cache_manager.find_exact_match("test query")
        assert result is None
        
        result = cache_manager.save_cache_entry("test", "test")
        assert result is None

    def test_get_error_status(self, mock_cache_manager):
        """测试获取错误状态"""
        status = mock_cache_manager.get_error_status()
        
        assert "cache_available" in status
        assert "error_count" in status

    def test_reset_error_state(self, mock_cache_manager):
        """测试重置错误状态"""
        mock_cache_manager.reset_error_state()
        
        status = mock_cache_manager.get_error_status()
        assert status["error_count"] == 0
