"""
数据库管理器模块
负责 SQLite 数据库的创建、初始化和安全管理
"""

import sqlite3
import os
import threading
from pathlib import Path
from datetime import datetime
from .config_manager import ConfigManager
from .hash_utils import hash_query


class SafeDatabaseManager:
    """安全的数据库管理器，支持跨平台初始化和异常降级"""

    def __init__(self, config_manager=None):
        """初始化数据库管理器"""
        self.config = config_manager or ConfigManager()
        self.db_path = None
        self.connection = None
        self.lock = threading.Lock()
        self.is_available = False

        # 尝试初始化数据库
        self._initialize_database()

    def _get_database_path(self):
        """根据配置获取数据库文件路径，尊重 cache_directory 与 database_file 配置。"""
        try:
            cache_directory = self.config.get("cache_directory") or self.config.get(
                "cache_dir"
            )
            database_file = self.config.get("database_file") or "cache.db"

            base_dir = Path(cache_directory or (Path.home() / ".ai-cmd")).expanduser()
            base_dir.mkdir(parents=True, exist_ok=True)

            new_db_path = base_dir / database_file
            return str(new_db_path)

        except Exception as e:
            print(f"Warning: Failed to determine database path: {e}")
            # 降级到临时目录
            try:
                import tempfile

                temp_dir = Path(tempfile.gettempdir()) / "ai-cmd"
                temp_dir.mkdir(parents=True, exist_ok=True)
                return str(temp_dir / "cache.db")
            except Exception as e2:
                print(f"Warning: Failed to create temp database path: {e2}")
                return None

    def _initialize_database(self):
        """安全初始化数据库"""
        try:
            # 检查是否启用缓存
            if not self.config.get("cache_enabled", True):
                print("Cache is disabled by configuration")
                return

            # 获取数据库路径
            self.db_path = self._get_database_path()
            if not self.db_path:
                print("Warning: Cannot initialize database, running without cache")
                return

            # 测试数据库连接
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                conn.execute("SELECT 1").fetchone()

            # 创建表结构
            self._create_tables()

            # 验证表结构
            if self._verify_tables():
                self.is_available = True
                # 降低噪音，避免常规路径打印
                # print(f"Database initialized successfully: {self.db_path}")
            else:
                print("Warning: Database table verification failed")

        except Exception as e:
            print(f"Warning: Database initialization failed: {e}")
            print("Running without cache functionality")

    def _create_tables(self):
        """创建数据库表结构"""
        if not self.db_path:
            raise Exception("Database path not available")

        enhanced_cache_sql = """
        CREATE TABLE IF NOT EXISTS enhanced_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            query_hash TEXT NOT NULL UNIQUE,
            command TEXT NOT NULL,
            confidence_score REAL DEFAULT 0.0,
            confirmation_count INTEGER DEFAULT 0,
            rejection_count INTEGER DEFAULT 0,
            last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            os_type TEXT,
            shell_type TEXT
        );
        """

        feedback_history_sql = """
        CREATE TABLE IF NOT EXISTS feedback_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_hash TEXT NOT NULL,
            command TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (query_hash) REFERENCES enhanced_cache (query_hash)
        );
        """

        # 创建索引以提高查询性能
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_query_hash ON enhanced_cache (query_hash);",
            "CREATE INDEX IF NOT EXISTS idx_last_used ON enhanced_cache (last_used);",
            "CREATE INDEX IF NOT EXISTS idx_confidence_score ON enhanced_cache (confidence_score);",
            "CREATE INDEX IF NOT EXISTS idx_feedback_query_hash ON feedback_history (query_hash);",
            "CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback_history (timestamp);",
        ]

        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                # 创建表
                conn.execute(enhanced_cache_sql)
                conn.execute(feedback_history_sql)

                # 创建索引
                for index_sql in indexes_sql:
                    conn.execute(index_sql)

                conn.commit()

        except Exception as e:
            print(f"Warning: Failed to create database tables: {e}")
            raise

    def _verify_tables(self):
        """验证数据库表结构是否正确"""
        if not self.db_path:
            return False

        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                cursor = conn.cursor()

                # 检查 enhanced_cache 表
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='enhanced_cache'
                """
                )
                if not cursor.fetchone():
                    return False

                # 检查 feedback_history 表
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='feedback_history'
                """
                )
                if not cursor.fetchone():
                    return False

                # 验证关键列存在
                cursor.execute("PRAGMA table_info(enhanced_cache)")
                cache_columns = {row[1] for row in cursor.fetchall()}
                required_cache_columns = {
                    "id",
                    "query",
                    "query_hash",
                    "command",
                    "confidence_score",
                    "confirmation_count",
                    "rejection_count",
                    "last_used",
                    "created_at",
                }

                if not required_cache_columns.issubset(cache_columns):
                    print(f"Warning: Missing required columns in enhanced_cache table")
                    return False

                return True

        except Exception as e:
            print(f"Warning: Database verification failed: {e}")
            return False

    def get_connection(self):
        """获取数据库连接（线程安全）"""
        if not self.is_available or not self.db_path:
            return None

        try:
            return sqlite3.connect(self.db_path, timeout=5.0)
        except Exception as e:
            print(f"Warning: Failed to get database connection: {e}")
            return None

    def execute_query(self, query, params=None, fetch=False):
        """安全执行数据库查询"""
        if not self.is_available or not self.db_path:
            return None

        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                    cursor = conn.cursor()

                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)

                    if fetch:
                        return cursor.fetchall()
                    else:
                        conn.commit()
                        return cursor.rowcount

            except Exception as e:
                print(f"Warning: Database query failed: {e}")
                return None

    def generate_query_hash(self, query):
        """统一调用哈希工具，确保一致性，支持配置的哈希策略"""
        hash_strategy = self.config.get("hash_strategy", "simple")
        return hash_query(query, strategy=hash_strategy)

    def cleanup_old_entries(self):
        """清理过期的缓存条目（基于配置的限制和TTL）"""
        if not self.is_available:
            return 0

        total_deleted = 0

        try:
            # 1. 先清理基于时间的TTL过期条目
            max_age_days = self.config.get("max_cache_age_days", 30)
            if max_age_days > 0:
                ttl_result = self.execute_query(
                    """
                    DELETE FROM enhanced_cache 
                    WHERE created_at < datetime('now', '-' || ? || ' days')
                    """,
                    (max_age_days,),
                )

                if ttl_result and isinstance(ttl_result, int):
                    total_deleted += ttl_result
                    if ttl_result > 0:
                        print(
                            f"Cleaned up {ttl_result} expired cache entries (older than {max_age_days} days)"
                        )

            # 2. 然后清理基于大小限制的条目
            cache_limit = self.config.get("cache_size_limit", 1000)
            if cache_limit > 0:
                # 获取当前缓存条目数
                result = self.execute_query(
                    "SELECT COUNT(*) FROM enhanced_cache", fetch=True
                )

                if result and isinstance(result, list) and len(result) > 0:
                    count = result[0][0]
                    if count > cache_limit:
                        # 删除最老的条目
                        delete_count = (
                            count - cache_limit + 100
                        )  # 多删除一些以避免频繁清理
                        size_result = self.execute_query(
                            """
                            DELETE FROM enhanced_cache 
                            WHERE id IN (
                                SELECT id FROM enhanced_cache 
                                ORDER BY last_used ASC 
                                LIMIT ?
                            )
                        """,
                            (delete_count,),
                        )

                        if size_result and isinstance(size_result, int):
                            total_deleted += size_result
                            if size_result > 0:
                                print(
                                    f"Cleaned up {size_result} old cache entries (size limit: {cache_limit})"
                                )

        except Exception as e:
            print(f"Warning: Cache cleanup failed: {e}")

        return total_deleted

    def get_database_stats(self):
        """获取数据库统计信息"""
        if not self.is_available:
            return {"status": "unavailable"}

        try:
            status = {}

            # 缓存条目统计
            result = self.execute_query(
                "SELECT COUNT(*) FROM enhanced_cache", fetch=True
            )
            status["cache_entries"] = (
                result[0][0]
                if result and isinstance(result, list) and len(result) > 0
                else 0
            )

            # 反馈历史统计
            result = self.execute_query(
                "SELECT COUNT(*) FROM feedback_history", fetch=True
            )
            status["feedback_entries"] = (
                result[0][0]
                if result and isinstance(result, list) and len(result) > 0
                else 0
            )

            # 数据库文件大小
            if self.db_path and os.path.exists(self.db_path):
                status["db_size_mb"] = round(
                    os.path.getsize(self.db_path) / (1024 * 1024), 2
                )

            status["status"] = "available"
            status["db_path"] = self.db_path

            return status

        except Exception as e:
            print(f"Warning: Failed to get database status: {e}")
            return {"status": "error", "error": str(e)}

    def backup_database(self, backup_path=None):
        """备份数据库文件"""
        if not self.is_available or not self.db_path:
            return False

        try:
            if not backup_path:
                backup_path = (
                    f"{self.db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )

            import shutil

            shutil.copy2(self.db_path, backup_path)
            print(f"Database backed up to: {backup_path}")
            return True

        except Exception as e:
            print(f"Warning: Database backup failed: {e}")
            return False

    def __enter__(self):
        """上下文管理器支持"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """清理资源"""
        if self.connection:
            self.connection.close()
