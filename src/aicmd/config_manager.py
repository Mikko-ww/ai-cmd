"""
配置管理器模块
负责读取和管理所有缓存相关配置项
"""

import os


class ConfigManager:
    """配置管理器，负责读取和管理所有缓存相关配置项"""
    
    def __init__(self):
        """初始化配置管理器，从环境变量读取配置"""
        self.config = {
            'interactive_mode': self._get_bool('AI_CMD_INTERACTIVE_MODE', False),
            'confidence_threshold': self._get_float('AI_CMD_CONFIDENCE_THRESHOLD', 0.8),
            'auto_copy_threshold': self._get_float('AI_CMD_AUTO_COPY_THRESHOLD', 0.9),
            'positive_weight': self._get_float('AI_CMD_POSITIVE_WEIGHT', 0.2),
            'negative_weight': self._get_float('AI_CMD_NEGATIVE_WEIGHT', 0.5),
            'similarity_threshold': self._get_float('AI_CMD_SIMILARITY_THRESHOLD', 0.7),
            'cache_enabled': self._get_bool('AI_CMD_CACHE_ENABLED', True),
            'cache_size_limit': self._get_int('AI_CMD_CACHE_SIZE_LIMIT', 1000),
            'cache_dir': self._get_string('AI_CMD_CACHE_DIR', None)
        }
    
    def get(self, key, default=None):
        """获取配置项的值"""
        return self.config.get(key, default)
    
    def _get_bool(self, key, default):
        """安全地从环境变量读取布尔值"""
        try:
            value = os.getenv(key, '').lower()
            if value in ('true', '1', 'yes', 'on'):
                return True
            elif value in ('false', '0', 'no', 'off'):
                return False
            elif value == '':
                return default
            else:
                print(f"Warning: Invalid boolean value for {key}: '{value}', using default: {default}")
                return default
        except Exception as e:
            print(f"Warning: Error reading {key}: {e}, using default: {default}")
            return default
    
    def _get_float(self, key, default):
        """安全地从环境变量读取浮点数"""
        try:
            value = os.getenv(key)
            if value is None or value == '':
                return default
            
            parsed_value = float(value)
            
            # 对特定配置项进行范围验证
            if key in ['AI_CMD_CONFIDENCE_THRESHOLD', 'AI_CMD_AUTO_COPY_THRESHOLD', 'AI_CMD_SIMILARITY_THRESHOLD']:
                if not (0.0 <= parsed_value <= 1.0):
                    print(f"Warning: {key} should be between 0.0 and 1.0, got {parsed_value}, using default: {default}")
                    return default
            elif key in ['AI_CMD_POSITIVE_WEIGHT', 'AI_CMD_NEGATIVE_WEIGHT']:
                if parsed_value < 0.0:
                    print(f"Warning: {key} should be non-negative, got {parsed_value}, using default: {default}")
                    return default
            
            return parsed_value
        except ValueError as e:
            print(f"Warning: Invalid float value for {key}: '{os.getenv(key)}', using default: {default}")
            return default
        except Exception as e:
            print(f"Warning: Error reading {key}: {e}, using default: {default}")
            return default
    
    def _get_int(self, key, default):
        """安全地从环境变量读取整数"""
        try:
            value = os.getenv(key)
            if value is None or value == '':
                return default
            
            parsed_value = int(value)
            
            # 对缓存大小限制进行范围验证
            if key == 'AI_CMD_CACHE_SIZE_LIMIT':
                if parsed_value < 0:
                    print(f"Warning: {key} should be non-negative, got {parsed_value}, using default: {default}")
                    return default
                elif parsed_value > 10000:
                    print(f"Warning: {key} seems too large ({parsed_value}), consider using a smaller value")
            
            return parsed_value
        except ValueError as e:
            print(f"Warning: Invalid integer value for {key}: '{os.getenv(key)}', using default: {default}")
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
        """验证配置的合理性"""
        warnings = []
        
        # 检查阈值的合理性
        confidence_threshold = self.get('confidence_threshold')
        auto_copy_threshold = self.get('auto_copy_threshold')
        
        if confidence_threshold is not None and auto_copy_threshold is not None:
            if auto_copy_threshold <= confidence_threshold:
                warnings.append(f"auto_copy_threshold ({auto_copy_threshold}) should be higher than confidence_threshold ({confidence_threshold})")
        
        # 检查权重的合理性
        positive_weight = self.get('positive_weight')
        negative_weight = self.get('negative_weight')
        
        if positive_weight is not None and negative_weight is not None:
            if positive_weight >= negative_weight:
                warnings.append(f"negative_weight ({negative_weight}) should typically be higher than positive_weight ({positive_weight}) for better learning")
        
        return warnings
    
    def print_config_summary(self):
        """打印当前配置摘要（用于调试）"""
        print("Current Configuration:")
        for key, value in self.config.items():
            print(f"  {key}: {value}")
        
        warnings = self.validate_config()
        if warnings:
            print("Configuration Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
