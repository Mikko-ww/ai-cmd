"""
Command Handler Module

Handles the core command generation logic with caching, confidence, 
and interactive features.
"""

from typing import Optional, Dict, Any
from .config_manager import ConfigManager
from .cache_manager import CacheManager
from .confidence_calculator import ConfidenceCalculator
from .query_matcher import QueryMatcher
from .interactive_manager import InteractiveManager, ConfirmationResult
from .multi_provider_api_client import MultiProviderAPIClient
from .safety_checker import CommandSafetyChecker
from .clipboard_manager import ClipboardManager
from .error_handler import GracefulDegradationManager
from .logger import logger


class CommandHandler:
    """
    Handles command generation with enhanced features like caching,
    confidence scoring, and user interaction.
    """
    
    def __init__(self, degradation_manager: GracefulDegradationManager):
        """
        Initialize command handler.
        
        Args:
            degradation_manager: Error handling and degradation manager
        """
        self.degradation_manager = degradation_manager
    
    def get_command_original(self, prompt: str, base_url: Optional[str] = None) -> str:
        """
        Original command generation function for backward compatibility and fallback.
        
        Args:
            prompt: Natural language prompt
            base_url: Optional API base URL override
            
        Returns:
            Generated shell command or error message
        """
        def main_api_operation():
            api_client = MultiProviderAPIClient(
                degradation_manager=self.degradation_manager, base_url=base_url
            )
            return api_client.send_chat_with_fallback(prompt)
        
        def fallback_operation():
            return "Error: Unable to process request due to system issues."
        
        # 使用错误处理机制保护API调用
        return self.degradation_manager.with_cache_fallback(
            main_api_operation, fallback_operation, "get_shell_command_original"
        )
    
    def get_command(
        self,
        prompt: str,
        force_api: bool = False,
        no_clipboard: bool = False,
        no_color: bool = False,
        json_output: bool = False,
        base_url: Optional[str] = None,
    ) -> Any:
        """
        Enhanced command generation with caching, confidence, and user interaction.
        
        Args:
            prompt: Natural language prompt
            force_api: Force API call, bypass cache
            no_clipboard: Disable clipboard copying
            no_color: Disable colored output
            json_output: Return JSON formatted output
            base_url: Optional API base URL override
            
        Returns:
            Generated command string or JSON dict with metadata
        """
        # 初始化配置管理器
        config = ConfigManager()
        
        # 检查是否启用交互模式
        if not config.get("interactive_mode", False) or force_api:
            # 交互模式未启用或强制使用API，使用原始功能
            return self._handle_simple_mode(
                prompt, base_url, no_clipboard, json_output, config
            )
        
        # 交互模式启用，使用增强功能
        try:
            return self._handle_interactive_mode(
                prompt, base_url, no_clipboard, no_color, json_output, config
            )
        except Exception as e:
            # 任何异常都降级到原始功能
            self.degradation_manager.logger.error(f"Enhanced shell command error: {e}")
            return self._handle_fallback(prompt, base_url, json_output)
    
    def _handle_simple_mode(
        self,
        prompt: str,
        base_url: Optional[str],
        no_clipboard: bool,
        json_output: bool,
        config: ConfigManager,
    ) -> Any:
        """Handle simple non-interactive mode"""
        command = self.get_command_original(prompt, base_url=base_url)
        if command:
            logger.info(command)
            
            # 安全检查
            safety_checker = CommandSafetyChecker(config)
            safety_info = safety_checker.get_safety_info(command)
            
            # 显示安全警告
            if safety_info["is_dangerous"] and safety_info["warnings"]:
                for warning in safety_info["warnings"]:
                    print(warning)
            
            # 复制到剪贴板（考虑安全和用户选择）
            clipboard = ClipboardManager(logger=self.degradation_manager.logger)
            copied, warning_msg = clipboard.get_copy_status_message(
                command, no_clipboard, safety_info
            )
            if copied:
                # 在非交互模式下显示复制确认
                print("✓ Copied to clipboard!")
            elif warning_msg:
                print(warning_msg)
        
        return command
    
    def _handle_interactive_mode(
        self,
        prompt: str,
        base_url: Optional[str],
        no_clipboard: bool,
        no_color: bool,
        json_output: bool,
        config: ConfigManager,
    ) -> Any:
        """Handle interactive mode with caching and confidence"""
        # 初始化所有管理器
        cache_manager = CacheManager(config, self.degradation_manager)
        confidence_calc = ConfidenceCalculator(
            config, cache_manager, self.degradation_manager
        )
        query_matcher = QueryMatcher()
        interactive_manager = InteractiveManager(
            config, self.degradation_manager, no_color=no_color
        )
        
        # 查找精确匹配的缓存
        cached_entry = cache_manager.find_exact_match(prompt)
        
        command = None
        source = "API"
        confidence = 0.0
        similarity = 0.0
        api_command = None
        
        if cached_entry:
            # 处理精确匹配的缓存
            command, source, confidence, similarity = self._handle_exact_match(
                cached_entry, prompt, base_url, no_clipboard,
                config, cache_manager, confidence_calc, interactive_manager
            )
            if command:
                return command
        else:
            # 查找相似缓存
            result = self._handle_similar_match(
                prompt, base_url, cache_manager, confidence_calc,
                query_matcher, interactive_manager, config
            )
            if result:
                command, source, confidence, similarity, api_command = result
        
        # 如果还没有命令，调用API
        if not command:
            interactive_manager.display_metrics(0.0, 0.0)
            if api_command is None:
                interactive_manager.display_info("API 请求中...", color="blue")
                api_command = self.get_command_original(prompt, base_url=base_url)
            command = api_command
            source = "API"
        
        # 验证命令有效性
        if not command or command.startswith("Error:"):
            print(f"Failed to get valid command: {command}")
            return command
        
        # 处理用户确认和反馈
        return self._handle_confirmation_and_feedback(
            command, source, confidence, similarity, prompt,
            no_clipboard, json_output, config, cache_manager,
            confidence_calc, interactive_manager
        )
    
    def _handle_exact_match(
        self,
        cached_entry,
        prompt: str,
        base_url: Optional[str],
        no_clipboard: bool,
        config: ConfigManager,
        cache_manager: CacheManager,
        confidence_calc: ConfidenceCalculator,
        interactive_manager: InteractiveManager,
    ) -> tuple:
        """Handle exact cache match"""
        # 找到缓存条目，计算置信度
        confidence = confidence_calc.calculate_confidence(
            cached_entry.confirmation_count,
            cached_entry.rejection_count,
            cached_entry.created_at,
            cached_entry.last_used,
        )
        
        # 在做决策前优先展示指标（精确匹配场景按用户期望显示 Similarity: 0.0%）
        interactive_manager.display_metrics(confidence, 0.0)
        
        # 根据置信度决定处理方式
        auto_copy_threshold = float(config.get("auto_copy_threshold", 0.9) or 0.9)
        
        # 安全检查（提前进行以影响自动复制决策）
        safety_checker = CommandSafetyChecker(config)
        safety_info = safety_checker.get_safety_info(cached_entry.command or "")
        
        if (
            confidence >= auto_copy_threshold
            and not safety_info["force_confirmation"]
        ):
            # 高置信度且不强制确认：直接使用缓存并自动复制
            command = cached_entry.command or ""
            source = "Cache (High Confidence)"
            if command:
                logger.info(command)
            
            # 显示安全警告（如果有）
            if safety_info["is_dangerous"] and safety_info["warnings"]:
                print()
                for warning in safety_info["warnings"]:
                    print(warning)
                print()
            
            clipboard = ClipboardManager(logger=self.degradation_manager.logger)
            copied = clipboard.copy_command(command, no_clipboard, safety_info)
            interactive_manager.display_success_message(command, copied=copied)
            if not copied and clipboard.should_show_safety_warning(safety_info):
                print("⚠️  Clipboard copying disabled for safety reasons")
            
            # 更新使用时间和隐式确认
            try:
                qh = (
                    cached_entry.query_hash
                    or cache_manager.db.generate_query_hash(prompt)
                )
                cache_manager.update_last_used(qh)
                confidence_calc.update_feedback(qh, command or "", True, 1.0)
            except Exception:
                pass
            
            return command, source, confidence, 1.0
        
        confidence_threshold = float(config.get("confidence_threshold", 0.8) or 0.8)
        if confidence >= confidence_threshold:
            # 中等置信度：使用缓存但询问用户确认
            command = cached_entry.command or ""
            source = "Cache"
            similarity = 1.0  # 精确匹配
        else:
            # 低置信度：调用API获取新命令
            interactive_manager.display_info("API 请求中...", color="blue")
            api_command = self.get_command_original(prompt, base_url=base_url)
            if not api_command or api_command.startswith("Error:"):
                # API调用失败，使用缓存作为备选
                command = cached_entry.command or ""
                source = "Cache (API Failed)"
            else:
                command = api_command
                source = "API"
        
        return command, source, confidence, similarity
    
    def _handle_similar_match(
        self,
        prompt: str,
        base_url: Optional[str],
        cache_manager: CacheManager,
        confidence_calc: ConfidenceCalculator,
        query_matcher: QueryMatcher,
        interactive_manager: InteractiveManager,
        config: ConfigManager,
    ) -> Optional[tuple]:
        """Handle similar cache match"""
        all_cached_queries = cache_manager.get_all_cached_queries()
        
        if not all_cached_queries:
            return None
        
        similarity_threshold = float(
            config.get("similarity_threshold", 0.7) or 0.7
        )
        similar_queries = query_matcher.find_similar_queries(
            prompt, all_cached_queries, threshold=similarity_threshold
        )
        
        if not similar_queries:
            return None
        
        # 找到相似查询，使用最相似的一个
        best_match = similar_queries[0]  # 已按相似度排序
        cached_query, cached_command, similarity = best_match
        
        # 获取该缓存条目的详细信息
        cached_entry = cache_manager.find_exact_match(cached_query)
        if not cached_entry:
            return None
        
        confidence = confidence_calc.calculate_confidence(
            cached_entry.confirmation_count,
            cached_entry.rejection_count,
            cached_entry.created_at,
            cached_entry.last_used,
        )
        
        # 结合相似度和置信度
        combined_confidence = confidence * similarity
        
        # 在做决策前优先展示指标（使用当前的 confidence/similarity）
        interactive_manager.display_metrics(confidence, similarity)
        
        confidence_threshold = float(
            config.get("confidence_threshold", 0.8) or 0.8
        )
        if combined_confidence >= confidence_threshold:
            command = cached_command
            source = "Similar Cache"
            api_command = None
        else:
            # 相似度或置信度不够，调用API
            interactive_manager.display_info("API 请求中...", color="blue")
            api_command = self.get_command_original(prompt, base_url=base_url)
            command = api_command
            source = "API"
        
        return command, source, confidence, similarity, api_command
    
    def _handle_confirmation_and_feedback(
        self,
        command: str,
        source: str,
        confidence: float,
        similarity: float,
        prompt: str,
        no_clipboard: bool,
        json_output: bool,
        config: ConfigManager,
        cache_manager: CacheManager,
        confidence_calc: ConfidenceCalculator,
        interactive_manager: InteractiveManager,
    ) -> Any:
        """Handle user confirmation and feedback recording"""
        # 安全检查
        safety_checker = CommandSafetyChecker(config)
        safety_info = safety_checker.get_safety_info(command)
        
        # 显示安全警告
        if safety_info["is_dangerous"] and safety_info["warnings"]:
            print()  # 添加空行提高可读性
            for warning in safety_info["warnings"]:
                print(warning)
            print()  # 添加空行
        
        # 用户交互确认
        need_confirmation = (
            interactive_manager.should_prompt_for_confirmation(confidence)
            or safety_info["force_confirmation"]
        )
        
        clipboard = ClipboardManager(logger=self.degradation_manager.logger)
        
        if need_confirmation:
            # 询问用户确认
            # 为避免重复打印指标，这里不再传入 confidence/similarity
            result, details = interactive_manager.prompt_user_confirmation(
                command, source, None, None
            )
            
            confirmed = result == ConfirmationResult.CONFIRMED
            
            if confirmed:
                # 用户确认，复制到剪贴板（考虑安全和用户选择）
                copied = clipboard.copy_command(command, no_clipboard, safety_info)
                interactive_manager.display_success_message(command, copied=copied)
                if not copied and clipboard.should_show_safety_warning(safety_info):
                    print("⚠️  Clipboard copying disabled for safety reasons")
            else:
                # 用户拒绝
                interactive_manager.display_rejection_message("Command not copied")
            
            # 超时也视为确认
            if result == ConfirmationResult.TIMEOUT:
                confirmed = True
        else:
            # 不需要确认，直接复制（考虑安全和用户选择）
            confirmed = True
            copied = clipboard.copy_command(command, no_clipboard, safety_info)
            interactive_manager.display_success_message(command, copied=copied)
            if not copied and clipboard.should_show_safety_warning(safety_info):
                print("⚠️  Clipboard copying disabled for safety reasons")
        
        # 保存到缓存（如果是新命令）
        if source == "API":
            cache_manager.save_cache_entry(prompt, command)
        
        # 更新反馈和置信度
        # 使用数据库统一哈希以确保可查到记录
        current_query_hash = cache_manager.db.generate_query_hash(prompt)
        confidence_calc.update_feedback(
            current_query_hash, command, confirmed, similarity
        )
        
        # 如果请求JSON输出，返回结构化数据
        if json_output:
            import json
            
            result_data = {
                "command": command,
                "source": source,
                "confidence": confidence,
                "similarity": similarity if similarity is not None else 0.0,
                "dangerous": safety_info.get("is_dangerous", False),
                "confirmed": confirmed,
            }
            print(json.dumps(result_data, indent=2, ensure_ascii=False))
            return result_data
        
        return command
    
    def _handle_fallback(
        self,
        prompt: str,
        base_url: Optional[str],
        json_output: bool,
    ) -> Any:
        """Handle fallback to basic mode on error"""
        if json_output:
            import json
            
            fallback_result = self.get_command_original(prompt, base_url=base_url)
            error_data = {
                "command": fallback_result,
                "source": "FALLBACK",
                "confidence": 0.0,
                "similarity": 0.0,
                "dangerous": False,
                "confirmed": False,
                "warning": "Enhanced features failed, using basic mode",
            }
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
            return error_data
        else:
            print(f"Warning: Enhanced features failed, using basic mode")
            return self.get_command_original(prompt, base_url=base_url)
