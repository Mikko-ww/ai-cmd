"""
ConfidenceCalculator 单元测试
测试置信度计算功能
"""

import pytest
from unittest.mock import MagicMock, patch


class TestConfidenceCalculator:
    """ConfidenceCalculator 测试类"""

    def test_calculate_confidence_no_feedback(self):
        """测试无反馈时的置信度计算"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        calculator = ConfidenceCalculator()
        
        # 无反馈时应该使用初始置信度
        confidence = calculator.calculate_confidence(0, 0)
        
        assert 0.0 <= confidence <= 1.0

    def test_calculate_confidence_with_confirmations(self):
        """测试确认反馈的置信度计算"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        calculator = ConfidenceCalculator()
        
        # 只有确认反馈
        confidence1 = calculator.calculate_confidence(1, 0)
        confidence2 = calculator.calculate_confidence(5, 0)
        confidence3 = calculator.calculate_confidence(10, 0)
        
        # 更多确认应该增加置信度
        assert confidence1 < confidence2 < confidence3

    def test_calculate_confidence_with_rejections(self):
        """测试拒绝反馈的置信度计算"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        calculator = ConfidenceCalculator()
        
        # 只有拒绝反馈
        confidence1 = calculator.calculate_confidence(0, 1)
        confidence2 = calculator.calculate_confidence(0, 5)
        
        # 更多拒绝应该降低置信度
        assert confidence1 > confidence2

    def test_calculate_confidence_mixed_feedback(self):
        """测试混合反馈的置信度计算"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        calculator = ConfidenceCalculator()
        
        # 混合反馈
        confidence_balanced = calculator.calculate_confidence(5, 5)
        confidence_positive = calculator.calculate_confidence(8, 2)
        confidence_negative = calculator.calculate_confidence(2, 8)
        
        # 正面反馈更多应该有更高置信度
        assert confidence_positive > confidence_negative

    def test_calculate_confidence_bounds(self):
        """测试置信度边界"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        calculator = ConfidenceCalculator()
        
        # 极端情况
        confidence_high = calculator.calculate_confidence(100, 0)
        confidence_low = calculator.calculate_confidence(0, 100)
        
        # 始终在 [0, 1] 范围内
        assert 0.0 <= confidence_high <= 1.0
        assert 0.0 <= confidence_low <= 1.0

    def test_calculate_desire(self):
        """测试欲望值计算函数"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        calculator = ConfidenceCalculator()
        
        # 测试基本欲望值计算
        desire = calculator._calculate_desire(
            n_a=5, n_r=0,
            alpha=0.2, beta=0.6,
            s0=0.3, k=0.8
        )
        
        assert 0.0 < desire < 1.0
        
        # 更多确认应该增加欲望值
        desire_more = calculator._calculate_desire(
            n_a=10, n_r=0,
            alpha=0.2, beta=0.6,
            s0=0.3, k=0.8
        )
        
        assert desire_more > desire

    def test_time_decay_factor(self):
        """测试时间衰减因子"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        from datetime import datetime, timedelta
        
        calculator = ConfidenceCalculator()
        
        # 最近的时间应该有更高的衰减因子
        now = datetime.now()
        recent = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        old = (now - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
        
        decay_recent = calculator._calculate_time_decay_factor(recent)
        decay_old = calculator._calculate_time_decay_factor(old)
        
        assert decay_recent > decay_old

    def test_should_auto_copy(self):
        """测试自动复制判断"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        calculator = ConfidenceCalculator()
        
        # 默认 auto_copy_threshold = 1.0（来自 setting_template.json）
        # 只有满分才会自动复制
        assert calculator.should_auto_copy(1.0) is True
        
        # 低于阈值不应该自动复制
        assert calculator.should_auto_copy(0.95) is False
        assert calculator.should_auto_copy(0.85) is False
        assert calculator.should_auto_copy(0.5) is False

    def test_should_ask_confirmation(self):
        """测试确认询问判断"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        calculator = ConfidenceCalculator()
        
        # 默认 confidence_threshold=0.75, auto_copy_threshold=1.0
        # 在两者之间应该询问确认
        assert calculator.should_ask_confirmation(0.85) is True
        assert calculator.should_ask_confirmation(0.80) is True
        assert calculator.should_ask_confirmation(0.95) is True  # 0.75 <= 0.95 < 1.0
        
        # 达到或超过 auto_copy_threshold (1.0) 不需要询问
        assert calculator.should_ask_confirmation(1.0) is False
        
        # 低于 confidence_threshold (0.75) 也不需要询问（会使用 API）
        assert calculator.should_ask_confirmation(0.5) is False
        assert calculator.should_ask_confirmation(0.74) is False

    def test_should_use_cache(self):
        """测试缓存使用判断"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        calculator = ConfidenceCalculator()
        
        # 默认 confidence_threshold = 0.75（来自 setting_template.json）
        # 高于或等于阈值应该使用缓存
        assert calculator.should_use_cache(0.85) is True
        assert calculator.should_use_cache(0.90) is True
        assert calculator.should_use_cache(0.75) is True  # 等于阈值
        
        # 低于阈值不应该使用缓存
        assert calculator.should_use_cache(0.74) is False
        assert calculator.should_use_cache(0.5) is False

    def test_get_confidence_thresholds(self):
        """测试获取置信度阈值"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        calculator = ConfidenceCalculator()
        
        thresholds = calculator.get_confidence_thresholds()
        
        assert "confidence_threshold" in thresholds
        assert "auto_copy_threshold" in thresholds
        assert "similarity_threshold" in thresholds


class TestConfidenceCalculatorWithCache:
    """带缓存管理器的置信度计算器测试"""

    def test_get_confidence_stats_unavailable(self):
        """测试缓存不可用时的统计"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        calculator = ConfidenceCalculator()
        
        stats = calculator.get_confidence_stats()
        
        assert "status" in stats
        # 没有缓存管理器时应该返回不可用状态
        assert stats["status"] in ["unavailable", "error"]

    def test_update_feedback_without_cache(self):
        """测试无缓存时的反馈更新"""
        from aicmd.confidence_calculator import ConfidenceCalculator
        
        calculator = ConfidenceCalculator()
        
        success, confidence = calculator.update_feedback(
            query_hash="test_hash",
            command="test command",
            confirmed=True
        )
        
        # 无缓存时应该返回失败
        assert success is False
