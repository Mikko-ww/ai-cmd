"""
哈希工具模块
提供统一的查询哈希算法，确保各模块使用一致的哈希以避免记录错配
"""

import hashlib


def hash_query_simple(query: str) -> str:
    """
    简单的查询哈希函数 (兼容现有数据)

    规则：
    - 全部小写
    - 折叠多余空白为单空格
    - sha256 后取前 16 位
    """
    if not isinstance(query, str):
        query = str(query)
    normalized_query = " ".join(query.lower().split())
    return hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()[:16]


def hash_query_normalized(query: str) -> str:
    """
    标准化查询哈希函数 (减少同义表达重复缓存)

    规则：
    - 全部小写
    - 折叠多余空白为单空格
    - 移除常见停用词和变体
    - sha256 后取前 16 位
    """
    if not isinstance(query, str):
        query = str(query)

    # 基本标准化
    normalized_query = " ".join(query.lower().split())

    # 移除常见的变体表达
    synonyms = {
        "show": "list",
        "display": "list",
        "print": "list",
        "find": "search",
        "locate": "search",
        "remove": "delete",
        "del": "delete",
        "rm": "delete",
        "create": "make",
        "generate": "make",
        "build": "make",
    }

    words = normalized_query.split()
    normalized_words = []
    for word in words:
        # 替换同义词
        word = synonyms.get(word, word)
        normalized_words.append(word)

    final_query = " ".join(normalized_words)
    return hashlib.sha256(final_query.encode("utf-8")).hexdigest()[:16]


def hash_query(query: str, strategy: str = "simple") -> str:
    """
    统一的查询哈希函数，支持不同策略

    Args:
        query: 查询字符串
        strategy: 哈希策略 ("simple" | "normalized")

    Returns:
        哈希值字符串

    说明：选择与数据库现有实现一致的标准化方式，避免破坏已存在的数据记录。
    """
    if strategy == "normalized":
        return hash_query_normalized(query)
    else:  # 默认使用 simple 策略保持兼容性
        return hash_query_simple(query)
