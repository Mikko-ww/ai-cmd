"""
命令安全检查模块
识别潜在危险的命令并提供安全警告
"""

import re
from typing import List, Dict, Any, Optional
from .config_manager import ConfigManager


class CommandSafetyChecker:
    """命令安全检查器"""
    
    # 默认危险命令模式
    DEFAULT_DANGEROUS_PATTERNS = [
        # 文件系统删除操作
        r'\brm\s+.*-r.*/',  # rm -r or rm -rf with paths
        r'\brm\s+.*-f.*/',  # rm -f with paths  
        r'\brm\s+-[rf]+\s+/',  # rm -rf /
        r'\brm\s+-[rf]+\s+\*',  # rm -rf *
        r'\brmdir\s+.*/',  # rmdir operations on paths
        
        # 系统级危险操作
        r'\bsudo\s+rm\s+.*-[rf]',  # sudo rm operations
        r'\bdd\s+.*of=/dev/',  # dd writing to devices
        r'\bmkfs\.',  # filesystem creation
        r'\bformat\s+[a-zA-Z]:', # Windows format command
        r'\bdel\s+.*\*',  # Windows delete all files
        
        # 网络和系统修改
        r'\bchmod\s+777',  # chmod 777 (overly permissive)
        r'\bchown\s+.*:.*\s+/',  # chown on system paths
        r'\b>\s*/dev/',  # redirecting to devices
        r'\bmv\s+.*\s+/dev/null',  # moving to /dev/null
        
        # 进程和系统控制
        r'\bkill\s+-9\s+1',  # killing init process
        r'\bkillall\s+.*',  # kill all processes
        r'\bshutdown\s+.*',  # system shutdown
        r'\breboot\b',  # system reboot
        r'\bhalt\b',  # system halt
        
        # 包管理危险操作
        r'\bapt\s+.*remove.*--purge.*\*',  # apt remove with wildcards
        r'\byum\s+.*remove.*\*',  # yum remove with wildcards
        r'\bpip\s+.*uninstall.*-y.*\*',  # pip uninstall with wildcards
    ]
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化安全检查器"""
        self.config = config_manager or ConfigManager()
        
        # 从配置获取自定义危险模式
        custom_patterns = self.config.get("dangerous_command_patterns", [])
        
        # 合并默认和自定义模式
        self.dangerous_patterns = self.DEFAULT_DANGEROUS_PATTERNS + custom_patterns
        
        # 编译正则表达式
        self.compiled_patterns = []
        for pattern in self.dangerous_patterns:
            try:
                self.compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                # 忽略无效的正则表达式
                continue
    
    def is_dangerous_command(self, command: str) -> bool:
        """
        检查命令是否危险
        
        Args:
            command: 要检查的命令字符串
            
        Returns:
            True if command is potentially dangerous, False otherwise
        """
        if not command or not command.strip():
            return False
        
        # 检查是否匹配任何危险模式
        for pattern in self.compiled_patterns:
            if pattern.search(command):
                return True
        
        return False
    
    def get_danger_level(self, command: str) -> str:
        """
        获取命令的危险等级
        
        Args:
            command: 要检查的命令字符串
            
        Returns:
            危险等级: "safe", "warning", "dangerous", "critical"
        """
        if not self.is_dangerous_command(command):
            return "safe"
        
        # 关键系统操作
        critical_patterns = [
            r'\brm\s+-[rf]+\s+/',
            r'\bdd\s+.*of=/dev/',
            r'\bformat\s+[a-zA-Z]:',
            r'\bmkfs\.',
            r'\bkill\s+-9\s+1',
            r'\bshutdown\s+.*',
            r'\breboot\b',
            r'\bhalt\b',
        ]
        
        for pattern_str in critical_patterns:
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                if pattern.search(command):
                    return "critical"
            except re.error:
                continue
        
        # 高危操作
        dangerous_patterns = [
            r'\brm\s+.*-[rf]',
            r'\bchmod\s+777',
            r'\bkillall\s+.*',
            r'\bsudo\s+rm\s+.*',
        ]
        
        for pattern_str in dangerous_patterns:
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                if pattern.search(command):
                    return "dangerous"
            except re.error:
                continue
        
        return "warning"
    
    def get_safety_warnings(self, command: str) -> List[str]:
        """
        获取命令的安全警告信息
        
        Args:
            command: 要检查的命令字符串
            
        Returns:
            警告信息列表
        """
        if not self.is_dangerous_command(command):
            return []
        
        warnings = []
        danger_level = self.get_danger_level(command)
        
        if danger_level == "critical":
            warnings.append("⚠️  CRITICAL: This command could cause irreversible system damage!")
            warnings.append("🚨 This command may delete system files or damage your system")
            warnings.append("💡 Please double-check before proceeding")
        elif danger_level == "dangerous":
            warnings.append("⚠️  WARNING: This command could delete files or modify system settings")
            warnings.append("💡 Make sure you understand what this command does")
        elif danger_level == "warning":
            warnings.append("⚠️  CAUTION: This command requires careful consideration")
        
        return warnings
    
    def should_force_confirmation(self, command: str) -> bool:
        """
        检查是否应该强制用户确认
        
        Args:
            command: 要检查的命令字符串
            
        Returns:
            True if confirmation should be forced, False otherwise
        """
        if not self.is_dangerous_command(command):
            return False
        
        # 从配置获取危险命令处理策略
        force_confirm_dangerous = self.config.get("force_confirm_dangerous_commands", True)
        return force_confirm_dangerous
    
    def should_disable_auto_copy(self, command: str) -> bool:
        """
        检查是否应该禁用自动复制
        
        Args:
            command: 要检查的命令字符串
            
        Returns:
            True if auto-copy should be disabled, False otherwise
        """
        if not self.is_dangerous_command(command):
            return False
        
        # 从配置获取自动复制策略
        disable_auto_copy_dangerous = self.config.get("disable_auto_copy_dangerous", True)
        return disable_auto_copy_dangerous
    
    def get_safety_info(self, command: str) -> Dict[str, Any]:
        """
        获取命令的完整安全信息
        
        Args:
            command: 要检查的命令字符串
            
        Returns:
            包含安全信息的字典
        """
        is_dangerous = self.is_dangerous_command(command)
        
        return {
            "is_dangerous": is_dangerous,
            "danger_level": self.get_danger_level(command),
            "warnings": self.get_safety_warnings(command),
            "force_confirmation": self.should_force_confirmation(command),
            "disable_auto_copy": self.should_disable_auto_copy(command),
        }