"""
pytest 配置文件
提供测试 fixtures 和全局配置
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Generator

import pytest

# 确保 src 目录在 Python path 中
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# ============================================================
# 测试环境隔离配置
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    设置测试环境变量，确保测试隔离
    设置 keyring 测试服务名，避免污染生产 keyring 数据
    """
    # 设置测试 keyring 服务
    os.environ["AICMD_KEYRING_SERVICE"] = "com.aicmd.ww.test"
    
    # 禁用颜色输出（测试中不需要）
    os.environ["NO_COLOR"] = "1"
    
    # 设置测试日志级别
    os.environ["AICMD_LOG_LEVEL"] = "DEBUG"
    
    yield
    
    # 清理环境变量
    os.environ.pop("AICMD_KEYRING_SERVICE", None)
    os.environ.pop("NO_COLOR", None)
    os.environ.pop("AICMD_LOG_LEVEL", None)


@pytest.fixture(autouse=True)
def reset_config_manager_singleton():
    """
    在每个测试前重置 ConfigManager 单例
    确保测试之间的配置隔离
    """
    from aicmd.config_manager import ConfigManager
    
    # 在测试前重置单例
    ConfigManager.reset_instance()
    
    yield
    
    # 在测试后也重置，保持清洁
    ConfigManager.reset_instance()


# ============================================================
# 临时目录和文件 fixtures
# ============================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    创建临时目录用于测试
    测试结束后自动清理
    """
    temp_path = Path(tempfile.mkdtemp(prefix="aicmd_test_"))
    yield temp_path
    
    # 清理
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def temp_config_dir(temp_dir: Path) -> Generator[Path, None, None]:
    """
    创建模拟配置目录（~/.ai-cmd）用于测试
    """
    config_dir = temp_dir / ".ai-cmd"
    config_dir.mkdir(parents=True, exist_ok=True)
    yield config_dir


@pytest.fixture
def temp_db_path(temp_config_dir: Path) -> Path:
    """
    生成临时数据库路径用于测试
    """
    return temp_config_dir / "test_cache.db"


# ============================================================
# Mock 配置 fixtures
# ============================================================

@pytest.fixture
def sample_config() -> dict:
    """
    提供示例配置数据
    """
    return {
        "version": "1.0.2",
        "basic": {
            "interactive_mode": False,
            "cache_enabled": True,
            "auto_copy_threshold": 0.9,
            "manual_confirmation_threshold": 0.8,
        },
        "api": {
            "timeout_seconds": 30,
            "max_retries": 3,
            "default_provider": "openrouter",
        },
        "providers": {
            "openrouter": {
                "model": "test-model",
                "base_url": "https://openrouter.ai/api/v1/chat/completions",
            },
        },
        "cache": {
            "cache_directory": "~/.ai-cmd",
            "database_file": "cache.db",
            "max_cache_age_days": 30,
            "cache_size_limit": 1000,
        },
        "interaction": {
            "interaction_timeout_seconds": 30,
            "positive_weight": 0.2,
            "negative_weight": 0.6,
            "similarity_threshold": 0.7,
            "confidence_threshold": 0.8,
        },
        "display": {
            "show_confidence": False,
            "show_source": False,
            "colored_output": True,
        },
    }


@pytest.fixture
def temp_config_file(temp_config_dir: Path, sample_config: dict) -> Path:
    """
    创建临时配置文件
    """
    import json
    
    config_file = temp_config_dir / "settings.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(sample_config, f, indent=2)
    
    return config_file


# ============================================================
# 测试数据 fixtures
# ============================================================

@pytest.fixture
def sample_queries() -> list:
    """
    提供示例查询数据
    """
    return [
        ("list all files in current directory", "ls -la"),
        ("find files containing hello", "grep -r 'hello' ."),
        ("show current directory", "pwd"),
        ("create a new directory named test", "mkdir test"),
        ("delete the file named temp.txt", "rm temp.txt"),
        ("显示当前目录", "pwd"),
        ("查找所有 Python 文件", "find . -name '*.py'"),
    ]


@pytest.fixture
def sample_dangerous_commands() -> list:
    """
    提供危险命令示例
    """
    return [
        "rm -rf /",
        "rm -rf /*",
        "sudo rm -rf /home",
        "dd if=/dev/zero of=/dev/sda",
        "chmod 777 /etc/passwd",
        "shutdown -h now",
        ":(){:|:&};:",  # fork bomb
    ]


@pytest.fixture
def sample_safe_commands() -> list:
    """
    提供安全命令示例
    """
    return [
        "ls -la",
        "pwd",
        "echo 'hello world'",
        "cat README.md",
        "git status",
        "python --version",
    ]


# ============================================================
# Mock 对象 fixtures
# ============================================================

@pytest.fixture
def mock_config_manager(temp_config_dir: Path, sample_config: dict, monkeypatch):
    """
    创建模拟的 ConfigManager
    """
    import json
    from aicmd.config_manager import ConfigManager
    
    # 创建配置文件
    config_file = temp_config_dir / "settings.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(sample_config, f, indent=2)
    
    # 修改 Path.home() 返回临时目录的父目录
    def mock_home():
        return temp_config_dir.parent
    
    monkeypatch.setattr(Path, "home", mock_home)
    
    # 创建 ConfigManager 实例
    config_manager = ConfigManager()
    return config_manager


@pytest.fixture
def mock_database_manager(temp_db_path: Path, mock_config_manager, monkeypatch):
    """
    创建模拟的 SafeDatabaseManager
    """
    from aicmd.database_manager import SafeDatabaseManager
    
    # 修改数据库路径
    def mock_get_database_path(self):
        return str(temp_db_path)
    
    monkeypatch.setattr(
        SafeDatabaseManager,
        "_get_database_path",
        mock_get_database_path
    )
    
    db_manager = SafeDatabaseManager(mock_config_manager)
    return db_manager


@pytest.fixture
def mock_cache_manager(mock_config_manager, mock_database_manager):
    """
    创建模拟的 CacheManager
    """
    from aicmd.cache_manager import CacheManager
    from aicmd.error_handler import GracefulDegradationManager
    
    degradation_manager = GracefulDegradationManager()
    cache_manager = CacheManager(
        config_manager=mock_config_manager,
        degradation_manager=degradation_manager
    )
    cache_manager.db = mock_database_manager
    
    return cache_manager


# ============================================================
# 辅助函数
# ============================================================

def pytest_configure(config):
    """
    pytest 配置钩子
    注册自定义标记
    """
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """
    修改测试项，自动为测试添加标记
    """
    for item in items:
        # 为集成测试添加标记
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
