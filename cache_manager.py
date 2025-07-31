"""
缓存管理器模块
提供缓存的基础增删改查操作，确保数据操作的原子性和一致性
"""

import platform
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from database_manager import SafeDatabaseManager
from config_manager import ConfigManager


class CacheEntry:
    """缓存条目数据模型"""
    
    def __init__(self, cache_id: Optional[int] = None, query: Optional[str] = None, 
                 query_hash: Optional[str] = None, command: Optional[str] = None,
                 confidence_score: float = 0.0, confirmation_count: int = 0, 
                 rejection_count: int = 0, last_used: Optional[str] = None, 
                 created_at: Optional[str] = None, os_type: Optional[str] = None, 
                 shell_type: Optional[str] = None):
        self.id = cache_id
        self.query = query
        self.query_hash = query_hash
        self.command = command
        self.confidence_score = confidence_score
        self.confirmation_count = confirmation_count
        self.rejection_count = rejection_count
        self.last_used = last_used
        self.created_at = created_at
        self.os_type = os_type
        self.shell_type = shell_type
    
    @classmethod
    def from_db_row(cls, row: List[Any]) -> Optional['CacheEntry']:
        """从数据库行创建 CacheEntry 对象"""
        if not row:
            return None
        return cls(
            cache_id=row[0],
            query=row[1],
            query_hash=row[2],
            command=row[3],
            confidence_score=row[4],
            confirmation_count=row[5],
            rejection_count=row[6],
            last_used=row[7],
            created_at=row[8],
            os_type=row[9] if len(row) > 9 else None,
            shell_type=row[10] if len(row) > 10 else None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'query': self.query,
            'query_hash': self.query_hash,
            'command': self.command,
            'confidence_score': self.confidence_score,
            'confirmation_count': self.confirmation_count,
            'rejection_count': self.rejection_count,
            'last_used': self.last_used,
            'created_at': self.created_at,
            'os_type': self.os_type,
            'shell_type': self.shell_type
        }


class CacheManager:
    """缓存管理器，提供完整的 CRUD 操作"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化缓存管理器"""
        self.config = config_manager or ConfigManager()
        self.db = SafeDatabaseManager(self.config)
        self.current_os = platform.system()
        self.current_shell = os.environ.get('SHELL', '').split('/')[-1] or 'unknown'
    
    def save_cache_entry(self, query: str, command: str, os_type: Optional[str] = None, 
                        shell_type: Optional[str] = None) -> Optional[str]:
        """保存新的缓存条目"""
        if not self.db.is_available:
            return None
            
        try:
            query_hash = self.db.generate_query_hash(query)
            os_type = os_type or self.current_os
            shell_type = shell_type or self.current_shell
            
            # 检查是否已存在相同的缓存条目
            existing_entry = self.find_exact_match(query)
            if existing_entry and existing_entry.query_hash:
                if existing_entry.command == command:
                    self.update_last_used(existing_entry.query_hash)
                    return existing_entry.query_hash
                else:
                    self.delete_cache_entry(existing_entry.query_hash)
            
            insert_sql = """
                INSERT INTO enhanced_cache 
                (query, query_hash, command, os_type, shell_type, created_at, last_used)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            
            result = self.db.execute_query(insert_sql, (query, query_hash, command, os_type, shell_type))
            
            if result and isinstance(result, int) and result > 0:
                print(f"Cache entry saved: {query_hash[:8]}...")
                return query_hash
            else:
                print(f"Warning: Failed to save cache entry")
                return None
                
        except Exception as e:
            print(f"Warning: Error saving cache entry: {e}")
            return None
    
    def find_exact_match(self, query: str) -> Optional[CacheEntry]:
        """查找精确匹配的缓存条目"""
        if not self.db.is_available:
            return None
            
        try:
            query_hash = self.db.generate_query_hash(query)
            
            select_sql = """
                SELECT id, query, query_hash, command, confidence_score,
                       confirmation_count, rejection_count, last_used, created_at,
                       os_type, shell_type
                FROM enhanced_cache 
                WHERE query_hash = ?
            """
            
            result = self.db.execute_query(select_sql, (query_hash,), fetch=True)
            
            if result and isinstance(result, list) and len(result) > 0:
                return CacheEntry.from_db_row(result[0])
            else:
                return None
                
        except Exception as e:
            print(f"Warning: Error finding exact match: {e}")
            return None
    
    def update_last_used(self, query_hash: str) -> bool:
        """更新最后使用时间"""
        if not self.db.is_available:
            return False
            
        try:
            update_sql = "UPDATE enhanced_cache SET last_used = CURRENT_TIMESTAMP WHERE query_hash = ?"
            result = self.db.execute_query(update_sql, (query_hash,))
            if result and isinstance(result, int):
                return result > 0
            return False
        except Exception as e:
            print(f"Warning: Error updating last used: {e}")
            return False
    
    def delete_cache_entry(self, query_hash: str) -> bool:
        """删除缓存条目"""
        if not self.db.is_available:
            return False
            
        try:
            result = self.db.execute_query("DELETE FROM enhanced_cache WHERE query_hash = ?", (query_hash,))
            if result and isinstance(result, int) and result > 0:
                print(f"Cache entry deleted: {query_hash[:8]}...")
                return True
            return False
        except Exception as e:
            print(f"Warning: Error deleting cache entry: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not self.db.is_available:
            return {"status": "unavailable"}
            
        try:
            stats = {}
            
            # 总缓存条目数
            result = self.db.execute_query("SELECT COUNT(*) FROM enhanced_cache", fetch=True)
            if result and isinstance(result, list) and len(result) > 0:
                stats['total_entries'] = result[0][0]
            else:
                stats['total_entries'] = 0
            
            stats['status'] = 'available'
            return stats
            
        except Exception as e:
            print(f"Warning: Error getting cache stats: {e}")
            return {"status": "error", "error": str(e)}
