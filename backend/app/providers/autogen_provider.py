"""
AutoGen Provider实现
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from autogen import ConversableAgent
from app.providers.base import LLMProvider, ProviderResponse
from app.domain.entity.llm_entity import LLMConfig, TokenUsage
from app.utils.autogen_helper import create_autogen_config_from_model_config, _clear_agent_chat_messages

logger = logging.getLogger(__name__)


class AutoGenProvider(LLMProvider):
    """AutoGen Provider实现"""
    
    def __init__(self, config: LLMConfig):
        """
        初始化AutoGen Provider
        
        Args:
            config: LLM配置
        """
        super().__init__(config)
        self.agent = None
        self.last_token_usage = TokenUsage()
    
    def _create_fresh_agent(
        self,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> ConversableAgent:
        """
        创建新的agent实例
        
        Args:
            system_message: 系统消息
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间
        
        Returns:
            ConversableAgent实例
        """
        # 构建模型配置字典
        model_config_dict = {
            "model_type": self.config.model_type,
            "model_version": self.config.model_version,
            "api_key": self.config.api_key,
            "api_base": self.config.api_base,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
            "timeout": timeout if timeout is not None else self.config.timeout,
        }
        
        # 创建autogen配置
        autogen_config = create_autogen_config_from_model_config(model_config_dict)
        
        # 使用提供的system_message或默认值
        default_system_message = system_message or "You are a helpful assistant. Respond to user requests directly and concisely."
        
        # 创建新的agent实例
        logger.info(f"[AutoGenProvider] Creating fresh agent instance (model={self.config.model_version}, temperature={model_config_dict.get('temperature')})")
        agent = ConversableAgent(
            name="llm_agent",
            system_message=default_system_message,
            llm_config=autogen_config,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )
        
        return agent
    
    def _force_clear_all_cache(self, agent: ConversableAgent) -> None:
        """
        强制清除所有可能的缓存
        
        Args:
            agent: ConversableAgent实例
        """
        if not agent:
            return
        
        try:
            # 使用现有的清除函数
            _clear_agent_chat_messages(agent)
            
            # 额外清除：确保client的last_response也被清除
            if hasattr(agent, 'client') and agent.client:
                if hasattr(agent.client, 'last_response'):
                    try:
                        agent.client.last_response = None
                        logger.debug("[AutoGenProvider] Cleared client.last_response")
                    except (AttributeError, TypeError):
                        pass
                
                # 清除client的缓存字典
                if hasattr(agent.client, '_cache'):
                    try:
                        if isinstance(agent.client._cache, dict):
                            agent.client._cache.clear()
                            logger.debug("[AutoGenProvider] Cleared client._cache")
                    except (AttributeError, TypeError):
                        pass
            
            logger.info("[AutoGenProvider] ✅ Successfully cleared all cache")
        except Exception as e:
            logger.warning(f"[AutoGenProvider] ⚠️ Warning: Failed to clear some cache: {str(e)}")
    
    def _extract_token_usage_from_response(self, agent: ConversableAgent) -> TokenUsage:
        """
        从实际API响应中提取Token使用量
        
        Args:
            agent: ConversableAgent实例
        
        Returns:
            TokenUsage对象
        """
        input_tokens = 0
        output_tokens = 0
        
        try:
            # 方法1: 从client.last_response中提取（最可靠，来自实际API响应）
            if hasattr(agent, 'client') and agent.client:
                if hasattr(agent.client, 'last_response') and agent.client.last_response:
                    response = agent.client.last_response
                    if hasattr(response, 'usage'):
                        usage = response.usage
                        if hasattr(usage, 'prompt_tokens'):
                            input_tokens = usage.prompt_tokens or 0
                        if hasattr(usage, 'completion_tokens'):
                            output_tokens = usage.completion_tokens or 0
                        if hasattr(usage, 'total_tokens') and usage.total_tokens:
                            # 如果total_tokens存在，验证一致性
                            total = usage.total_tokens
                            if input_tokens + output_tokens == 0:
                                # 如果input和output都是0，但total有值，尝试从total推断
                                # 这种情况不应该发生，但作为fallback
                                logger.warning(f"[AutoGenProvider] Token usage: total={total} but input/output are 0")
                    elif isinstance(response, dict) and "usage" in response:
                        usage = response["usage"]
                        if isinstance(usage, dict):
                            input_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or 0
                            output_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0
            
            # 方法2: 从agent的usage属性中提取
            if input_tokens == 0 and output_tokens == 0:
                if hasattr(agent, 'usage'):
                    usage = agent.usage
                    if isinstance(usage, dict):
                        input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0) or 0
                        output_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0) or 0
            
            # 方法3: 从chat_messages中提取
            if input_tokens == 0 and output_tokens == 0:
                if hasattr(agent, 'chat_messages') and agent.chat_messages:
                    messages = agent.chat_messages
                    if isinstance(messages, list) and len(messages) > 0:
                        last_message = messages[-1]
                        if isinstance(last_message, dict) and "usage" in last_message:
                            usage = last_message["usage"]
                            if isinstance(usage, dict):
                                input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0) or 0
                                output_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0) or 0
            
            # 验证token值不为0（如果为0，可能是缓存值或提取失败）
            if input_tokens == 0 and output_tokens == 0:
                logger.warning("[AutoGenProvider] ⚠️ Token usage is 0, this may indicate caching or extraction failure")
            else:
                logger.info(f"[AutoGenProvider] ✅ Extracted token usage: input={input_tokens}, output={output_tokens}")
        
        except Exception as e:
            logger.warning(f"[AutoGenProvider] Failed to extract token usage: {str(e)}")
        
        return TokenUsage(
            input_tokens=int(input_tokens) if input_tokens else 0,
            output_tokens=int(output_tokens) if output_tokens else 0,
        )
    
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
            messages: 消息列表
            system_message: 系统消息
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间
        
        Returns:
            ProviderResponse
        """
        # 1. 创建新的agent实例（不使用缓存的agent）
        self.agent = self._create_fresh_agent(
            system_message=system_message,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        
        # 2. 强制清除所有缓存
        self._force_clear_all_cache(self.agent)
        
        # 3. 调用generate_reply（在异步上下文中执行同步调用）
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.agent.generate_reply(messages=messages)
            )
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # 分类错误
            if "connection" in error_msg.lower() or "connect" in error_msg.lower():
                raise ValueError(f"Connection error: Failed to connect to LLM service: {error_msg} (type: {error_type})")
            elif "timeout" in error_msg.lower():
                raise ValueError(f"Timeout error: LLM request timed out: {error_msg} (type: {error_type})")
            elif "api" in error_msg.lower() and "key" in error_msg.lower():
                raise ValueError(f"Authentication error: Invalid API key or authentication failed: {error_msg} (type: {error_type})")
            else:
                raise ValueError(f"LLM invocation error: {error_msg} (type: {error_type})")
        
        # 4. 提取内容
        if isinstance(response, dict):
            content = response.get("content", "")
        elif hasattr(response, "content"):
            content = response.content
        else:
            content = str(response)
        
        # 5. 从实际API响应中提取token usage
        self.last_token_usage = self._extract_token_usage_from_response(self.agent)
        
        # 6. 清理agent（释放资源，但不删除，因为可能需要再次提取token）
        # 注意：我们保留agent以便后续提取token，但会在下次调用时创建新实例
        
        # 7. 构建元数据
        metadata = {
            "model": self.config.model_version,
            "model_type": self.config.model_type,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }
        
        logger.info(f"[AutoGenProvider] ✅ Generated response (length={len(content)}, tokens={self.last_token_usage.total_tokens})")
        
        return ProviderResponse(
            content=content,
            token_usage=self.last_token_usage,
            metadata=metadata,
        )
    
    def clear_cache(self) -> None:
        """清除缓存"""
        if self.agent:
            self._force_clear_all_cache(self.agent)

