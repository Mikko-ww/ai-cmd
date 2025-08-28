"""
Multi-Provider API Client - 使用路由器的API客户端包装器
Provides backward compatibility while using the new LLM router system
"""

from typing import Optional
from .config_manager import ConfigManager
from .error_handler import GracefulDegradationManager
from .llm_router import LLMRouter
from .logger import logger


class MultiProviderAPIClient:
    """多提供商API客户端，提供与原OpenRouterAPIClient相同的接口"""
    
    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        degradation_manager: Optional[GracefulDegradationManager] = None,
        base_url: Optional[str] = None,
    ):
        """初始化多提供商API客户端"""
        self.config = config_manager or ConfigManager()
        self.degradation_manager = degradation_manager or GracefulDegradationManager()
        
        # 初始化路由器
        self.router = LLMRouter(
            config_manager=self.config,
            degradation_manager=self.degradation_manager
        )
        
        # 向后兼容：如果指定了base_url，可能是为了覆盖OpenRouter的URL
        self.override_base_url = base_url
        
        # 请求配置
        self.timeout = self.config.get("api_timeout_seconds", 30)
        self.max_retries = self.config.get("max_retries", 3)
        
    def send_chat(
        self, 
        prompt: str, 
        model: Optional[str] = None, 
        timeout: Optional[int] = None
    ) -> str:
        """发送聊天请求，兼容原OpenRouterAPIClient接口"""
        request_timeout = timeout or self.timeout
        
        # 如果有base_url覆盖，我们需要特殊处理
        if self.override_base_url:
            # 临时设置OpenRouter提供商的base_url
            providers_config = self.config.get("providers", {})
            openrouter_config = providers_config.get("openrouter", {})
            original_base_url = openrouter_config.get("base_url")
            
            # 临时修改配置
            openrouter_config["base_url"] = self.override_base_url
            providers_config["openrouter"] = openrouter_config
            self.config.set("providers", providers_config)
            
            try:
                # 使用openrouter提供商
                result = self.router.send_chat(
                    prompt, 
                    provider_name="openrouter",
                    model=model,
                    timeout=request_timeout
                )
            finally:
                # 恢复原始配置
                if original_base_url:
                    openrouter_config["base_url"] = original_base_url
                else:
                    openrouter_config.pop("base_url", None)
                providers_config["openrouter"] = openrouter_config
                self.config.set("providers", providers_config)
            
            return result
        else:
            # 使用默认提供商
            return self.router.send_chat(
                prompt, 
                model=model,
                timeout=request_timeout
            )
    
    def send_chat_with_fallback(self, prompt: str) -> str:
        """发送聊天请求，支持回退机制"""
        return self.router.send_chat_with_fallback(prompt)
    
    def close(self):
        """关闭所有连接"""
        self.router.close()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()