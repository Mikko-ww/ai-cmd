"""
跨平台用户输入超时处理模块
替代Unix专用的signal.alarm，提供Windows兼容的超时机制
"""

import sys
import threading
from typing import Optional, Callable, Any


class InputTimeoutError(Exception):
    """输入超时异常"""
    pass


class CrossPlatformInput:
    """跨平台的带超时用户输入处理器"""
    
    def __init__(self):
        self.input_result = None
        self.input_exception = None
        self.input_thread = None
        
    def input_with_timeout(self, prompt: str = "", timeout: int = 30) -> str:
        """
        跨平台的带超时输入函数
        
        Args:
            prompt: 输入提示信息
            timeout: 超时时间（秒）
            
        Returns:
            用户输入的字符串
            
        Raises:
            InputTimeoutError: 输入超时
            KeyboardInterrupt: 用户中断（Ctrl+C）
            EOFError: 输入流结束（Ctrl+D）
        """
        self.input_result = None
        self.input_exception = None
        
        def get_input():
            """在单独线程中获取用户输入"""
            try:
                self.input_result = input(prompt)
            except Exception as e:
                self.input_exception = e
        
        # 启动输入线程
        self.input_thread = threading.Thread(target=get_input)
        self.input_thread.daemon = True
        self.input_thread.start()
        
        # 等待输入或超时
        self.input_thread.join(timeout)
        
        if self.input_thread.is_alive():
            # 超时了，但线程仍在运行
            # 注意：我们不能强制终止线程，但可以忽略结果
            raise InputTimeoutError(f"Input timed out after {timeout} seconds")
        
        # 检查是否有异常
        if self.input_exception:
            raise self.input_exception
        
        # 返回结果
        if self.input_result is not None:
            return self.input_result
        else:
            raise InputTimeoutError("Input failed without specific error")


def input_with_timeout(prompt: str = "", timeout: int = 30) -> str:
    """
    便捷函数：带超时的用户输入
    
    Args:
        prompt: 输入提示信息
        timeout: 超时时间（秒）
        
    Returns:
        用户输入的字符串
        
    Raises:
        InputTimeoutError: 输入超时
        KeyboardInterrupt: 用户中断（Ctrl+C）
        EOFError: 输入流结束（Ctrl+D）
    """
    cross_input = CrossPlatformInput()
    return cross_input.input_with_timeout(prompt, timeout)


# 为了向后兼容，如果在Unix系统上，优先使用signal方式
# 这样可以提供更好的用户体验（可以中断正在等待的input）
def get_best_input_method():
    """获取当前平台最佳的输入超时方法"""
    try:
        import signal
        if hasattr(signal, 'SIGALRM') and sys.platform != 'win32':
            return 'signal'
    except ImportError:
        pass
    return 'threading'


class UniversalInputTimeout:
    """通用输入超时处理器，自动选择最佳方法"""
    
    def __init__(self):
        self.method = get_best_input_method()
        
    def input_with_timeout(self, prompt: str = "", timeout: int = 30) -> str:
        """
        通用的带超时输入函数，自动选择最佳实现
        
        Args:
            prompt: 输入提示信息
            timeout: 超时时间（秒）
            
        Returns:
            用户输入的字符串
            
        Raises:
            InputTimeoutError: 输入超时
            KeyboardInterrupt: 用户中断（Ctrl+C）
            EOFError: 输入流结束（Ctrl+D）
        """
        if self.method == 'signal':
            return self._input_with_signal(prompt, timeout)
        else:
            return self._input_with_threading(prompt, timeout)
    
    def _input_with_signal(self, prompt: str, timeout: int) -> str:
        """使用Unix signal的超时输入"""
        import signal
        
        def timeout_handler(signum, frame):
            raise InputTimeoutError(f"Input timed out after {timeout} seconds")
        
        # 设置超时处理器
        original_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            result = input(prompt)
            signal.alarm(0)  # 取消超时
            signal.signal(signal.SIGALRM, original_handler)  # 恢复原处理器
            return result
        except InputTimeoutError:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)
            raise
        except (KeyboardInterrupt, EOFError):
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)
            raise
        except Exception as e:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)
            raise
    
    def _input_with_threading(self, prompt: str, timeout: int) -> str:
        """使用线程的超时输入"""
        cross_input = CrossPlatformInput()
        return cross_input.input_with_timeout(prompt, timeout)


# 创建全局实例
universal_input = UniversalInputTimeout()