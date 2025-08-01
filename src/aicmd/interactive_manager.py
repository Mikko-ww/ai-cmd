"""
用户交互界面模块
提供友好的用户确认界面，支持Y/N确认、超时处理、异常中断等情况
"""

import signal
import sys
import os
from typing import Optional, Tuple, Dict, Any
from enum import Enum
from .config_manager import ConfigManager
from .error_handler import GracefulDegradationManager


class ConfirmationResult(Enum):
    """确认结果枚举"""
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    ERROR = "error"


class InteractiveManager:
    """交互管理器，处理用户确认和反馈收集"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None,
                 degradation_manager: Optional[GracefulDegradationManager] = None):
        """初始化交互管理器"""
        self.config = config_manager or ConfigManager()
        self.degradation_manager = degradation_manager or GracefulDegradationManager()
        
        # 从配置获取交互参数
        self.default_timeout = self.config.get('interaction_timeout', 30)
        self.auto_confirm_on_timeout = self.config.get('auto_confirm_on_timeout', True)
        self.show_detailed_info = self.config.get('show_detailed_info', True)
        self.use_colors = self.config.get('use_colors', True) and self._supports_color()
        
        # 交互统计
        self.interaction_stats = {
            'total_prompts': 0,
            'confirmed': 0,
            'rejected': 0,
            'timeouts': 0,
            'cancelled': 0,
            'errors': 0
        }
    
    def _supports_color(self) -> bool:
        """检查终端是否支持颜色输出"""
        return (
            hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
            os.environ.get('TERM', '').lower() != 'dumb'
        )
    
    def _colorize(self, text: str, color: str) -> str:
        """为文本添加颜色（如果支持）"""
        if not self.use_colors:
            return text
        
        colors = {
            'green': '\033[92m',
            'yellow': '\033[93m',
            'red': '\033[91m',
            'blue': '\033[94m',
            'cyan': '\033[96m',
            'bold': '\033[1m',
            'reset': '\033[0m'
        }
        
        return f"{colors.get(color, '')}{text}{colors.get('reset', '')}"
    
    def prompt_user_confirmation(self, command: str, source: str = 'API', 
                                confidence: Optional[float] = None,
                                similarity: Optional[float] = None,
                                timeout: Optional[int] = None) -> Tuple[ConfirmationResult, Dict[str, Any]]:
        """
        提示用户确认命令
        
        Args:
            command: 要执行的命令
            source: 命令来源（API、Cache等）
            confidence: 置信度分数（可选）
            similarity: 相似度分数（可选）
            timeout: 超时时间（秒），None使用默认值
            
        Returns:
            (确认结果, 详细信息字典)
        """
        self.interaction_stats['total_prompts'] += 1
        timeout = timeout or self.default_timeout
        
        try:
            # 显示命令信息
            self._display_command_info(command, source, confidence, similarity)
            
            # 获取用户输入
            result = self._get_user_input(timeout)
            
            # 更新统计
            self.interaction_stats[result.value] = self.interaction_stats.get(result.value, 0) + 1
            
            # 返回结果和详细信息
            details = {
                'command': command,
                'source': source,
                'confidence': confidence,
                'similarity': similarity,
                'timeout_used': timeout,
                'result': result.value
            }
            
            return result, details
            
        except Exception as e:
            self.degradation_manager.logger.error(f"Error in user confirmation: {e}")
            self.interaction_stats['errors'] += 1
            
            return ConfirmationResult.ERROR, {
                'command': command,
                'source': source,
                'error': str(e)
            }
    
    def _display_command_info(self, command: str, source: str, 
                            confidence: Optional[float] = None,
                            similarity: Optional[float] = None):
        """显示命令和相关信息"""
        print()  # 空行分隔
        
        # 显示命令
        command_display = self._colorize(command, 'bold')
        source_display = self._colorize(f'[{source}]', 'cyan')
        print(f'> {command_display}  {source_display}')
        
        # 显示详细信息（如果启用且有数据）
        if self.show_detailed_info and (confidence is not None or similarity is not None):
            info_parts = []
            
            if confidence is not None:
                conf_color = 'green' if confidence >= 0.8 else 'yellow' if confidence >= 0.5 else 'red'
                conf_display = self._colorize(f'{confidence:.1%}', conf_color)
                info_parts.append(f'Confidence: {conf_display}')
            
            if similarity is not None:
                sim_color = 'green' if similarity >= 0.8 else 'yellow' if similarity >= 0.5 else 'red'
                sim_display = self._colorize(f'{similarity:.1%}', sim_color)
                info_parts.append(f'Similarity: {sim_display}')
            
            if info_parts:
                info_text = '  ' + ' | '.join(info_parts)
                print(info_text)
    
    def _get_user_input(self, timeout: int) -> ConfirmationResult:
        """获取用户输入，处理超时和异常"""
        
        def timeout_handler(signum, frame):
            raise TimeoutError("User input timeout")
        
        # 设置超时处理（仅在Unix系统上）
        if hasattr(signal, 'SIGALRM'):
            original_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
        
        try:
            # 获取用户输入
            prompt = self._colorize('Copy to clipboard? [Y/n]: ', 'blue')
            response = input(prompt).strip().lower()
            
            # 取消超时
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)
            
            # 解析响应
            return self._parse_response(response)
            
        except (KeyboardInterrupt, EOFError):
            # Ctrl+C 或 Ctrl+D
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)
            
            print(self._colorize('\n✗ Cancelled', 'red'))
            return ConfirmationResult.CANCELLED
            
        except TimeoutError:
            # 超时处理
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)
            
            if self.auto_confirm_on_timeout:
                print(self._colorize(f'\n⏰ Timeout ({timeout}s), auto-confirming', 'yellow'))
                return ConfirmationResult.TIMEOUT
            else:
                print(self._colorize(f'\n⏰ Timeout ({timeout}s), cancelled', 'yellow'))
                return ConfirmationResult.CANCELLED
                
        except Exception as e:
            # 其他异常
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, original_handler)
            
            print(self._colorize(f'\n❌ Input error: {e}', 'red'))
            self.degradation_manager.logger.warning(f"Input error: {e}")
            return ConfirmationResult.ERROR
    
    def _parse_response(self, response: str) -> ConfirmationResult:
        """解析用户响应"""
        # 确认的响应
        yes_responses = ['', 'y', 'yes', 'ok', 'sure', '是', '好', '确认', '1', 'true']
        # 拒绝的响应
        no_responses = ['n', 'no', 'nope', 'cancel', '否', '不', '取消', '0', 'false']
        
        if response in yes_responses:
            return ConfirmationResult.CONFIRMED
        elif response in no_responses:
            return ConfirmationResult.REJECTED
        else:
            # 未识别的响应，默认为确认
            print(self._colorize(f'  Unrecognized response "{response}", treating as Yes', 'yellow'))
            return ConfirmationResult.CONFIRMED
    
    def display_success_message(self, command: str, copied: bool = True):
        """显示成功消息"""
        if copied:
            message = self._colorize('✓ Copied to clipboard!', 'green')
        else:
            message = self._colorize('✓ Command ready', 'green')
        
        print(message)
    
    def display_rejection_message(self, alternative_action: Optional[str] = None):
        """显示拒绝消息"""
        message = self._colorize('✗ Not copied', 'red')
        print(message)
        
        if alternative_action:
            alt_message = self._colorize(f'  {alternative_action}', 'yellow')
            print(alt_message)
    
    def quick_confirm(self, message: str, default: bool = True, timeout: int = 10) -> bool:
        """快速确认对话框，用于简单的是/否问题"""
        try:
            default_text = "[Y/n]" if default else "[y/N]"
            prompt = f"{message} {default_text}: "
            
            def timeout_handler(signum, frame):
                raise TimeoutError()
            
            if hasattr(signal, 'SIGALRM'):
                original_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)
            
            try:
                response = input(prompt).strip().lower()
                
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, original_handler)
                
                if not response:
                    return default
                
                return response in ['y', 'yes', '是', '好']
                
            except (KeyboardInterrupt, EOFError, TimeoutError):
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, original_handler)
                return default
                
        except Exception as e:
            self.degradation_manager.logger.warning(f"Quick confirm error: {e}")
            return default
    
    def show_help(self):
        """显示交互帮助信息"""
        help_text = """
Interactive Mode Help:
  Y/yes/是/好    - Confirm and copy to clipboard
  N/no/否/不     - Reject, don't copy
  Ctrl+C        - Cancel operation
  <Enter>       - Default to Yes
  <Timeout>     - Auto-confirm after {timeout}s
        """.format(timeout=self.default_timeout)
        
        print(self._colorize(help_text, 'cyan'))
    
    def get_interaction_stats(self) -> Dict[str, Any]:
        """获取交互统计信息"""
        total = self.interaction_stats['total_prompts']
        if total == 0:
            return {'message': 'No interactions yet'}
        
        stats = self.interaction_stats.copy()
        
        # 计算百分比
        for key in ['confirmed', 'rejected', 'timeouts', 'cancelled', 'errors']:
            count = stats[key]
            stats[f'{key}_percentage'] = round((count / total) * 100, 1) if total > 0 else 0
        
        return stats
    
    def reset_stats(self):
        """重置交互统计"""
        for key in self.interaction_stats:
            self.interaction_stats[key] = 0
    
    def is_interactive_mode_enabled(self) -> bool:
        """检查是否启用交互模式"""
        return self.config.get('interactive_mode', False)
    
    def should_prompt_for_confirmation(self, confidence: float) -> bool:
        """根据置信度判断是否需要用户确认"""
        confidence_threshold = self.config.get('confidence_threshold', 0.8)
        auto_copy_threshold = self.config.get('auto_copy_threshold', 0.9)
        
        # 置信度很高，不需要确认
        if confidence >= auto_copy_threshold:
            return False
        
        # 置信度中等，需要确认
        if confidence >= confidence_threshold:
            return True
        
        # 置信度较低，需要确认
        return True


def create_simple_prompt_function(config_manager: Optional[ConfigManager] = None):
    """创建简化的提示函数，用于向后兼容"""
    manager = InteractiveManager(config_manager)
    
    def prompt_user_confirmation(command: str, source: str = 'API', timeout: int = 30) -> bool:
        """简化的用户确认函数"""
        result, details = manager.prompt_user_confirmation(command, source, timeout=timeout)
        
        # 将结果转换为布尔值
        return result in [ConfirmationResult.CONFIRMED, ConfirmationResult.TIMEOUT]
    
    return prompt_user_confirmation
