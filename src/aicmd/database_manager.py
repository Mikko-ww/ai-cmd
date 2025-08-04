"""
数据库管理器模块
负责 SQLite 数据库的创建、初始化和安全管理
"""

import sqlite3
import os
import hashlib
import threading
from pathlib import Path
from datetime import datetime
from .config_manager import ConfigManager


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
        """获取数据库文件路径，支持跨平台"""
        try:
            # 从配置获取自定义路径
            custom_dir = self.config.get("cache_dir")
            if custom_dir:
                cache_dir = Path(custom_dir)
            else:
                # 使用默认路径：用户主目录/.ai-cmd
                cache_dir = Path.home() / ".ai-cmd"

            # 确保目录存在
            cache_dir.mkdir(parents=True, exist_ok=True)

            db_path = cache_dir / "cache.db"
            return str(db_path)

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
                print(f"Database initialized successfully: {self.db_path}")
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
        """生成查询的唯一哈希值"""
        # 标准化查询（去除多余空格，转换为小写）
        normalized_query = " ".join(query.lower().split())
        return hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()[:16]

    def cleanup_old_entries(self):
        """清理过期的缓存条目（基于配置的限制）"""
        if not self.is_available:
            return

        try:
            cache_limit = self.config.get("cache_size_limit", 1000)

            # 获取当前缓存条目数
            result = self.execute_query(
                "SELECT COUNT(*) FROM enhanced_cache", fetch=True
            )

            if result and isinstance(result, list) and len(result) > 0:
                count = result[0][0]
                if count > cache_limit:
                    # 删除最老的条目
                    delete_count = count - cache_limit + 100  # 多删除一些以避免频繁清理
                    self.execute_query(
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

                    print(f"Cleaned up {delete_count} old cache entries")

        except Exception as e:
            print(f"Warning: Cache cleanup failed: {e}")

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
