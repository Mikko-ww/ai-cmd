"""
查询匹配算法模块
提供基础的查询匹配功能，包括精确匹配和相似性匹配
"""

import re
import hashlib
from typing import List, Dict, Set, Tuple, Optional
from difflib import SequenceMatcher


class QueryMatcher:
    """基础查询匹配器，提供查询标准化和相似度计算功能"""
    
    def __init__(self):
        """初始化查询匹配器，包含基础同义词映射"""
        # 基础同义词映射 - 可扩展
        self.synonyms = {
            # 文件操作
            'list': ['show', 'display', 'ls', 'dir', '列出', '显示', '查看'],
            'create': ['make', 'new', 'mkdir', 'touch', '创建', '新建'],
            'delete': ['remove', 'rm', 'del', 'unlink', '删除', '移除'],
            'copy': ['cp', 'duplicate', '复制', '拷贝'],
            'move': ['mv', 'rename', '移动', '重命名'],
            'find': ['search', 'locate', 'grep', '查找', '搜索'],
            
            # 系统操作
            'install': ['add', 'setup', '安装', '添加'],
            'update': ['upgrade', 'refresh', '更新', '升级'],
            'start': ['run', 'execute', 'launch', '启动', '运行'],
            'stop': ['kill', 'terminate', 'halt', '停止', '终止'],
            'status': ['check', 'info', 'state', '状态', '检查'],
            
            # 网络操作
            'download': ['fetch', 'get', 'pull', '下载', '获取'],
            'upload': ['push', 'send', '上传', '发送'],
            'connect': ['link', 'join', '连接', '链接'],
            
            # 通用词汇
            'all': ['everything', 'total', '全部', '所有'],
            'current': ['now', 'present', '当前', '现在'],
            'recursive': ['r', 'deep', '递归', '深度'],
            'force': ['f', 'overwrite', '强制', '覆盖']
        }
        
        # 反向索引，提高查找效率
        self._build_reverse_synonyms()
        
        # 常见停用词
        self.stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'must', 'shall', 'to', 'of', 'in',
            'on', 'at', 'by', 'for', 'with', 'from', 'up', 'about', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'between',
            'among', 'under', 'over', 'out', 'off', 'down', 'so', 'but', 'and',
            'or', 'not', 'no', 'nor', 'as', 'if', 'than', 'then', 'now', 'here',
            'there', 'when', 'where', 'why', 'how', 'what', 'which', 'who',
            'whom', 'this', 'that', 'these', 'those', 'my', 'your', 'his',
            'her', 'its', 'our', 'their'
        }
    
    def _build_reverse_synonyms(self):
        """构建反向同义词索引"""
        self.reverse_synonyms = {}
        for canonical, synonyms in self.synonyms.items():
            self.reverse_synonyms[canonical] = canonical
            for synonym in synonyms:
                self.reverse_synonyms[synonym] = canonical
    
    def normalize_query(self, query: str) -> List[str]:
        """
        标准化查询字符串
        
        Args:
            query: 原始查询字符串
            
        Returns:
            标准化后的词汇列表
        """
        if not query:
            return []
        
        # 提取词汇（支持中英文和数字）
        words = re.findall(r'[\w\u4e00-\u9fff]+', query.lower())
        
        # 过滤停用词
        words = [word for word in words if word not in self.stop_words]
        
        # 应用同义词替换
        normalized_words = []
        for word in words:
            canonical = self.reverse_synonyms.get(word, word)
            normalized_words.append(canonical)
        
        return normalized_words
    
    def calculate_similarity(self, query1: str, query2: str) -> float:
        """
        计算两个查询之间的相似度
        
        Args:
            query1: 第一个查询
            query2: 第二个查询
            
        Returns:
            相似度分数 (0.0 - 1.0)
        """
        words1 = set(self.normalize_query(query1))
        words2 = set(self.normalize_query(query2))
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        # Jaccard 相似度
        intersection = words1 & words2
        union = words1 | words2
        jaccard = len(intersection) / len(union)
        
        # 序列相似度（考虑词序）
        seq1 = ' '.join(sorted(words1))
        seq2 = ' '.join(sorted(words2))
        sequence_similarity = SequenceMatcher(None, seq1, seq2).ratio()
        
        # 综合相似度（Jaccard 权重更高）
        combined_similarity = 0.7 * jaccard + 0.3 * sequence_similarity
        
        return round(combined_similarity, 3)
    
    def get_query_hash(self, query: str) -> str:
        """
        生成查询的标准化哈希值
        
        Args:
            query: 查询字符串
            
        Returns:
            16位哈希字符串
        """
        normalized_words = self.normalize_query(query)
        # 排序确保哈希稳定性
        normalized_text = ' '.join(sorted(normalized_words))
        
        if not normalized_text:
            normalized_text = query.lower().strip()
        
        return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()[:16]
    
    def find_similar_queries(self, target_query: str, cached_queries: List[Tuple[str, str]], 
                           threshold: float = 0.7) -> List[Tuple[str, str, float]]:
        """
        从缓存查询中找到相似的查询
        
        Args:
            target_query: 目标查询
            cached_queries: 缓存的查询列表 [(query, command), ...]
            threshold: 相似度阈值
            
        Returns:
            相似查询列表 [(query, command, similarity), ...] 按相似度降序排列
        """
        similar_queries = []
        
        for cached_query, command in cached_queries:
            similarity = self.calculate_similarity(target_query, cached_query)
            if similarity >= threshold:
                similar_queries.append((cached_query, command, similarity))
        
        # 按相似度降序排列
        similar_queries.sort(key=lambda x: x[2], reverse=True)
        return similar_queries
    
    def is_exact_match(self, query1: str, query2: str) -> bool:
        """
        检查两个查询是否完全匹配（基于标准化）
        
        Args:
            query1: 第一个查询
            query2: 第二个查询
            
        Returns:
            是否完全匹配
        """
        return self.get_query_hash(query1) == self.get_query_hash(query2)
    
    def get_query_categories(self, query: str) -> Set[str]:
        """
        获取查询的分类标签
        
        Args:
            query: 查询字符串
            
        Returns:
            分类标签集合
        """
        normalized_words = self.normalize_query(query)
        categories = set()
        
        # 基于同义词映射推断类别
        for word in normalized_words:
            canonical = self.reverse_synonyms.get(word, word)
            if canonical in self.synonyms:
                categories.add(canonical)
        
        # 基于关键词模式识别特定类别
        query_lower = query.lower()
        
        if any(pattern in query_lower for pattern in ['git', 'repository', 'repo', 'commit']):
            categories.add('git')
        if any(pattern in query_lower for pattern in ['docker', 'container', 'image']):
            categories.add('docker')
        if any(pattern in query_lower for pattern in ['npm', 'node', 'package.json']):
            categories.add('nodejs')
        if any(pattern in query_lower for pattern in ['python', 'pip', 'requirements']):
            categories.add('python')
        if any(pattern in query_lower for pattern in ['ssh', 'scp', 'rsync']):
            categories.add('network')
        if any(pattern in query_lower for pattern in ['log', 'grep', 'awk', 'sed']):
            categories.add('text_processing')
        
        return categories
    
    def extract_key_parameters(self, query: str) -> Dict[str, str]:
        """
        从查询中提取关键参数
        
        Args:
            query: 查询字符串
            
        Returns:
            参数字典
        """
        parameters = {}
        
        # 提取文件路径
        path_pattern = r'[/~][\w/.-]*|[\w.-]+\.[\w]+'
        paths = re.findall(path_pattern, query)
        if paths:
            parameters['paths'] = paths
        
        # 提取端口号
        port_pattern = r':(\d{2,5})\b'
        ports = re.findall(port_pattern, query)
        if ports:
            parameters['ports'] = ports
        
        # 提取 IP 地址
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ips = re.findall(ip_pattern, query)
        if ips:
            parameters['ips'] = ips
        
        # 提取选项标志
        flag_pattern = r'-+[\w-]+'
        flags = re.findall(flag_pattern, query)
        if flags:
            parameters['flags'] = flags
        
        return parameters
    
    def add_synonym(self, canonical: str, synonyms: List[str]):
        """
        添加新的同义词映射
        
        Args:
            canonical: 标准词汇
            synonyms: 同义词列表
        """
        if canonical not in self.synonyms:
            self.synonyms[canonical] = []
        
        self.synonyms[canonical].extend(synonyms)
        self._build_reverse_synonyms()  # 重建反向索引
    
    def get_matching_stats(self) -> Dict[str, int]:
        """
        获取匹配器统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'synonym_groups': len(self.synonyms),
            'total_synonyms': sum(len(synonyms) for synonyms in self.synonyms.values()),
            'stop_words': len(self.stop_words)
        }
