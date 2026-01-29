"""
SafeDatabaseManager 单元测试
测试数据库连接和操作
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestSafeDatabaseManager:
    """SafeDatabaseManager 测试类"""

    def test_database_initialization(self, temp_db_path, mock_config_manager, monkeypatch):
        """测试数据库初始化"""
        from aicmd.database_manager import SafeDatabaseManager
        
        # Mock 数据库路径
        monkeypatch.setattr(
            SafeDatabaseManager,
            "_get_database_path",
            lambda self: str(temp_db_path)
        )
        
        db = SafeDatabaseManager(mock_config_manager)
        
        assert db.is_available is True
        assert db.db_path == str(temp_db_path)

    def test_table_creation(self, temp_db_path, mock_config_manager, monkeypatch):
        """测试表创建"""
        from aicmd.database_manager import SafeDatabaseManager
        
        monkeypatch.setattr(
            SafeDatabaseManager,
            "_get_database_path",
            lambda self: str(temp_db_path)
        )
        
        db = SafeDatabaseManager(mock_config_manager)
        
        if db.is_available:
            # 验证表存在
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查 enhanced_cache 表
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='enhanced_cache'"
                )
                assert cursor.fetchone() is not None
                
                # 检查 feedback_history 表
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='feedback_history'"
                )
                assert cursor.fetchone() is not None

    def test_verify_tables(self, temp_db_path, mock_config_manager, monkeypatch):
        """测试表验证"""
        from aicmd.database_manager import SafeDatabaseManager
        
        monkeypatch.setattr(
            SafeDatabaseManager,
            "_get_database_path",
            lambda self: str(temp_db_path)
        )
        
        db = SafeDatabaseManager(mock_config_manager)
        
        if db.is_available:
            result = db._verify_tables()
            assert result is True

    def test_execute_query_insert(self, temp_db_path, mock_config_manager, monkeypatch):
        """测试插入查询"""
        from aicmd.database_manager import SafeDatabaseManager
        
        monkeypatch.setattr(
            SafeDatabaseManager,
            "_get_database_path",
            lambda self: str(temp_db_path)
        )
        
        db = SafeDatabaseManager(mock_config_manager)
        
        if db.is_available:
            insert_sql = """
                INSERT INTO enhanced_cache 
                (query, query_hash, command, confidence_score)
                VALUES (?, ?, ?, ?)
            """
            
            result = db.execute_query(
                insert_sql,
                ("test query", "test_hash", "test command", 0.5)
            )
            
            assert result == 1

    def test_execute_query_select(self, temp_db_path, mock_config_manager, monkeypatch):
        """测试查询操作"""
        from aicmd.database_manager import SafeDatabaseManager
        
        monkeypatch.setattr(
            SafeDatabaseManager,
            "_get_database_path",
            lambda self: str(temp_db_path)
        )
        
        db = SafeDatabaseManager(mock_config_manager)
        
        if db.is_available:
            # 先插入数据
            insert_sql = """
                INSERT INTO enhanced_cache 
                (query, query_hash, command, confidence_score)
                VALUES (?, ?, ?, ?)
            """
            db.execute_query(insert_sql, ("select test", "select_hash", "cmd", 0.5))
            
            # 查询数据
            select_sql = "SELECT query FROM enhanced_cache WHERE query_hash = ?"
            result = db.execute_query(select_sql, ("select_hash",), fetch=True)
            
            assert result is not None
            assert len(result) > 0
            assert result[0][0] == "select test"

    def test_generate_query_hash(self, temp_db_path, mock_config_manager, monkeypatch):
        """测试查询哈希生成"""
        from aicmd.database_manager import SafeDatabaseManager
        
        monkeypatch.setattr(
            SafeDatabaseManager,
            "_get_database_path",
            lambda self: str(temp_db_path)
        )
        
        db = SafeDatabaseManager(mock_config_manager)
        
        hash1 = db.generate_query_hash("test query")
        hash2 = db.generate_query_hash("test query")
        hash3 = db.generate_query_hash("different query")
        
        # 相同查询应该产生相同哈希
        assert hash1 == hash2
        # 不同查询应该产生不同哈希
        assert hash1 != hash3

    def test_get_database_stats(self, temp_db_path, mock_config_manager, monkeypatch):
        """测试获取数据库统计"""
        from aicmd.database_manager import SafeDatabaseManager
        
        monkeypatch.setattr(
            SafeDatabaseManager,
            "_get_database_path",
            lambda self: str(temp_db_path)
        )
        
        db = SafeDatabaseManager(mock_config_manager)
        
        stats = db.get_database_stats()
        
        assert "status" in stats
        if stats["status"] == "available":
            assert "cache_entries" in stats
            assert "feedback_entries" in stats
            assert "db_path" in stats

    def test_cleanup_old_entries(self, temp_db_path, mock_config_manager, monkeypatch):
        """测试清理旧条目"""
        from aicmd.database_manager import SafeDatabaseManager
        
        monkeypatch.setattr(
            SafeDatabaseManager,
            "_get_database_path",
            lambda self: str(temp_db_path)
        )
        
        db = SafeDatabaseManager(mock_config_manager)
        
        if db.is_available:
            result = db.cleanup_old_entries()
            # 结果应该 >= 0
            assert result >= 0


class TestDatabaseIndexes:
    """数据库索引测试"""

    def test_indexes_exist(self, temp_db_path, mock_config_manager, monkeypatch):
        """测试索引是否已创建"""
        from aicmd.database_manager import SafeDatabaseManager
        
        monkeypatch.setattr(
            SafeDatabaseManager,
            "_get_database_path",
            lambda self: str(temp_db_path)
        )
        
        db = SafeDatabaseManager(mock_config_manager)
        
        if db.is_available:
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取所有索引
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
                indexes = [row[0] for row in cursor.fetchall()]
                
                # 验证关键索引存在
                assert "idx_query_hash" in indexes
                assert "idx_last_used" in indexes
                assert "idx_confidence_score" in indexes


class TestDatabaseGracefulDegradation:
    """数据库优雅降级测试"""

    def test_unavailable_database_operations(self, mock_config_manager):
        """测试数据库不可用时的操作"""
        from aicmd.database_manager import SafeDatabaseManager
        
        db = SafeDatabaseManager(mock_config_manager)
        db.is_available = False
        db.db_path = None
        
        # 所有操作应该返回 None 或空结果
        result = db.execute_query("SELECT 1")
        assert result is None
        
        conn = db.get_connection()
        assert conn is None
        
        stats = db.get_database_stats()
        assert stats["status"] == "unavailable"

    def test_connection_failure_handling(self, mock_config_manager, monkeypatch):
        """测试连接失败处理"""
        from aicmd.database_manager import SafeDatabaseManager
        
        # 模拟连接失败
        def mock_connect(*args, **kwargs):
            raise sqlite3.Error("Connection failed")
        
        monkeypatch.setattr(sqlite3, "connect", mock_connect)
        
        db = SafeDatabaseManager(mock_config_manager)
        
        # 应该不会抛出异常
        assert db.is_available is False


class TestDatabaseBackup:
    """数据库备份测试"""

    def test_backup_database(self, temp_db_path, mock_config_manager, monkeypatch):
        """测试数据库备份"""
        from aicmd.database_manager import SafeDatabaseManager
        
        monkeypatch.setattr(
            SafeDatabaseManager,
            "_get_database_path",
            lambda self: str(temp_db_path)
        )
        
        db = SafeDatabaseManager(mock_config_manager)
        
        if db.is_available:
            backup_path = str(temp_db_path) + ".backup"
            result = db.backup_database(backup_path)
            
            assert result is True
            assert Path(backup_path).exists()
