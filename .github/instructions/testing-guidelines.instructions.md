---
applyTo: "tests/**/*.py"
---

# 测试编写规范

## 框架与运行
- 框架：`pytest`，运行命令：`uv run python -m pytest`
- 测试文件命名：`tests/test_<模块名>.py`，镜像 `src/aicmd/` 结构
- 测试类命名：`Test<ClassName>`，方法命名：`test_<行为描述>`

## Keyring 隔离（强制）
测试环境必须使用隔离的 keyring 服务名，避免污染生产数据：
```python
# conftest.py 已配置，所有测试自动生效
os.environ["AICMD_KEYRING_SERVICE"] = "com.aicmd.ww.test"
```
在 keyring 相关测试中验证隔离：
```python
assert os.environ.get("AICMD_KEYRING_SERVICE") == "com.aicmd.ww.test"
```

## 单例重置
`ConfigManager` 使用单例模式，每个测试前后必须重置：
```python
@pytest.fixture(autouse=True)
def reset_config_manager_singleton():
    from aicmd.config_manager import ConfigManager
    ConfigManager.reset_instance()
    yield
    ConfigManager.reset_instance()
```
此 fixture 已在 `conftest.py` 中全局配置。

## 可用 Fixtures
| Fixture | 用途 |
|---------|------|
| `temp_dir` | 临时目录，测试后自动清理 |
| `temp_config_dir` | 模拟 `~/.ai-cmd` 配置目录 |
| `temp_db_path` | 临时数据库文件路径 |
| `sample_config` | 标准测试配置字典 |
| `mock_config_manager` | Mock 的 ConfigManager |
| `mock_database_manager` | Mock 的 DatabaseManager |
| `mock_cache_manager` | Mock 的 CacheManager |

## Mock 模式
```python
from unittest.mock import patch, Mock

@pytest.fixture
def mock_keyring():
    with patch("aicmd.llm_providers.KeyringManager") as mock:
        mock.get_api_key.return_value = "test-api-key-123"
        yield mock

@pytest.fixture
def mock_successful_response():
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "ls -la"}}]
    }
    return mock_resp
```

## 测试脚本位置
临时测试脚本放在项目 `./tmp/` 目录，**禁止** 使用系统 `/tmp/` 目录：
```bash
# 正确 ✓
cat > ./tmp/test_example.sh

# 错误 ✗
cat > /tmp/test_example.sh
```

## 测试标记
- `@pytest.mark.unit` — 单元测试
- `@pytest.mark.integration` — 集成测试
- `@pytest.mark.slow` — 耗时测试
