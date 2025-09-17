"""
配置管理器模块
负责读取和管理所有缓存相关配置项
支持环境变量和JSON配置文件的多层配置源
"""

from importlib import resources
import os
import json
from pathlib import Path
from .logger import logger


class ConfigManager:
    """配置管理器，负责读取和管理所有缓存相关配置项"""

    def __init__(self):
        """初始化配置管理器，支持多层配置源"""
        # 默认配置
        self.default_config = {
            # 基本配置
            "interactive_mode": False,
            "cache_enabled": True,
            "auto_copy_threshold": 0.9,
            "manual_confirmation_threshold": 0.8,
            # API配置
            "api_timeout_seconds": 30,
            "max_retries": 3,
            "default_provider": "",
            # 提供商配置
            "providers": {},
            # 缓存配置
            "cache_directory": "~/.ai-cmd",
            "database_file": "cache.db",
            "max_cache_age_days": 30,
            "cache_size_limit": 1000,
            # 交互配置
            "interaction_timeout_seconds": 30,
            "positive_weight": 0.2,
            "negative_weight": 0.6,
            "similarity_threshold": 0.7,
            "confidence_threshold": 0.8,
            # 显示配置
            "show_confidence": False,
            "show_source": False,
            "colored_output": True,
            # 哈希策略配置
            "hash_strategy": "simple",  # simple | normalized
            # 兼容性配置（旧版本）
            "cache_dir": None,
        }

        # 预加载默认 JSON 结构，用于键路径解析与类型推断
        self.default_json_structure = self._get_default_json_config()
        self._simple_key_paths = self._build_simple_key_paths(self.default_json_structure)

        # 加载配置
        self.config = self._load_configuration()

    def _load_configuration(self):
        """加载配置，按优先级合并：环境变量 > JSON文件 > 默认配置"""
        config = self.default_config.copy()

        # 1. 加载JSON配置文件
        json_config = self._load_json_config()
        if json_config:
            config.update(self._flatten_json_config(json_config))

        # 2. 加载环境变量配置（最高优先级）
        env_config = self._load_env_config()
        config.update(env_config)

        return config

    def _get_config_file_path(self):
        """获取配置文件路径"""
        # 优先查找用户配置
        user_config = Path.home() / ".ai-cmd" / "settings.json"
        if user_config.exists():
            return user_config

        # 查找项目配置
        project_config = Path.cwd() / ".ai-cmd.json"
        if project_config.exists():
            return project_config

        return None

    def _load_json_config(self):
        """加载JSON配置文件"""
        config_path = self._get_config_file_path()
        if not config_path:
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                json_config = json.load(f)
            return json_config
        except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
            print(f"Warning: Failed to load config file {config_path}: {e}")
            return {}

    def _flatten_json_config(self, json_config):
        """将嵌套的JSON配置扁平化为ConfigManager格式"""
        flattened = {}

        # 映射JSON结构到配置键
        if "basic" in json_config:
            basic = json_config["basic"]
            flattened.update(
                {
                    "interactive_mode": basic.get("interactive_mode"),
                    "cache_enabled": basic.get("cache_enabled"),
                    "auto_copy_threshold": basic.get("auto_copy_threshold"),
                    "manual_confirmation_threshold": basic.get(
                        "manual_confirmation_threshold"
                    ),
                }
            )

        if "api" in json_config:
            api = json_config["api"]
            flattened.update(
                {
                    "use_backup_model": api.get("use_backup_model", False),
                    "api_timeout_seconds": api.get("timeout_seconds"),
                    "max_retries": api.get("max_retries"),
                    "default_provider": api.get("default_provider", ""),
                }
            )

        if "providers" in json_config:
            providers = json_config["providers"]
            flattened["providers"] = providers

        if "cache" in json_config:
            cache = json_config["cache"]
            flattened.update(
                {
                    "cache_directory": cache.get("cache_directory"),
                    "database_file": cache.get("database_file"),
                    "max_cache_age_days": cache.get("max_cache_age_days"),
                    "cache_size_limit": cache.get("cache_size_limit"),
                }
            )

        if "interaction" in json_config:
            interaction = json_config["interaction"]
            flattened.update(
                {
                    "interaction_timeout_seconds": interaction.get(
                        "interaction_timeout_seconds"
                    ),
                    "positive_weight": interaction.get("positive_weight"),
                    "negative_weight": interaction.get("negative_weight"),
                    "similarity_threshold": interaction.get("similarity_threshold"),
                    "confidence_threshold": interaction.get("confidence_threshold"),
                }
            )

        if "display" in json_config:
            display = json_config["display"]
            flattened.update(
                {
                    "show_confidence": display.get("show_confidence"),
                    "show_source": display.get("show_source"),
                    "colored_output": display.get("colored_output"),
                }
            )

        # 过滤None值
        flattened_filtered = {k: v for k, v in flattened.items() if v is not None}

        # 处理顶级配置项
        for key in ["hash_strategy"]:
            if key in json_config:
                flattened_filtered[key] = json_config[key]

        return flattened_filtered

    def _load_env_config(self):
        """从环境变量加载配置（保持向后兼容性）"""
        env_config = {}

        # 映射环境变量到配置键
        env_mappings = {
            "AI_CMD_INTERACTIVE_MODE": ("interactive_mode", self._get_bool),
            "AI_CMD_CONFIDENCE_THRESHOLD": ("confidence_threshold", self._get_float),
            "AI_CMD_AUTO_COPY_THRESHOLD": ("auto_copy_threshold", self._get_float),
            "AI_CMD_POSITIVE_WEIGHT": ("positive_weight", self._get_float),
            "AI_CMD_NEGATIVE_WEIGHT": ("negative_weight", self._get_float),
            "AI_CMD_SIMILARITY_THRESHOLD": ("similarity_threshold", self._get_float),
            "AI_CMD_CACHE_ENABLED": ("cache_enabled", self._get_bool),
            "AI_CMD_CACHE_SIZE_LIMIT": ("cache_size_limit", self._get_int),
            "AI_CMD_CACHE_DIR": ("cache_dir", self._get_string),
            "AI_CMD_DEFAULT_PROVIDER": ("default_provider", self._get_string),
        }

        for env_key, (config_key, converter) in env_mappings.items():
            value = converter(env_key, None)
            if value is not None:
                env_config[config_key] = value

        return env_config

    def get(self, key, default=None):
        """获取配置项的值"""
        return self.config.get(key, default)

    def set(self, key, value):
        """设置配置项的值（运行时）"""
        self.config[key] = value

    def get_config_source(self, key):
        """获取配置项的来源"""
        env_mappings = {
            "interactive_mode": "AI_CMD_INTERACTIVE_MODE",
            "confidence_threshold": "AI_CMD_CONFIDENCE_THRESHOLD",
            "auto_copy_threshold": "AI_CMD_AUTO_COPY_THRESHOLD",
            "cache_enabled": "AI_CMD_CACHE_ENABLED",
            "default_provider": "AI_CMD_DEFAULT_PROVIDER",
        }

        # 检查环境变量
        env_key = env_mappings.get(key)
        if env_key and os.getenv(env_key):
            return "Environment Variable"

        # 检查JSON配置文件
        config_path = self._get_config_file_path()
        if config_path:
            return f"JSON Config ({config_path})"

        return "Default"

    def create_user_config(self, config_data=None, is_force=False):
        config_dir = Path.home() / ".ai-cmd"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "settings.json"
        if not is_force and config_file.exists():
            print(f"Config file already exists: {config_file}")
            print("Use --create-config-force to overwrite the existing file.")
            return config_file

        if config_data is None:
            try:
                # 读取包内资源
                with (
                    resources.files("aicmd")
                    .joinpath("setting_template.json")
                    .open("r", encoding="utf-8") as f
                ):
                    config_data = json.load(f)
            except Exception:
                config_data = self._get_default_json_config()

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            print(f"✓ User configuration file created: {config_file}")
            print("You can now edit this file to customize your settings.")
            print("Run 'aicmd --show-config' to see the current configuration.")
            return config_file
        except Exception as e:
            print(f"Error creating config file: {e}")
            return None

    def _get_default_json_config(self):
        """获取默认JSON配置结构"""
        return {
            "version": "0.4.1",
            "description": "AI Command Line Tool Configuration",
            "basic": {
                "interactive_mode": False,
                "cache_enabled": True,
                "auto_copy_threshold": 0.9,
                "manual_confirmation_threshold": 0.8,
            },
            "api": {
                "timeout_seconds": 30, 
                "max_retries": 3, 
                "use_backup_model": False,
                "default_provider": ""
            },
            "providers": {
                "openrouter": {
                    "api_key": "",
                    "model": "",
                    "base_url": "https://openrouter.ai/api/v1/chat/completions"
                },
                "openai": {
                    "api_key": "",
                    "model": "gpt-3.5-turbo",
                    "base_url": "https://api.openai.com/v1/chat/completions"
                },
                "deepseek": {
                    "api_key": "",
                    "model": "deepseek-chat",
                    "base_url": "https://api.deepseek.com/v1/chat/completions"
                },
                "xai": {
                    "api_key": "",
                    "model": "grok-beta",
                    "base_url": "https://api.x.ai/v1/chat/completions"
                },
                "gemini": {
                    "api_key": "",
                    "model": "gemini-pro",
                    "base_url": "https://generativelanguage.googleapis.com/v1beta/models"
                },
                "qwen": {
                    "api_key": "",
                    "model": "qwen-turbo",
                    "base_url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
                }
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

    def _build_simple_key_paths(self, data):
        """为扁平键生成默认 JSON 路径映射，忽略重复键"""
        mapping = {}
        duplicates = set()

        def helper(node, path):
            if not isinstance(node, dict):
                return
            for key, value in node.items():
                new_path = path + (key,)
                if isinstance(value, dict):
                    helper(value, new_path)
                else:
                    existing_path = mapping.get(key)
                    if existing_path and existing_path != new_path:
                        duplicates.add(key)
                    else:
                        mapping[key] = new_path

        helper(data, tuple())
        for key in duplicates:
            mapping.pop(key, None)
        return mapping

    def _get_bool(self, key, default):
        """安全地从环境变量读取布尔值"""
        try:
            value = os.getenv(key, "").lower()
            if value in ("true", "1", "yes", "on"):
                return True
            elif value in ("false", "0", "no", "off"):
                return False
            elif value == "":
                return default
            else:
                print(
                    f"Warning: Invalid boolean value for {key}: '{value}', using default: {default}"
                )
                return default
        except Exception as e:
            print(f"Warning: Error reading {key}: {e}, using default: {default}")
            return default

    def _get_float(self, key, default):
        """安全地从环境变量读取浮点数"""
        try:
            value = os.getenv(key)
            if value is None or value == "":
                return default

            parsed_value = float(value)

            # 对特定配置项进行范围验证
            if key in [
                "AI_CMD_CONFIDENCE_THRESHOLD",
                "AI_CMD_AUTO_COPY_THRESHOLD",
                "AI_CMD_SIMILARITY_THRESHOLD",
            ]:
                if not (0.0 <= parsed_value <= 1.0):
                    print(
                        f"Warning: {key} should be between 0.0 and 1.0, got {parsed_value}, using default: {default}"
                    )
                    return default
            elif key in ["AI_CMD_POSITIVE_WEIGHT", "AI_CMD_NEGATIVE_WEIGHT"]:
                if parsed_value < 0.0:
                    print(
                        f"Warning: {key} should be non-negative, got {parsed_value}, using default: {default}"
                    )
                    return default

            return parsed_value
        except ValueError:
            print(
                f"Warning: Invalid float value for {key}: '{os.getenv(key)}', using default: {default}"
            )
            return default
        except Exception as e:
            print(f"Warning: Error reading {key}: {e}, using default: {default}")
            return default

    def _get_int(self, key, default):
        """安全地从环境变量读取整数"""
        try:
            value = os.getenv(key)
            if value is None or value == "":
                return default

            parsed_value = int(value)

            # 对缓存大小限制进行范围验证
            if key == "AI_CMD_CACHE_SIZE_LIMIT":
                if parsed_value < 0:
                    print(
                        f"Warning: {key} should be non-negative, got {parsed_value}, using default: {default}"
                    )
                    return default
                elif parsed_value > 10000:
                    print(
                        f"Warning: {key} seems too large ({parsed_value}), consider using a smaller value"
                    )

            return parsed_value
        except ValueError:
            print(
                f"Warning: Invalid integer value for {key}: '{os.getenv(key)}', using default: {default}"
            )
            return default
        except Exception as e:
            print(f"Warning: Error reading {key}: {e}, using default: {default}")
            return default

    def _get_string(self, key, default):
        """安全地从环境变量读取字符串"""
        try:
            value = os.getenv(key)
            return value if value is not None else default
        except Exception as e:
            print(f"Warning: Error reading {key}: {e}, using default: {default}")
            return default

    def validate_config(self):
        """验证配置的合理性和完整性"""
        warnings = []
        errors = []

        # 检查阈值的合理性
        confidence_threshold = self.get("confidence_threshold")
        auto_copy_threshold = self.get("auto_copy_threshold")
        manual_confirmation_threshold = self.get("manual_confirmation_threshold")

        if confidence_threshold is not None and auto_copy_threshold is not None:
            if auto_copy_threshold <= confidence_threshold:
                warnings.append(
                    f"auto_copy_threshold ({auto_copy_threshold}) should be higher than confidence_threshold ({confidence_threshold})"
                )

        if (
            manual_confirmation_threshold is not None
            and auto_copy_threshold is not None
        ):
            if manual_confirmation_threshold >= auto_copy_threshold:
                warnings.append(
                    f"manual_confirmation_threshold ({manual_confirmation_threshold}) should be lower than auto_copy_threshold ({auto_copy_threshold})"
                )

        # 检查权重的合理性
        positive_weight = self.get("positive_weight")
        negative_weight = self.get("negative_weight")

        if positive_weight is not None and negative_weight is not None:
            if positive_weight >= negative_weight:
                warnings.append(
                    f"negative_weight ({negative_weight}) should typically be higher than positive_weight ({positive_weight}) for better learning"
                )

        # 检查数值范围
        range_checks = [
            ("confidence_threshold", 0.0, 1.0),
            ("auto_copy_threshold", 0.0, 1.0),
            ("manual_confirmation_threshold", 0.0, 1.0),
            ("similarity_threshold", 0.0, 1.0),
            ("positive_weight", 0.0, 1.0),
            ("negative_weight", 0.0, 1.0),
        ]

        for key, min_val, max_val in range_checks:
            value = self.get(key)
            if value is not None and not (min_val <= value <= max_val):
                errors.append(
                    f"{key} ({value}) must be between {min_val} and {max_val}"
                )

        # 检查整数值
        int_checks = [
            ("cache_size_limit", 1, 100000),
            ("max_cache_age_days", 1, 365),
            ("interaction_timeout_seconds", 1, 300),
            ("api_timeout_seconds", 1, 300),
            ("max_retries", 0, 10),
        ]

        for key, min_val, max_val in int_checks:
            value = self.get(key)
            if value is not None:
                if not isinstance(value, int) or not (min_val <= value <= max_val):
                    errors.append(
                        f"{key} ({value}) must be an integer between {min_val} and {max_val}"
                    )

        # 检查目录路径
        cache_directory = self.get("cache_directory")
        if cache_directory:
            try:
                expanded_path = Path(cache_directory).expanduser()
                if not expanded_path.parent.exists():
                    warnings.append(
                        f"Parent directory of cache_directory ({cache_directory}) does not exist"
                    )
            except Exception as e:
                warnings.append(
                    f"Invalid cache_directory path ({cache_directory}): {e}"
                )

        return {"warnings": warnings, "errors": errors}

    def is_config_valid(self):
        """检查配置是否有效（没有错误）"""
        validation_result = self.validate_config()
        return len(validation_result["errors"]) == 0

    def print_config_summary(self):
        """打印当前配置摘要（用于调试）"""
        print("=== Configuration Summary ===")

        # 按类别显示配置
        categories = {
            "Basic Configuration": [
                "interactive_mode",
                "cache_enabled",
                "auto_copy_threshold",
                "manual_confirmation_threshold",
            ],
            "API Configuration": ["api_timeout_seconds", "max_retries", "default_provider"],
            "Cache Configuration": [
                "cache_directory",
                "database_file",
                "max_cache_age_days",
                "cache_size_limit",
            ],
            "Interaction Configuration": [
                "interaction_timeout_seconds",
                "positive_weight",
                "negative_weight",
                "similarity_threshold",
                "confidence_threshold",
            ],
            "Display Configuration": [
                "show_confidence",
                "show_source",
                "colored_output",
            ],
        }

        for category, keys in categories.items():
            print(f"\n{category}:")
            for key in keys:
                value = self.get(key)
                source = self.get_config_source(key)
                print(f"  {key}: {value} ({source})")

        # 显示提供商配置
        providers = self.get("providers", {})
        if providers:
            print(f"\nProvider Configurations:")
            for provider_name, provider_config in providers.items():
                print(f"  {provider_name}:")
                
                # 检查API密钥，首先从配置，然后从环境变量
                config_api_key = provider_config.get("api_key", "")
                env_api_key_var = f"AI_CMD_{provider_name.upper()}_API_KEY"
                env_api_key = os.getenv(env_api_key_var, "")
                api_key = config_api_key or env_api_key
                
                # 检查模型，首先从配置，然后从环境变量
                config_model = provider_config.get("model", "")
                env_model_var = f"AI_CMD_{provider_name.upper()}_MODEL"
                env_model = os.getenv(env_model_var, "")
                model = config_model or env_model
                
                base_url = provider_config.get("base_url", "")
                
                api_key_source = "Config" if config_api_key else ("Environment" if env_api_key else "Not set")
                model_source = "Config" if config_model else ("Environment" if env_model else "Not set")
                
                print(f"    api_key: {'***' if api_key else 'Not set'} ({api_key_source})")
                print(f"    model: {model or 'Not set'} ({model_source})")
                print(f"    base_url: {base_url or 'Not set'}")

        # 显示配置文件路径
        config_path = self._get_config_file_path()
        print(f"\nConfiguration Sources:")
        print(f"  JSON Config File: {config_path or 'Not found'}")
        print(f"  Environment Variables: Available")
        print(f"  Default Values: Fallback")

        # 显示验证结果
        validation_result = self.validate_config()
        if validation_result["warnings"]:
            print(f"\nConfiguration Warnings:")
            for warning in validation_result["warnings"]:
                print(f"  ⚠ {warning}")

        if validation_result["errors"]:
            print(f"\nConfiguration Errors:")
            for error in validation_result["errors"]:
                print(f"  ✗ {error}")

        if not validation_result["warnings"] and not validation_result["errors"]:
            print(f"\n✓ Configuration is valid with no issues.")

    # 设置配置属性 只有当配置有效时（也就是配置文件存在的时候）
    def _get_nested_value(self, data, key):
        if not data or "." not in key:
            return None
        current = data
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _ensure_path_container(self, data, path_parts):
        current = data
        for part in path_parts[:-1]:
            next_item = current.get(part)
            if next_item is None:
                next_item = {}
                current[part] = next_item
            elif not isinstance(next_item, dict):
                return None
            current = next_item
        return current

    def _path_exists(self, data, path_parts):
        current = data
        for part in path_parts:
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        return True

    def set_config(self, key, value):
        config_path = self._get_config_file_path()
        if not config_path:
            logger.error("No configuration file found. Create one with --create-config first.")
            return False

        json_config = self._load_json_config() or {}
        path_parts = []
        if "." in key:
            path_parts = key.split(".")
        else:
            path_parts = list(self._simple_key_paths.get(key, (key,)))

        if not path_parts:
            logger.error(f"Invalid configuration key: {key}")
            return False

        container = self._ensure_path_container(json_config, path_parts)
        if container is None:
            logger.error(f"Invalid configuration path for key: {key}")
            return False

        container[path_parts[-1]] = value

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(json_config, f, indent=2, ensure_ascii=False)
            print(f"✓ Configuration updated: {key} = {value}")
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False

        self.config.update(self._flatten_json_config(json_config))
        return True

    def is_valid_config_key(self, key: str) -> bool:
        """检查配置键是否有效"""
        if not key:
            return False

        if "." not in key:
            return key in self.default_config

        path_parts = key.split(".")

        current_config = self._load_json_config()
        if current_config and self._path_exists(current_config, path_parts):
            return True

        if self._path_exists(self.default_json_structure, path_parts):
            return True

        # providers.* 允许通过 CLI 扩展新提供商
        if path_parts[0] == "providers" and len(path_parts) >= 2:
            return True

        return False

    def convert_config_value(self, key: str, value: str):
        """根据配置键的类型转换值"""
        try:
            expected_value = None
            expected_type = None

            if "." in key:
                json_config = self._load_json_config() or {}
                expected_value = self._get_nested_value(json_config, key)
                if expected_value is None:
                    expected_value = self._get_nested_value(self.default_json_structure, key)
            else:
                expected_value = self.default_config.get(key)

            if expected_value is not None:
                expected_type = type(expected_value)
            elif key.startswith("providers."):
                expected_type = str
            else:
                expected_type = None

            if expected_type is bool:
                return value.lower() in ("true", "1", "yes", "on")
            if expected_type is int:
                return int(value)
            if expected_type is float:
                return float(value)
            if expected_type is str or expected_type is None:
                return value

            return None

        except (ValueError, TypeError, KeyError):
            return None
