"""
增强的日志模块
使用标准Python logging库，支持文件轮转、彩色输出和可配置日志级别
"""

import sys
import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI颜色码
    COLORS = {
        'DEBUG': '\033[96m',    # 青色
        'INFO': '\033[94m',     # 蓝色
        'WARNING': '\033[93m',  # 黄色
        'ERROR': '\033[91m',    # 红色
        'CRITICAL': '\033[95m', # 紫色
        'RESET': '\033[0m'      # 重置
    }
    
    def __init__(self, use_color: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_color = use_color and self._supports_color()
    
    def _supports_color(self) -> bool:
        """检查终端是否支持颜色"""
        return (
            hasattr(sys.stdout, "isatty")
            and sys.stdout.isatty()
            and os.environ.get("TERM", "").lower() != "dumb"
            and os.name != 'nt'  # Windows Terminal 支持有限
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        if self.use_color and record.levelname in self.COLORS:
            # 添加颜色
            levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            # 临时替换levelname用于格式化
            original_levelname = record.levelname
            record.levelname = levelname
            formatted = super().format(record)
            # 恢复原始levelname
            record.levelname = original_levelname
            return formatted
        else:
            return super().format(record)


class AICommandLogger:
    """AI Command工具的增强日志管理器"""
    
    def __init__(
        self, 
        name: str = "aicmd", 
        log_dir: Optional[str] = None,
        use_color: bool = True,
        console_level: str = "INFO",
        file_level: str = "DEBUG"
    ):
        """
        初始化日志管理器
        
        Args:
            name: 日志器名称
            log_dir: 日志目录路径，None表示使用默认路径
            use_color: 是否在控制台使用颜色
            console_level: 控制台日志级别
            file_level: 文件日志级别
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # 设置为最低级别，由handler控制
        
        # 清除现有handlers
        self.logger.handlers.clear()
        
        # 设置日志目录
        if log_dir is None:
            log_dir = os.path.expanduser("~/.ai-cmd/logs")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 添加控制台处理器
        self._setup_console_handler(use_color, console_level)
        
        # 添加文件处理器
        self._setup_file_handler(file_level)
        
        # 防止重复日志
        self.logger.propagate = False
    
    def _setup_console_handler(self, use_color: bool, level: str):
        """设置控制台日志处理器"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # 简化的控制台格式（用户友好）
        console_formatter = ColoredFormatter(
            use_color=use_color,
            fmt='%(message)s'  # 只显示消息内容
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def _setup_file_handler(self, level: str):
        """设置文件日志处理器（支持轮转）"""
        log_file = self.log_dir / "aicmd.log"
        
        # 使用RotatingFileHandler支持文件轮转
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,         # 保留3个备份
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        
        # 详细的文件格式（调试友好）
        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
    
    def info(self, msg: str):
        """信息日志"""
        self.logger.info(msg)
    
    def success(self, msg: str):
        """成功日志（以INFO级别记录）"""
        self.logger.info(f"✓ {msg}")
    
    def warning(self, msg: str):
        """警告日志"""
        self.logger.warning(msg)
    
    def error(self, msg: str):
        """错误日志"""
        self.logger.error(msg)
    
    def debug(self, msg: str):
        """调试日志"""
        self.logger.debug(msg)
    
    def critical(self, msg: str):
        """严重错误日志"""
        self.logger.critical(msg)
    
    def print(self, msg: str):
        """普通打印（不经过日志系统）"""
        print(msg)
    
    def get_log_info(self) -> Dict[str, Any]:
        """获取日志配置信息"""
        return {
            "log_dir": str(self.log_dir),
            "log_file": str(self.log_dir / "aicmd.log"),
            "handlers": len(self.logger.handlers),
            "level": self.logger.level,
            "exists": (self.log_dir / "aicmd.log").exists(),
        }
    
    def set_level(self, console_level: Optional[str] = None, file_level: Optional[str] = None):
        """动态设置日志级别"""
        if console_level and self.logger.handlers:
            # 假设第一个handler是控制台handler
            console_handler = self.logger.handlers[0]
            console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
        
        if file_level and len(self.logger.handlers) > 1:
            # 假设第二个handler是文件handler
            file_handler = self.logger.handlers[1]
            file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))


# 为了保持向后兼容，创建一个兼容的Logger类
class Logger:
    """向后兼容的Logger类，内部使用AICommandLogger"""
    
    def __init__(self, use_color: bool = True):
        self._enhanced_logger = AICommandLogger(use_color=use_color)
    
    def info(self, msg: str):
        self._enhanced_logger.info(msg)
    
    def success(self, msg: str):
        self._enhanced_logger.success(msg)
    
    def warning(self, msg: str):
        self._enhanced_logger.warning(msg)
    
    def error(self, msg: str):
        self._enhanced_logger.error(msg)
    
    def bold(self, msg: str):
        # bold被映射为info，因为标准logging没有bold级别
        self._enhanced_logger.info(f"**{msg}**")
    
    def print(self, msg: str):
        self._enhanced_logger.print(msg)


# 创建全局logger实例（向后兼容）
logger = Logger()

# 创建增强的logger实例
enhanced_logger = AICommandLogger()