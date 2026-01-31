"""
QueryMatcher 单元测试
测试查询匹配和相似度计算
"""

import pytest


class TestQueryMatcher:
    """QueryMatcher 测试类"""

    def test_normalize_query(self):
        """测试查询标准化"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        # 基本标准化
        words = matcher.normalize_query("list all files in directory")
        assert "list" in words
        assert "files" in words
        assert "directory" in words
        assert "all" in words  # "all" 不在停用词列表中
        # "in" 在停用词列表中会被移除
        assert "in" not in words

    def test_normalize_query_with_synonyms(self):
        """测试同义词替换"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        # "show" 应该被替换为 "list"
        words1 = matcher.normalize_query("show files")
        words2 = matcher.normalize_query("list files")
        
        # 标准化后应该相同
        assert set(words1) == set(words2)
        
        # "remove" 应该被替换为 "delete"
        words3 = matcher.normalize_query("remove file")
        words4 = matcher.normalize_query("delete file")
        
        assert set(words3) == set(words4)

    def test_normalize_query_chinese(self):
        """测试中文查询标准化"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        words = matcher.normalize_query("显示当前目录")
        
        # 中文文本作为一个整体被处理（因为没有空格分隔）
        # 整个字符串会被作为一个词返回
        assert len(words) >= 1
        # 验证返回的内容包含中文
        result_str = "".join(words)
        assert "显示" in result_str or "目录" in result_str

    def test_calculate_similarity_identical(self):
        """测试相同查询的相似度"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        similarity = matcher.calculate_similarity(
            "list all files",
            "list all files"
        )
        
        # 相同查询应该返回 1.0
        assert similarity == 1.0

    def test_calculate_similarity_synonyms(self):
        """测试同义词查询的相似度"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        similarity = matcher.calculate_similarity(
            "show files",
            "list files"
        )
        
        # 同义词查询应该有高相似度
        assert similarity >= 0.7

    def test_calculate_similarity_different(self):
        """测试不同查询的相似度"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        similarity = matcher.calculate_similarity(
            "list files",
            "connect server"
        )
        
        # 不同查询应该有低相似度
        assert similarity < 0.5

    def test_calculate_similarity_empty(self):
        """测试空查询的相似度"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        # 两个空查询
        assert matcher.calculate_similarity("", "") == 1.0
        
        # 一个空查询
        assert matcher.calculate_similarity("list files", "") == 0.0
        assert matcher.calculate_similarity("", "list files") == 0.0

    def test_get_query_hash(self):
        """测试查询哈希生成"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        hash1 = matcher.get_query_hash("list files")
        hash2 = matcher.get_query_hash("list files")
        hash3 = matcher.get_query_hash("delete files")
        
        # 相同查询应该产生相同哈希
        assert hash1 == hash2
        # 不同查询应该产生不同哈希
        assert hash1 != hash3

    def test_is_exact_match(self):
        """测试精确匹配检查"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        # 相同查询
        assert matcher.is_exact_match("list files", "list files") is True
        
        # 大小写不同但应该匹配（标准化处理）
        assert matcher.is_exact_match("List Files", "list files") is True
        
        # 不同查询
        assert matcher.is_exact_match("list files", "delete files") is False

    def test_find_similar_queries(self):
        """测试查找相似查询"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        cached_queries = [
            ("list all files", "ls -la"),
            ("show directory contents", "ls"),
            ("delete temp files", "rm -rf temp"),
            ("connect to server", "ssh server"),
        ]
        
        similar = matcher.find_similar_queries(
            "show all files",
            cached_queries,
            threshold=0.5
        )
        
        # 应该找到相似的查询
        assert len(similar) > 0
        
        # 结果应该按相似度降序排列
        if len(similar) > 1:
            assert similar[0][2] >= similar[1][2]

    def test_get_query_categories(self):
        """测试查询分类"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        # Git 相关查询
        categories = matcher.get_query_categories("git commit changes")
        assert "git" in categories
        
        # Docker 相关查询
        categories = matcher.get_query_categories("docker build image")
        assert "docker" in categories
        
        # Python 相关查询
        categories = matcher.get_query_categories("pip install package")
        assert "python" in categories

    def test_extract_key_parameters(self):
        """测试提取关键参数"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        # 提取路径
        params = matcher.extract_key_parameters("copy file /tmp/test.txt")
        assert "paths" in params
        assert "/tmp/test.txt" in params["paths"]
        
        # 提取端口号
        params = matcher.extract_key_parameters("connect to server:8080")
        assert "ports" in params
        assert "8080" in params["ports"]
        
        # 提取 IP 地址
        params = matcher.extract_key_parameters("connect to 192.168.1.1")
        assert "ips" in params
        assert "192.168.1.1" in params["ips"]

    def test_add_synonym(self):
        """测试添加同义词"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        # 添加新同义词
        matcher.add_synonym("deploy", ["release", "publish"])
        
        # 验证同义词已添加
        words1 = matcher.normalize_query("deploy app")
        words2 = matcher.normalize_query("release app")
        words3 = matcher.normalize_query("publish app")
        
        assert set(words1) == set(words2) == set(words3)

    def test_get_matching_stats(self):
        """测试获取匹配器统计"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        stats = matcher.get_matching_stats()
        
        assert "synonym_groups" in stats
        assert "total_synonyms" in stats
        assert "stop_words" in stats
        assert stats["synonym_groups"] > 0
        assert stats["stop_words"] > 0


class TestQueryMatcherPerformance:
    """测试查询匹配器的性能优化功能"""
    
    def test_precompute_normalized_queries(self):
        """测试预计算标准化查询"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        # 预计算一些查询
        queries = ["list all files", "show directories", "create new folder"]
        matcher.precompute_normalized_queries(queries)
        
        # 验证缓存已创建
        assert len(matcher._normalized_cache) == 3
        
        # 验证缓存内容正确
        for query in queries:
            assert query in matcher._normalized_cache
            assert isinstance(matcher._normalized_cache[query], set)
    
    def test_clear_normalized_cache(self):
        """测试清空预计算缓存"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        # 预计算查询
        matcher.precompute_normalized_queries(["test query"])
        assert len(matcher._normalized_cache) > 0
        
        # 清空缓存
        matcher.clear_normalized_cache()
        assert len(matcher._normalized_cache) == 0
    
    def test_find_similar_queries_with_fast_filter(self):
        """测试优化后的相似查询查找（带快速过滤）"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        # 创建一些缓存查询
        cached_queries = [
            ("list all files", "ls -la"),
            ("show directories", "ls -d */"),
            ("create new folder", "mkdir new_folder"),
            ("delete old files", "rm -f old*"),
            ("completely different query", "some command"),
        ]
        
        # 查找相似查询
        target = "list files in directory"
        similar = matcher.find_similar_queries(target, cached_queries, threshold=0.3)
        
        # 应该找到一些相似的查询
        assert len(similar) > 0
        
        # 验证结果格式
        for query, command, similarity in similar:
            assert isinstance(query, str)
            assert isinstance(command, str)
            assert isinstance(similarity, float)
            assert 0 <= similarity <= 1
        
        # 验证结果按相似度降序排列
        similarities = [s for _, _, s in similar]
        assert similarities == sorted(similarities, reverse=True)
    
    def test_find_similar_queries_empty_target(self):
        """测试空目标查询的处理"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        cached_queries = [("list files", "ls"), ("show dirs", "ls -d")]
        
        # 空查询应该返回空列表
        similar = matcher.find_similar_queries("", cached_queries)
        assert similar == []
    
    def test_find_similar_queries_performance_optimization(self):
        """测试大量查询时的性能优化效果"""
        from aicmd.query_matcher import QueryMatcher
        
        matcher = QueryMatcher()
        
        # 创建大量缓存查询
        cached_queries = [(f"query {i} test", f"command {i}") for i in range(100)]
        
        # 添加一些相关查询
        cached_queries.extend([
            ("list files test", "ls test"),
            ("show files test", "ls -la test"),
            ("display files test", "find . -name test"),
        ])
        
        # 查找相似查询
        target = "list test files"
        similar = matcher.find_similar_queries(target, cached_queries, threshold=0.3)
        
        # 应该能找到相关查询
        assert len(similar) > 0
        
        # 验证预计算缓存被使用
        assert len(matcher._normalized_cache) > 0
