"""
LLM Provider抽象接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.domain.entity.llm_entity import LLMConfig, TokenUsage


class ProviderResponse:
    """Provider响应"""
    def __init__(self, content: str, token_usage: TokenUsage, metadata: Dict[str, Any] = None):
        self.content = content
        self.token_usage = token_usage
        self.metadata = metadata or {}


class LLMProvider(ABC):
    """LLM Provider抽象基类"""
    
    def __init__(self, config: LLMConfig):
        """
        初始化Provider
        
        Args:
            config: LLM配置
        """
        self.config = config
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> ProviderResponse:
        """
        生成回复
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            system_message: 系统消息（可选，覆盖配置）
            temperature: 温度参数（可选，覆盖配置）
            max_tokens: 最大token数（可选，覆盖配置）
            timeout: 超时时间（可选，覆盖配置）
        
        Returns:
            ProviderResponse: 包含content和token_usage
        """
        pass
    
    @abstractmethod
    def clear_cache(self) -> None:
        """清除缓存"""
        pass

