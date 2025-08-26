"""
置信度计算模块
基于用户反馈（确认/拒绝）计算和更新缓存命令的置信度
"""

import math
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from .config_manager import ConfigManager
from .cache_manager import CacheManager, CacheEntry
from .error_handler import GracefulDegradationManager


class ConfidenceCalculator:
    """置信度计算器，基于用户反馈动态计算命令置信度"""

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        cache_manager: Optional[CacheManager] = None,
        degradation_manager: Optional[GracefulDegradationManager] = None,
    ):
        """初始化置信度计算器"""
        self.config = config_manager or ConfigManager()
        self.cache_manager = cache_manager
        self.degradation_manager = degradation_manager or GracefulDegradationManager()

        # 从配置获取权重参数
        self.positive_weight = self.config.get("positive_weight", 0.2)
        self.negative_weight = self.config.get("negative_weight", 0.6)
        self.decay_factor = self.config.get("confidence_decay_factor", 0.95)
        self.initial_confidence = self.config.get("initial_confidence", 0.3)

        # 时间衰减参数
        self.time_decay_enabled = self.config.get("time_decay_enabled", True)
        self.decay_half_life_days = self.config.get("decay_half_life_days", 30)

    def calculate_confidence(
        self,
        confirmation_count: int,
        rejection_count: int,
        created_at: Optional[str] = None,
        last_used: Optional[str] = None,
    ) -> float:
        """
        基于反馈次数计算置信度

        Args:
            confirmation_count: 确认次数
            rejection_count: 拒绝次数
            created_at: 创建时间（用于时间衰减）
            last_used: 最后使用时间

        Returns:
            置信度分数 (0.0 - 1.0)
        """
        # # 基础得分计算
        # positive_score = confirmation_count * self.positive_weight
        # negative_score = rejection_count * self.negative_weight

        # total_score = positive_score + negative_score
        # if total_score == 0:
        #     # 如果没有反馈，使用初始置信度
        #     base_confidence = self.initial_confidence
        # else:
        #     # 计算基础置信度
        #     base_confidence = positive_score / total_score

        base_confidence = self._calculate_desire(
            confirmation_count,
            rejection_count,
            alpha=self.positive_weight,
            beta=self.negative_weight,
            s0=self.initial_confidence,
            k=0.8,  # 可以根据需要调整敏感度
        )

        # # 总反馈次数
        # total_feedback = confirmation_count + rejection_count

        # if total_feedback == 0:
        #     # 没有反馈时使用初始置信度
        #     base_confidence = self.initial_confidence
        # else:
        #     # 使用改进的置信度计算公式
        #     net_score = positive_score - negative_score

        #     # 使用 Sigmoid 函数进行归一化，但保持简单
        #     # 避免过于复杂的数学函数
        #     if net_score >= 0:
        #         base_confidence = 0.5 + (net_score / (net_score + total_feedback * 0.5))
        #     else:
        #         base_confidence = 0.5 * (
        #             1 + net_score / (abs(net_score) + total_feedback * 0.5)
        #         )

        # 应用时间衰减
        if self.time_decay_enabled and created_at:
            time_factor = self._calculate_time_decay_factor(created_at, last_used)
            base_confidence *= time_factor

        # 确保结果在有效范围内
        return max(0.0, min(1.0, base_confidence))


    def _calculate_desire(self,n_a: int, n_r: int, alpha: float, beta: float, s0: float, k: float) -> float:
        """
        根据增强和拒绝次数计算智能提示的欲望值。

        该函数基于一个Sigmoid模型，将一个内部的“潜在得分”映射到(0, 1)区间。

        Args:
            n_a (int): 增强次数 (用户接受或主动请求)。
            n_r (int): 拒绝次数。
            alpha (float): 单次增强因子，代表每次增强对内在得分的提升量。
            beta (float): 单次降低因子，代表每次拒绝带来的惩罚。
                        根据要求，beta 应该大于 alpha。
            s0 (float): 初始得分，代表系统在无交互前的基础倾向。
                        s0=0 表示中立。
            k (float): 敏感度因子，控制函数曲线的陡峭程度。
                    k值越大，欲望值变化越剧烈。

        Returns:
            float: 计算出的欲望值，范围在 (0, 1) 之间。
        """
        if not beta > alpha > 0:
            # 添加一个检查，确保核心约束得到满足
            raise ValueError("参数必须满足约束: beta > alpha > 0")

        # 1. 计算内部潜在得分 (S)
        latent_score = s0 + n_a * alpha - n_r * beta

        # 2. 将潜在得分通过Sigmoid函数映射到 (0, 1)
        #    公式: D = 1 / (1 + e^(-k * S))
        try:
            desire_value = 1 / (1 + math.exp(-k * latent_score))
        except OverflowError:
            # 如果 latent_score 过大或过小，math.exp 可能会溢出
            # 如果 -k * S 是一个非常大的负数，e^(-kS) -> 0, D -> 1
            # 如果 -k * S 是一个非常大的正数，e^(-kS) -> ∞, D -> 0
            desire_value = 0.0 if latent_score < 0 else 1.0


        return desire_value

    


    def _calculate_time_decay_factor(
        self, created_at: str, last_used: Optional[str] = None
    ) -> float:
        """
        计算时间衰减因子

        Args:
            created_at: 创建时间
            last_used: 最后使用时间

        Returns:
            时间衰减因子 (0.0 - 1.0)
        """
        try:
            # 使用最后使用时间，如果没有则使用创建时间
            reference_time = last_used or created_at

            # 解析时间字符串
            if isinstance(reference_time, str):
                # 尝试多种时间格式
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                    try:
                        reference_dt = datetime.strptime(reference_time, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # 如果所有格式都失败，返回默认值
                    return 1.0
            else:
                reference_dt = reference_time

            # 计算天数差
            now = datetime.now()
            days_ago = (now - reference_dt).days

            # 使用指数衰减：confidence * (0.5 ^ (days / half_life))
            decay_factor = 0.5 ** (days_ago / self.decay_half_life_days)

            # 限制衰减的最小值，避免过度衰减
            min_decay_factor = 0.1
            return max(min_decay_factor, decay_factor)

        except Exception as e:
            # 时间解析失败时不应影响置信度计算
            self.degradation_manager.logger.warning(
                f"Time decay calculation failed: {e}"
            )
            return 1.0

    def update_feedback(
        self,
        query_hash: str,
        command: str,
        confirmed: bool,
        similarity_score: Optional[float] = None,
    ) -> Tuple[bool, float]:
        """
        更新用户反馈并重新计算置信度

        Args:
            query_hash: 查询哈希
            command: 执行的命令
            confirmed: 用户是否确认
            similarity_score: 查询相似度分数（可选）

        Returns:
            (更新是否成功, 新的置信度分数)
        """

        def feedback_operation():
            # if not self.cache_manager or not self.cache_manager.db.is_available:
            #     return False, 0.0

            # 查找现有缓存条目
            cache_entry = self.find_exact_match_by_hash(query_hash)

            if not cache_entry:
                # 没有找到缓存条目，可能需要创建新的
                self.degradation_manager.logger.warning(
                    f"No cache entry found for hash: {query_hash}"
                )
                return False, 0.0

            # 更新反馈计数
            if confirmed:
                new_confirmation_count = cache_entry.confirmation_count + 1
                new_rejection_count = cache_entry.rejection_count
            else:
                new_confirmation_count = cache_entry.confirmation_count
                new_rejection_count = cache_entry.rejection_count + 1

            # 重新计算置信度
            new_confidence = self.calculate_confidence(
                new_confirmation_count,
                new_rejection_count,
                cache_entry.created_at,
                cache_entry.last_used,
            )

            # 更新数据库
            update_success = self._update_cache_confidence(
                query_hash, new_confirmation_count, new_rejection_count, new_confidence
            )

            if update_success:
                # 记录反馈历史
                self._record_feedback_history(
                    query_hash, command, confirmed, similarity_score
                )
                return True, new_confidence
            else:
                return False, cache_entry.confidence_score

        def fallback_operation():
            return False, 0.0

        return self.degradation_manager.with_cache_fallback(
            feedback_operation, fallback_operation, "update_feedback"
        )

    def _update_cache_confidence(
        self,
        query_hash: str,
        confirmation_count: int,
        rejection_count: int,
        new_confidence: float,
    ) -> bool:
        """更新缓存条目的置信度和反馈计数"""
        if not self.cache_manager or not self.cache_manager.db.is_available:
            return False

        update_sql = """
            UPDATE enhanced_cache 
            SET confidence_score = ?, confirmation_count = ?, rejection_count = ?,
                last_used = CURRENT_TIMESTAMP
            WHERE query_hash = ?
        """

        result = self.cache_manager.db.execute_query(
            update_sql,
            (new_confidence, confirmation_count, rejection_count, query_hash),
        )

        return result and isinstance(result, int) and result > 0

    def _record_feedback_history(
        self,
        query_hash: str,
        command: str,
        confirmed: bool,
        similarity_score: Optional[float] = None,
    ):
        """记录反馈历史到数据库"""
        if not self.cache_manager or not self.cache_manager.db.is_available:
            return

        action = "confirmed" if confirmed else "rejected"

        insert_sql = """
            INSERT INTO feedback_history (query_hash, command, action, timestamp)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """

        try:
            self.cache_manager.db.execute_query(
                insert_sql, (query_hash, command, action)
            )
        except Exception as e:
            self.degradation_manager.logger.warning(
                f"Failed to record feedback history: {e}"
            )

    def find_exact_match_by_hash(self, query_hash: str) -> Optional[Any]:
        """根据哈希查找精确匹配的缓存条目"""
        if not self.cache_manager or not self.cache_manager.db.is_available:
            return None

        select_sql = """
            SELECT id, query, query_hash, command, confidence_score,
                   confirmation_count, rejection_count, last_used, created_at,
                   os_type, shell_type
            FROM enhanced_cache 
            WHERE query_hash = ?
        """

        result = self.cache_manager.db.execute_query(
            select_sql, (query_hash,), fetch=True
        )

        if result and isinstance(result, list) and len(result) > 0:
            # from self.cache_manager import CacheEntry

            return CacheEntry.from_db_row(result[0])

        return None

    def get_confidence_thresholds(self) -> Dict[str, float]:
        """获取置信度阈值配置"""
        return {
            "confidence_threshold": self.config.get("confidence_threshold", 0.8),
            "auto_copy_threshold": self.config.get("auto_copy_threshold", 0.9),
            "similarity_threshold": self.config.get("similarity_threshold", 0.7),
        }

    def should_auto_copy(self, confidence: float) -> bool:
        """判断是否应该自动复制"""
        auto_copy_threshold = self.config.get("auto_copy_threshold", 0.9)
        return confidence >= auto_copy_threshold

    def should_ask_confirmation(self, confidence: float) -> bool:
        """判断是否应该询问用户确认"""
        confidence_threshold = self.config.get("confidence_threshold", 0.8)
        auto_copy_threshold = self.config.get("auto_copy_threshold", 0.9)
        return confidence_threshold <= confidence < auto_copy_threshold

    def should_use_cache(self, confidence: float) -> bool:
        """判断是否应该使用缓存"""
        confidence_threshold = self.config.get("confidence_threshold", 0.8)
        return confidence >= confidence_threshold

    def get_confidence_stats(self) -> Dict[str, Any]:
        """获取置信度统计信息"""

        def stats_operation():
            if not self.cache_manager or not self.cache_manager.db.is_available:
                return {"status": "unavailable"}

            status = {}

            # 置信度分布统计
            confidence_ranges = [
                ("very_high", 0.9, 1.0),
                ("high", 0.8, 0.9),
                ("medium", 0.5, 0.8),
                ("low", 0.0, 0.5),
            ]

            for range_name, min_conf, max_conf in confidence_ranges:
                count_sql = """
                    SELECT COUNT(*) FROM enhanced_cache 
                    WHERE confidence_score >= ? AND confidence_score < ?
                """
                result = self.cache_manager.db.execute_query(
                    count_sql, (min_conf, max_conf), fetch=True
                )
                if result and isinstance(result, list) and len(result) > 0:
                    status[f"{range_name}_confidence_count"] = result[0][0]
                else:
                    status[f"{range_name}_confidence_count"] = 0

            # 反馈统计
            feedback_sql = """
                SELECT 
                    SUM(confirmation_count) as total_confirmations,
                    SUM(rejection_count) as total_rejections,
                    AVG(confidence_score) as avg_confidence
                FROM enhanced_cache
            """
            result = self.cache_manager.db.execute_query(feedback_sql, fetch=True)
            if result and isinstance(result, list) and len(result) > 0:
                row = result[0]
                status["total_confirmations"] = row[0] or 0
                status["total_rejections"] = row[1] or 0
                status["avg_confidence"] = round(row[2] or 0, 3)

            status["status"] = "available"
            return status

        def fallback_operation():
            return {"status": "error", "message": "Confidence status unavailable"}

        return self.degradation_manager.with_cache_fallback(
            stats_operation, fallback_operation, "get_confidence_stats"
        )

    def cleanup_low_confidence_entries(
        self, threshold: float = 0.1, max_cleanup: int = 50
    ):
        """清理低置信度的缓存条目"""

        def cleanup_operation():
            if not self.cache_manager or not self.cache_manager.db.is_available:
                return 0

            # 找到低置信度条目
            select_sql = """
                SELECT query_hash FROM enhanced_cache 
                WHERE confidence_score < ? 
                ORDER BY confidence_score ASC, last_used ASC 
                LIMIT ?
            """

            result = self.cache_manager.db.execute_query(
                select_sql, (threshold, max_cleanup), fetch=True
            )

            if not result or not isinstance(result, list):
                return 0

            # 删除低置信度条目
            cleanup_count = 0
            for row in result:
                query_hash = row[0]
                if self.cache_manager.delete_cache_entry(query_hash):
                    cleanup_count += 1

            if cleanup_count > 0:
                print(f"Cleaned up {cleanup_count} low confidence cache entries")

            return cleanup_count

        def fallback_operation():
            return 0

        return self.degradation_manager.with_cache_fallback(
            cleanup_operation, fallback_operation, "cleanup_low_confidence_entries"
        )

    def recalculate_all_confidence(self) -> int:
        """重新计算所有缓存条目的置信度"""

        def recalc_operation():
            if not self.cache_manager or not self.cache_manager.db.is_available:
                return 0

            # 获取所有缓存条目
            select_sql = """
                SELECT query_hash, confirmation_count, rejection_count, 
                       created_at, last_used
                FROM enhanced_cache
            """

            result = self.cache_manager.db.execute_query(select_sql, fetch=True)
            if not result or not isinstance(result, list):
                return 0

            update_count = 0
            for row in result:
                query_hash, conf_count, rej_count, created_at, last_used = row

                # 重新计算置信度
                new_confidence = self.calculate_confidence(
                    conf_count, rej_count, created_at, last_used
                )

                # 更新数据库
                if self._update_cache_confidence(
                    query_hash, conf_count, rej_count, new_confidence
                ):
                    update_count += 1

            if update_count > 0:
                print(f"Recalculated confidence for {update_count} cache entries")

            return update_count

        def fallback_operation():
            return 0

        return self.degradation_manager.with_cache_fallback(
            recalc_operation, fallback_operation, "recalculate_all_confidence"
        )
