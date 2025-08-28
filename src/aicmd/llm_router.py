"""
API Router - 负责路由到不同的LLM提供商
Manages routing to different LLM providers based on configuration
"""

from typing import Optional, Dict, Any
from .llm_providers import (
    LLMProvider,
    OpenRouterProvider,
    OpenAIProvider,
    DeepSeekProvider,
    XAIProvider,
    GeminiProvider,
    QwenProvider,
)
from .config_manager import ConfigManager
from .error_handler import GracefulDegradationManager
from .logger import logger
from .api_client import APIClientError, APIAuthError


class LLMRouter:
    """LLM路由器，负责管理和路由到不同的LLM提供商"""
    
    # 支持的提供商映射
    PROVIDERS = {
        "openrouter": OpenRouterProvider,
        "openai": OpenAIProvider,
        "deepseek": DeepSeekProvider,
        "xai": XAIProvider,
        "gemini": GeminiProvider,
        "qwen": QwenProvider,
    }
    
    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        degradation_manager: Optional[GracefulDegradationManager] = None,
    ):
        """初始化路由器"""
        self.config = config_manager or ConfigManager()
        self.degradation_manager = degradation_manager or GracefulDegradationManager()
        self._providers: Dict[str, LLMProvider] = {}
    
    def _get_default_provider(self) -> str:
        """获取默认提供商名称，优先从配置读取，否则使用openrouter"""
        provider_name = self.config.get("default_provider", "")
        
        # 如果配置中没有指定默认提供商或为空字符串，使用openrouter
        if not provider_name:
            provider_name = "openrouter"
        
        return provider_name.lower()
    
    def _get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """获取指定提供商的配置"""
        # 从配置中获取提供商特定配置
        providers_config = self.config.get("providers", {})
        return providers_config.get(provider_name, {})
    
    def _create_provider(self, provider_name: str) -> LLMProvider:
        """创建指定的提供商实例"""
        if provider_name not in self.PROVIDERS:
            raise APIClientError(f"Unsupported provider: {provider_name}")
        
        provider_class = self.PROVIDERS[provider_name]
        provider_config = self._get_provider_config(provider_name)
        
        return provider_class(provider_config)
    
    def _get_provider(self, provider_name: Optional[str] = None) -> LLMProvider:
        """获取提供商实例，如果不存在则创建"""
        if provider_name is None:
            provider_name = self._get_default_provider()
        
        provider_name = provider_name.lower()
        
        if provider_name not in self._providers:
            self._providers[provider_name] = self._create_provider(provider_name)
        
        return self._providers[provider_name]
    
    def send_chat(
        self, 
        prompt: str, 
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> str:
        """发送聊天请求到指定或默认提供商"""
        provider = self._get_provider(provider_name)
        
        # 使用配置中的超时时间如果没有指定
        if timeout is None:
            timeout = self.config.get("api_timeout_seconds", 30)
        
        return provider.send_chat(prompt, model, timeout)
    
    def send_chat_with_fallback(
        self, 
        prompt: str,
        provider_name: Optional[str] = None
    ) -> str:
        """发送聊天请求，支持备用提供商的回退"""
        
        def main_api_operation():
            try:
                # 尝试主提供商
                return self.send_chat(prompt, provider_name)
            except (APIClientError, APIAuthError) as e:
                # 如果指定了提供商且失败，尝试回退到默认提供商
                if provider_name and provider_name.lower() != self._get_default_provider():
                    try:
                        logger.warning(f"Provider {provider_name} failed ({e}), trying default provider")
                        return self.send_chat(prompt)  # 使用默认提供商
                    except Exception as backup_e:
                        logger.error(f"Default provider also failed: {backup_e}")
                        return f"Error: {backup_e}"
                else:
                    return f"Error: {e}"
        
        def fallback_operation():
            return "Error: Unable to process request due to system issues."
        
        # 使用错误处理机制保护API调用
        return self.degradation_manager.with_cache_fallback(
            main_api_operation, fallback_operation, "llm_router_send_chat"
        )
    
    def list_providers(self) -> list:
        """列出所有支持的提供商"""
        return list(self.PROVIDERS.keys())
    
    def get_current_provider(self) -> str:
        """获取当前默认提供商名称"""
        return self._get_default_provider()
    
    def validate_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """验证提供商配置是否有效"""
        if provider_name not in self.PROVIDERS:
            return {
                "valid": False,
                "error": f"Unsupported provider: {provider_name}"
            }
        
        try:
            provider = self._create_provider(provider_name)
            api_key = provider.get_api_key()
            model = provider.get_model()
            base_url = provider.get_base_url()
            
            issues = []
            if not api_key:
                issues.append(f"API key not configured for {provider_name}")
            if not model:
                issues.append(f"Model not configured for {provider_name}")
            if not base_url:
                issues.append(f"Base URL not configured for {provider_name}")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "config": {
                    "api_key": "***" if api_key else None,
                    "model": model,
                    "base_url": base_url,
                }
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    def close(self):
        """关闭所有提供商的连接"""
        for provider in self._providers.values():
            provider.close()
        self._providers.clear()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()