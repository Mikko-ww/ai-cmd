"""
用户交互界面模块
提供友好的用户确认界面，支持Y/N确认、超时处理、异常中断等情况
"""

import sys
import os
from typing import Optional, Tuple, Dict, Any
from enum import Enum
from .config_manager import ConfigManager
from .error_handler import GracefulDegradationManager
from .cross_platform_input import universal_input, InputTimeoutError


class ConfirmationResult(Enum):
    """确认结果枚举"""

    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    ERROR = "error"


class InteractiveManager:
    """交互管理器，处理用户确认和反馈收集"""

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        degradation_manager: Optional[GracefulDegradationManager] = None,
    ):
        """初始化交互管理器"""
        self.config = config_manager or ConfigManager()
        self.degradation_manager = degradation_manager or GracefulDegradationManager()

        # 从配置获取交互参数（与模板对齐，同时兼容旧键名）
        # 读取并强制类型的配置项
        timeout_primary = self.config.get("interaction_timeout_seconds", None)
        timeout_fallback = self.config.get("interaction_timeout", 30)
        default_timeout: int = 30
        for candidate in (timeout_primary, timeout_fallback):
            try:
                if isinstance(candidate, (int, float, str)):
                    default_timeout = int(candidate)
                    break
            except Exception:
                continue
        self.default_timeout = default_timeout
        auto_confirm_raw = self.config.get("auto_confirm_on_timeout", True)
        self.auto_confirm_on_timeout = (
            bool(auto_confirm_raw)
            if isinstance(auto_confirm_raw, (bool, int, str))
            else True
        )
        # 展示项
        self.show_detailed_info = self.config.get("show_detailed_info", True)
        colored_output = self.config.get("colored_output", None)
        if colored_output is None:
            colored_output = self.config.get("use_colors", True)
        self.use_colors = bool(colored_output) and self._supports_color()

        # 交互统计
        self.interaction_stats = {
            "total_prompts": 0,
            "confirmed": 0,
            "rejected": 0,
            "timeouts": 0,
            "cancelled": 0,
            "errors": 0,
        }

    def _supports_color(self) -> bool:
        """检查终端是否支持颜色输出"""
        return (
            hasattr(sys.stdout, "isatty")
            and sys.stdout.isatty()
            and os.environ.get("TERM", "").lower() != "dumb"
        )

    def _colorize(self, text: str, color: str) -> str:
        """为文本添加颜色（如果支持）"""
        if not self.use_colors:
            return text

        colors = {
            "green": "\033[92m",
            "yellow": "\033[93m",
            "red": "\033[91m",
            "blue": "\033[94m",
            "cyan": "\033[96m",
            "bold": "\033[1m",
            "reset": "\033[0m",
        }

        return f"{colors.get(color, '')}{text}{colors.get('reset', '')}"

    def display_info(self, message: str, color: str = "blue") -> None:
        """显示一条普通信息（带颜色）"""
        try:
            print(self._colorize(message, color))
        except Exception:
            print(message)

    def display_metrics(
        self, confidence: Optional[float], similarity: Optional[float]
    ) -> None:
        """在交互流程前优先展示置信度与相似度信息"""
        parts = []
        if confidence is not None:
            conf_color = (
                "green" if confidence >= 0.8 else "yellow" if confidence >= 0.5 else "red"
            )
            parts.append(
                f"Confidence: {self._colorize(f'{confidence*100:.1f}%', conf_color)}"
            )
        if similarity is not None:
            sim_color = (
                "green" if similarity >= 0.8 else "yellow" if similarity >= 0.5 else "red"
            )
            parts.append(
                f"Similarity: {self._colorize(f'{similarity*100:.1f}%', sim_color)}"
            )
        if parts:
            print(" | ".join(parts))

    def prompt_user_confirmation(
        self,
        command: str,
        source: str = "API",
        confidence: Optional[float] = None,
        similarity: Optional[float] = None,
        timeout: Optional[int] = None,
    ) -> Tuple[ConfirmationResult, Dict[str, Any]]:
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
        self.interaction_stats["total_prompts"] += 1
        timeout = timeout or self.default_timeout

        try:
            # 显示命令信息
            self._display_command_info(command, source, confidence, similarity)

            # 获取用户输入
            result = self._get_user_input(timeout)

            # 更新统计
            self.interaction_stats[result.value] = (
                self.interaction_stats.get(result.value, 0) + 1
            )

            # 返回结果和详细信息
            details = {
                "command": command,
                "source": source,
                "confidence": confidence,
                "similarity": similarity,
                "timeout_used": timeout,
                "result": result.value,
            }

            return result, details

        except Exception as e:
            self.degradation_manager.logger.error(f"Error in user confirmation: {e}")
            self.interaction_stats["errors"] += 1

            return ConfirmationResult.ERROR, {
                "command": command,
                "source": source,
                "error": str(e),
            }

    def _display_command_info(
        self,
        command: str,
        source: str,
        confidence: Optional[float] = None,
        similarity: Optional[float] = None,
    ):
        """显示命令和相关信息"""
        print()  # 空行分隔

        # 显示命令
        command_display = self._colorize(command, "bold")
        source_display = self._colorize(f"[{source}]", "cyan")
        print(f"> {command_display}  {source_display}")

        # 显示详细信息（如果启用且有数据）
        if self.show_detailed_info and (
            confidence is not None or similarity is not None
        ):
            info_parts = []

            if confidence is not None:
                conf_color = (
                    "green"
                    if confidence >= 0.8
                    else "yellow" if confidence >= 0.5 else "red"
                )
                conf_display = self._colorize(f"{confidence:.1%}", conf_color)
                info_parts.append(f"Confidence: {conf_display}")

            if similarity is not None:
                sim_color = (
                    "green"
                    if similarity >= 0.8
                    else "yellow" if similarity >= 0.5 else "red"
                )
                sim_display = self._colorize(f"{similarity:.1%}", sim_color)
                info_parts.append(f"Similarity: {sim_display}")

            if info_parts:
                info_text = "  " + " | ".join(info_parts)
                print(info_text)

    def _get_user_input(self, timeout: int) -> ConfirmationResult:
        """获取用户输入，处理超时和异常（跨平台支持）"""

        try:
            # 获取用户输入（跨平台超时）
            prompt = self._colorize("Copy to clipboard? [Y/n]: ", "blue")
            response = universal_input.input_with_timeout(prompt, timeout).strip().lower()
            
            # 解析响应
            return self._parse_response(response)

        except (KeyboardInterrupt, EOFError):
            # Ctrl+C 或 Ctrl+D
            print(self._colorize("\n✗ Cancelled", "red"))
            return ConfirmationResult.CANCELLED

        except InputTimeoutError:
            # 超时处理
            if self.auto_confirm_on_timeout:
                print(
                    self._colorize(
                        f"\n⏰ Timeout ({timeout}s), auto-confirming", "yellow"
                    )
                )
                return ConfirmationResult.TIMEOUT
            else:
                print(self._colorize(f"\n⏰ Timeout ({timeout}s), cancelled", "yellow"))
                return ConfirmationResult.CANCELLED

        except Exception as e:
            # 其他异常
            print(self._colorize(f"\n❌ Input error: {e}", "red"))
            self.degradation_manager.logger.warning(f"Input error: {e}")
            return ConfirmationResult.ERROR

    def _parse_response(self, response: str) -> ConfirmationResult:
        """解析用户响应"""
        # 确认的响应
        yes_responses = ["", "y", "yes", "ok", "sure", "是", "好", "确认", "1", "true"]
        # 拒绝的响应
        no_responses = ["n", "no", "nope", "cancel", "否", "不", "取消", "0", "false"]

        if response in yes_responses:
            return ConfirmationResult.CONFIRMED
        elif response in no_responses:
            return ConfirmationResult.REJECTED
        else:
            # 未识别的响应，默认为确认
            print(
                self._colorize(
                    f'  Unrecognized response "{response}", treating as Yes', "yellow"
                )
            )
            return ConfirmationResult.CONFIRMED

    def display_success_message(self, command: str, copied: bool = True):
        """显示成功消息"""
        if copied:
            message = self._colorize("✓ Copied to clipboard!", "green")
        else:
            message = self._colorize("✓ Command ready", "green")

        print(message)

    def display_rejection_message(self, alternative_action: Optional[str] = None):
        """显示拒绝消息"""
        message = self._colorize("✗ Not copied", "red")
        print(message)

        if alternative_action:
            alt_message = self._colorize(f"  {alternative_action}", "yellow")
            print(alt_message)

    def quick_confirm(
        self, message: str, default: bool = True, timeout: int = 10
    ) -> bool:
        """快速确认对话框，用于简单的是/否问题（跨平台支持）"""
        try:
            default_text = "[Y/n]" if default else "[y/N]"
            prompt = f"{message} {default_text}: "

            try:
                response = universal_input.input_with_timeout(prompt, timeout).strip().lower()

                if not response:
                    return default

                return response in ["y", "yes", "是", "好"]

            except (KeyboardInterrupt, EOFError, InputTimeoutError):
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
        """.format(
            timeout=self.default_timeout
        )

        print(self._colorize(help_text, "cyan"))

    def get_interaction_stats(self) -> Dict[str, Any]:
        """获取交互统计信息"""
        total = int(self.interaction_stats.get("total_prompts", 0))
        if total == 0:
            return {"message": "No interactions yet"}

        status_dict: Dict[str, Any] = dict(self.interaction_stats)

        # 计算百分比
        for key in ["confirmed", "rejected", "timeouts", "cancelled", "errors"]:
            count = int(status_dict.get(key, 0))
            percentage = round((count / total) * 100.0, 1)
            status_dict[f"{key}_percentage"] = float(percentage)

        return status_dict

    def reset_stats(self):
        """重置交互统计"""
        for key in self.interaction_stats:
            self.interaction_stats[key] = 0

    def is_interactive_mode_enabled(self) -> bool:
        """检查是否启用交互模式"""
        return bool(self.config.get("interactive_mode", False) or False)

    def should_prompt_for_confirmation(self, confidence: float) -> bool:
        """根据置信度判断是否需要用户确认"""
        try:
            confidence_threshold = float(self.config.get("confidence_threshold", 0.8) or 0.8)
        except Exception:
            confidence_threshold = 0.8
        try:
            auto_copy_threshold = float(self.config.get("auto_copy_threshold", 0.9) or 0.9)
        except Exception:
            auto_copy_threshold = 0.9
        try:
            manual_confirmation_threshold = float(self.config.get("manual_confirmation_threshold", 0.8) or 0.8)
        except Exception:
            manual_confirmation_threshold = 0.8

        # 置信度很高，不需要确认
        if confidence >= auto_copy_threshold:
            return False

        # 置信度高于手动确认阈值，需要确认
        if confidence >= manual_confirmation_threshold:
            return True

        # 置信度中等，需要确认
        if confidence >= confidence_threshold:
            return True

        # 置信度较低，需要确认
        return True


def create_simple_prompt_function(config_manager: Optional[ConfigManager] = None):
    """创建简化的提示函数，用于向后兼容"""
    manager = InteractiveManager(config_manager)

    def prompt_user_confirmation(
        command: str, source: str = "API", timeout: int = 30
    ) -> bool:
        """简化的用户确认函数"""
        result, details = manager.prompt_user_confirmation(
            command, source, timeout=timeout
        )

        # 将结果转换为布尔值
        return result in [ConfirmationResult.CONFIRMED, ConfirmationResult.TIMEOUT]

    return prompt_user_confirmation
