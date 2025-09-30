# 优化任务快速开始指南

## 推荐的首个任务：TASK-1-001

**任务**: 创建测试目录结构和配置  
**优先级**: P0（最高）  
**工作量**: 0.5天  
**依赖**: 无

这是整个优化工作的基础，建议作为第一个任务实施。

## 实施步骤

### 1. 创建测试目录结构

```bash
# 在项目根目录创建测试结构
mkdir -p tests/integration tests/fixtures

# 创建必要的文件
touch tests/__init__.py
touch tests/conftest.py
touch tests/integration/__init__.py
touch tests/fixtures/__init__.py
touch tests/fixtures/config_fixtures.py
touch tests/fixtures/mock_data.py
```

### 2. 配置测试依赖

在 `pyproject.toml` 中添加测试依赖：

```toml
[dependency-groups]
dev = [
    "black>=25.1.0", 
    "flake8>=7.3.0",
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.11.1",
]
```

安装依赖：
```bash
uv sync
```

### 3. 创建 conftest.py

创建 `tests/conftest.py` 包含全局fixtures：

```python
"""
Pytest configuration and global fixtures
"""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_config():
    """Provide a mock configuration for tests"""
    return {
        "interactive_mode": False,
        "cache_enabled": True,
        "auto_copy_threshold": 0.9,
        "confidence_threshold": 0.8,
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv("AI_CMD_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("AI_CMD_OPENROUTER_MODEL", "test-model")
```

### 4. 创建示例测试

创建 `tests/test_example.py` 验证配置：

```python
"""
Example test to verify test infrastructure
"""
import pytest


def test_basic_assertion():
    """Basic test to verify pytest is working"""
    assert 1 + 1 == 2


def test_temp_dir_fixture(temp_dir):
    """Test that temp_dir fixture works"""
    assert temp_dir.exists()
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")
    assert test_file.read_text() == "test content"


def test_mock_config_fixture(mock_config):
    """Test that mock_config fixture works"""
    assert mock_config["interactive_mode"] is False
    assert mock_config["cache_enabled"] is True
    assert mock_config["auto_copy_threshold"] == 0.9
```

### 5. 配置 pytest

在 `pyproject.toml` 中添加 pytest 配置：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--tb=short",
    "--cov=aicmd",
    "--cov-report=term-missing",
    "--cov-report=html",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow running tests",
]
```

### 6. 验证测试运行

```bash
# 运行所有测试
uv run pytest

# 运行带覆盖率的测试
uv run pytest --cov=aicmd --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html  # macOS/Linux
# 或
start htmlcov/index.html  # Windows
```

### 7. 创建 .gitignore 条目

确保测试生成的文件不被提交：

```gitignore
# 测试相关
.pytest_cache/
.coverage
htmlcov/
*.pyc
__pycache__/
```

## 验收标准

完成后检查：

- [x] `tests/` 目录结构创建完成
- [x] `conftest.py` 包含基本 fixtures
- [x] 至少有一个示例测试通过
- [x] pytest 配置正确
- [x] 可以生成覆盖率报告
- [x] 测试依赖已安装

## 下一步

完成 TASK-1-001 后，可以继续：

- **TASK-1-002**: 配置管理器单元测试
- **TASK-1-003**: 缓存管理器单元测试
- **TASK-1-010**: 添加完整类型注解（可并行）

## 常见问题

### Q: pytest 找不到模块？
A: 确保已运行 `uv pip install -e .` 进行可编辑安装。

### Q: 测试覆盖率为0？
A: 检查 `--cov=aicmd` 路径是否正确，应该指向 `src/aicmd`。

### Q: fixture 不工作？
A: 确保 `conftest.py` 在正确的位置，且 pytest 可以发现它。

## 参考资源

- [pytest 官方文档](https://docs.pytest.org/)
- [pytest-cov 文档](https://pytest-cov.readthedocs.io/)
- [项目的 AGENTS.md](./AGENTS.md) - 测试指南部分

---

*完成这个任务后，整个项目的测试基础设施就建立起来了！*
