"""
数据库管理器模块
负责 SQLite 数据库的创建、初始化和安全管理
支持连接池、批量操作和性能优化
"""

import sqlite3
import os
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple, Any, Dict
from queue import Queue, Empty
from contextlib import contextmanager
from .config_manager import ConfigManager
from .hash_utils import hash_query


# =============================================================================
# 连接池实现
# =============================================================================

class DatabaseConnectionPool:
    """SQLite 连接池管理器"""
    
    def __init__(
        self,
        db_path: str,
        pool_size: int = 5,
        timeout: float = 10.0
    ):
        """
        初始化连接池
        
        Args:
            db_path: 数据库文件路径
            pool_size: 连接池大小
            timeout: 获取连接的超时时间（秒）
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool: Queue = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._initialized = False
        
        # 延迟初始化
        self._initialize_pool()
    
    def _initialize_pool(self):
        """初始化连接池"""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            try:
                for _ in range(self.pool_size):
                    conn = self._create_connection()
                    if conn:
                        self._pool.put(conn)
                self._initialized = True
            except Exception as e:
                print(f"Warning: Failed to initialize connection pool: {e}")
    
    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """创建新的数据库连接"""
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=False  # 允许跨线程使用
            )
            # 启用 WAL 模式以提高并发性能
            conn.execute("PRAGMA journal_mode=WAL")
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys=ON")
            # 优化同步模式
            conn.execute("PRAGMA synchronous=NORMAL")
            # 增加缓存大小
            conn.execute("PRAGMA cache_size=-10000")  # 约 10MB
            return conn
        except Exception as e:
            print(f"Warning: Failed to create database connection: {e}")
            return None
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = None
        try:
            conn = self._pool.get(timeout=self.timeout)
            yield conn
        except Empty:
            # 池中没有可用连接，创建临时连接
            conn = self._create_connection()
            yield conn
            if conn:
                conn.close()
            conn = None
        finally:
            if conn is not None:
                try:
                    self._pool.put_nowait(conn)
                except Exception:
                    conn.close()
    
    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Exception:
                pass
        self._initialized = False


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

    # =========================================================================
    # 批量操作方法
    # =========================================================================

    def execute_batch(
        self,
        query: str,
        params_list: List[Tuple],
        batch_size: int = 100
    ) -> int:
        """
        批量执行数据库插入/更新操作
        
        Args:
            query: SQL 查询语句（带占位符）
            params_list: 参数列表
            batch_size: 每批处理的记录数
            
        Returns:
            成功处理的记录数
        """
        if not self.is_available or not self.db_path:
            return 0
        
        total_affected = 0
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    cursor = conn.cursor()
                    
                    # 启用事务优化
                    conn.execute("PRAGMA synchronous=OFF")
                    conn.execute("BEGIN TRANSACTION")
                    
                    try:
                        for i in range(0, len(params_list), batch_size):
                            batch = params_list[i:i + batch_size]
                            cursor.executemany(query, batch)
                            total_affected += cursor.rowcount
                        
                        conn.commit()
                    except Exception as e:
                        conn.rollback()
                        raise e
                    finally:
                        # 恢复正常同步模式
                        conn.execute("PRAGMA synchronous=NORMAL")
                        
            except Exception as e:
                print(f"Warning: Batch execution failed: {e}")
                return 0
        
        return total_affected

    def bulk_insert_cache_entries(
        self,
        entries: List[Dict[str, Any]]
    ) -> int:
        """
        批量插入缓存条目
        
        Args:
            entries: 缓存条目字典列表，每个包含 query, command, confidence_score 等
            
        Returns:
            成功插入的记录数
        """
        if not entries:
            return 0
        
        query = """
        INSERT OR REPLACE INTO enhanced_cache 
        (query, query_hash, command, confidence_score, os_type, shell_type)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        params_list = []
        for entry in entries:
            query_text = entry.get("query", "")
            params_list.append((
                query_text,
                self.generate_query_hash(query_text),
                entry.get("command", ""),
                entry.get("confidence_score", 0.5),
                entry.get("os_type"),
                entry.get("shell_type")
            ))
        
        return self.execute_batch(query, params_list)

    def bulk_delete_by_ids(self, ids: List[int]) -> int:
        """
        批量删除指定 ID 的缓存条目
        
        Args:
            ids: 要删除的记录 ID 列表
            
        Returns:
            成功删除的记录数
        """
        if not ids or not self.is_available:
            return 0
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                    placeholders = ",".join("?" * len(ids))
                    cursor = conn.cursor()
                    cursor.execute(
                        f"DELETE FROM enhanced_cache WHERE id IN ({placeholders})",
                        ids
                    )
                    conn.commit()
                    return cursor.rowcount
            except Exception as e:
                print(f"Warning: Bulk delete failed: {e}")
                return 0

    # =========================================================================
    # 数据库维护方法
    # =========================================================================

    def vacuum_database(self) -> bool:
        """
        执行 VACUUM 命令压缩数据库文件
        
        Returns:
            是否成功
        """
        if not self.is_available or not self.db_path:
            return False
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=60.0) as conn:
                    conn.execute("VACUUM")
                print("Database vacuum completed successfully")
                return True
            except Exception as e:
                print(f"Warning: Database vacuum failed: {e}")
                return False

    def analyze_database(self) -> bool:
        """
        执行 ANALYZE 命令更新索引统计信息
        
        Returns:
            是否成功
        """
        if not self.is_available or not self.db_path:
            return False
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    conn.execute("ANALYZE")
                return True
            except Exception as e:
                print(f"Warning: Database analyze failed: {e}")
                return False

    def check_integrity(self) -> Dict[str, Any]:
        """
        检查数据库完整性
        
        Returns:
            完整性检查结果
        """
        result = {
            "status": "unknown",
            "integrity_check": None,
            "foreign_key_check": None,
            "errors": []
        }
        
        if not self.is_available or not self.db_path:
            result["status"] = "unavailable"
            return result
        
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()
                
                # 完整性检查
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()
                result["integrity_check"] = integrity_result[0] if integrity_result else "unknown"
                
                # 外键检查
                cursor.execute("PRAGMA foreign_key_check")
                fk_errors = cursor.fetchall()
                result["foreign_key_check"] = "ok" if not fk_errors else f"{len(fk_errors)} errors"
                if fk_errors:
                    result["errors"].extend([str(e) for e in fk_errors[:5]])  # 最多显示5个错误
                
                # 判断总体状态
                if result["integrity_check"] == "ok" and result["foreign_key_check"] == "ok":
                    result["status"] = "healthy"
                else:
                    result["status"] = "issues_found"
                    
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
        
        return result

    def get_health_report(self) -> Dict[str, Any]:
        """
        获取数据库健康报告
        
        Returns:
            包含各项健康指标的字典
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "status": "unknown",
            "statistics": {},
            "integrity": {},
            "performance": {},
            "recommendations": []
        }
        
        if not self.is_available:
            report["status"] = "unavailable"
            return report
        
        try:
            # 基本统计
            report["statistics"] = self.get_database_stats()
            
            # 完整性检查
            report["integrity"] = self.check_integrity()
            
            # 性能指标
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                cursor = conn.cursor()
                
                # 检查索引使用情况
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
                index_count = cursor.fetchone()[0]
                report["performance"]["index_count"] = index_count
                
                # 检查页面大小
                cursor.execute("PRAGMA page_size")
                report["performance"]["page_size"] = cursor.fetchone()[0]
                
                # 检查缓存大小
                cursor.execute("PRAGMA cache_size")
                report["performance"]["cache_size"] = cursor.fetchone()[0]
                
                # 检查日志模式
                cursor.execute("PRAGMA journal_mode")
                report["performance"]["journal_mode"] = cursor.fetchone()[0]
            
            # 生成建议
            stats = report["statistics"]
            if stats.get("db_size_mb", 0) > 100:
                report["recommendations"].append("Database size > 100MB, consider running VACUUM")
            
            if stats.get("cache_entries", 0) > 10000:
                report["recommendations"].append("Cache entries > 10000, consider cleanup")
            
            if report["integrity"]["status"] != "healthy":
                report["recommendations"].append("Database integrity issues detected, backup and repair recommended")
            
            # 总体状态
            if report["integrity"]["status"] == "healthy" and not report["recommendations"]:
                report["status"] = "healthy"
            elif report["integrity"]["status"] == "healthy":
                report["status"] = "good_with_recommendations"
            else:
                report["status"] = "needs_attention"
                
        except Exception as e:
            report["status"] = "error"
            report["error"] = str(e)
        
        return report

    def optimize(self) -> bool:
        """
        执行数据库优化操作
        
        Returns:
            是否成功
        """
        success = True
        
        # 清理旧条目
        self.cleanup_old_entries()
        
        # 分析索引
        if not self.analyze_database():
            success = False
        
        # 压缩数据库
        if not self.vacuum_database():
            success = False
        
        return success

    def __enter__(self):
        """上下文管理器支持"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """清理资源"""
        if self.connection:
            self.connection.close()
