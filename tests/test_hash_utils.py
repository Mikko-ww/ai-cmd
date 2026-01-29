"""
hash_utils 单元测试
测试哈希函数
"""

import pytest


class TestHashUtils:
    """hash_utils 测试类"""

    def test_hash_query_simple(self):
        """测试简单哈希函数"""
        from aicmd.hash_utils import hash_query_simple
        
        # 基本哈希
        hash1 = hash_query_simple("list all files")
        
        assert isinstance(hash1, str)
        assert len(hash1) == 16  # 16位哈希
        
    def test_hash_query_simple_consistency(self):
        """测试简单哈希的一致性"""
        from aicmd.hash_utils import hash_query_simple
        
        query = "list all files"
        
        hash1 = hash_query_simple(query)
        hash2 = hash_query_simple(query)
        
        # 相同查询应该产生相同哈希
        assert hash1 == hash2

    def test_hash_query_simple_normalization(self):
        """测试简单哈希的标准化"""
        from aicmd.hash_utils import hash_query_simple
        
        # 大小写应该被标准化
        hash1 = hash_query_simple("List All Files")
        hash2 = hash_query_simple("list all files")
        
        assert hash1 == hash2
        
        # 多余空格应该被折叠
        hash3 = hash_query_simple("list   all   files")
        
        assert hash1 == hash3

    def test_hash_query_simple_different_queries(self):
        """测试不同查询产生不同哈希"""
        from aicmd.hash_utils import hash_query_simple
        
        hash1 = hash_query_simple("list files")
        hash2 = hash_query_simple("delete files")
        
        assert hash1 != hash2

    def test_hash_query_normalized(self):
        """测试标准化哈希函数"""
        from aicmd.hash_utils import hash_query_normalized
        
        hash1 = hash_query_normalized("show all files")
        
        assert isinstance(hash1, str)
        assert len(hash1) == 16

    def test_hash_query_normalized_synonyms(self):
        """测试标准化哈希的同义词处理"""
        from aicmd.hash_utils import hash_query_normalized
        
        # "show" 和 "list" 是同义词，应该产生相同哈希
        hash1 = hash_query_normalized("show files")
        hash2 = hash_query_normalized("list files")
        
        assert hash1 == hash2
        
        # "remove" 和 "delete" 是同义词
        hash3 = hash_query_normalized("remove file")
        hash4 = hash_query_normalized("delete file")
        
        assert hash3 == hash4

    def test_hash_query_default_strategy(self):
        """测试默认哈希策略"""
        from aicmd.hash_utils import hash_query
        
        # 默认使用 simple 策略
        hash1 = hash_query("list files")
        hash2 = hash_query("list files", strategy="simple")
        
        assert hash1 == hash2

    def test_hash_query_normalized_strategy(self):
        """测试 normalized 策略"""
        from aicmd.hash_utils import hash_query
        
        hash1 = hash_query("show files", strategy="normalized")
        hash2 = hash_query("list files", strategy="normalized")
        
        # 同义词应该产生相同哈希
        assert hash1 == hash2

    def test_hash_query_empty_string(self):
        """测试空字符串哈希"""
        from aicmd.hash_utils import hash_query_simple, hash_query_normalized
        
        # 空字符串应该能正常处理
        hash1 = hash_query_simple("")
        hash2 = hash_query_normalized("")
        
        assert isinstance(hash1, str)
        assert isinstance(hash2, str)

    def test_hash_query_non_string_input(self):
        """测试非字符串输入"""
        from aicmd.hash_utils import hash_query_simple
        
        # 应该能处理非字符串输入
        hash1 = hash_query_simple(123)
        
        assert isinstance(hash1, str)
        assert len(hash1) == 16

    def test_hash_query_unicode(self):
        """测试 Unicode 输入"""
        from aicmd.hash_utils import hash_query_simple, hash_query_normalized
        
        # 中文查询
        hash1 = hash_query_simple("显示文件")
        hash2 = hash_query_normalized("显示文件")
        
        assert isinstance(hash1, str)
        assert isinstance(hash2, str)
        assert len(hash1) == 16
        assert len(hash2) == 16

    def test_hash_query_special_characters(self):
        """测试特殊字符"""
        from aicmd.hash_utils import hash_query_simple
        
        # 包含特殊字符的查询
        hash1 = hash_query_simple("find files with name '*.txt'")
        hash2 = hash_query_simple("connect to server:8080")
        
        assert isinstance(hash1, str)
        assert isinstance(hash2, str)
