"""
LLM entity definitions
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token使用统计"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        # 自动计算total_tokens
        if self.total_tokens == 0 and (self.input_tokens > 0 or self.output_tokens > 0):
            self.total_tokens = self.input_tokens + self.output_tokens


class LLMConfig(BaseModel):
    """LLM配置"""
    model_type: str
    model_version: str
    api_key: str
    api_base: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: int = 120


class LLMResponse(BaseModel):
    """LLM响应"""
    content: str
    token_usage: TokenUsage
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        """判断是否成功"""
        return self.error is None

