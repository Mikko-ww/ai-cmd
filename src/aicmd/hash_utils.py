"""
哈希工具模块
提供统一的查询哈希算法，确保各模块使用一致的哈希以避免记录错配
"""

import hashlib


def hash_query(query: str) -> str:
    """
    统一的查询哈希函数

    规则：
    - 全部小写
    - 折叠多余空白为单空格
    - sha256 后取前 16 位
    说明：选择与数据库现有实现一致的标准化方式，避免破坏已存在的数据记录。
    """
    if not isinstance(query, str):
        query = str(query)
    normalized_query = " ".join(query.lower().split())
    return hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()[:16]
