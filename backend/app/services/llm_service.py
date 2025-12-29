"""
LLM Service - 统一的大模型调用服务
"""
import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.utils.llm_config_manager import LLMConfigManager
from app.providers import AutoGenProvider
from app.domain.entity.llm_entity import LLMResponse, TokenUsage

logger = logging.getLogger(__name__)


class LLMService:
    """统一的大模型调用服务"""
    
    def __init__(self, db: Session):
        """
        初始化LLM Service
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.config_manager = LLMConfigManager(db)
    
    async def invoke(
        self,
        messages: List[Dict[str, Any]],
        model_config_id: int,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> LLMResponse:
        """
        统一的大模型调用入口
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            model_config_id: 模型配置ID（从数据库加载）
            system_message: 系统消息（可选，覆盖模型配置）
            temperature: 温度参数（可选，覆盖模型配置）
            max_tokens: 最大token数（可选，覆盖模型配置）
            timeout: 超时时间（可选，覆盖模型配置）
        
        Returns:
            LLMResponse: 包含content、token_usage、metadata等
        """
        start_time = time.time()
        
        try:
            # 1. 加载模型配置
            logger.info(f"[LLMService] Loading model config: {model_config_id}")
            llm_config = self.config_manager.load_config(model_config_id)
            
            if not llm_config:
                error_msg = f"Model configuration {model_config_id} not found or invalid"
                logger.error(f"[LLMService] {error_msg}")
                return LLMResponse(
                    content="",
                    token_usage=TokenUsage(),
                    metadata={"model_config_id": model_config_id},
                    error=error_msg,
                )
            
            # 2. 创建Provider实例（当前使用AutoGenProvider）
            logger.info(f"[LLMService] Creating provider for model: {llm_config.model_version}")
            provider = AutoGenProvider(llm_config)
            
            # 3. 调用Provider生成回复
            logger.info(f"[LLMService] Invoking LLM with {len(messages)} message(s)")
            logger.debug(f"[LLMService] Messages: {messages}")
            
            response = await provider.generate(
                messages=messages,
                system_message=system_message,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            
            # 4. 计算耗时
            elapsed_time = time.time() - start_time
            
            # 5. 构建响应
            llm_response = LLMResponse(
                content=response.content,
                token_usage=response.token_usage,
                metadata={
                    **response.metadata,
                    "model_config_id": model_config_id,
                    "elapsed_time": elapsed_time,
                    "message_count": len(messages),
                },
            )
            
            # 6. 记录日志
            logger.info(
                f"[LLMService] ✅ LLM invocation completed: "
                f"model={llm_config.model_version}, "
                f"tokens={response.token_usage.total_tokens} "
                f"(input={response.token_usage.input_tokens}, "
                f"output={response.token_usage.output_tokens}), "
                f"time={elapsed_time:.2f}s"
            )
            
            # 7. 验证Token统计
            if response.token_usage.total_tokens == 0:
                logger.warning(
                    f"[LLMService] ⚠️ Token usage is 0, this may indicate caching or extraction failure. "
                    f"Model: {llm_config.model_version}"
                )
            
            return llm_response
            
        except ValueError as e:
            # 已知错误（连接错误、超时错误等）
            error_msg = str(e)
            elapsed_time = time.time() - start_time
            logger.error(f"[LLMService] ❌ LLM invocation failed: {error_msg}")
            
            return LLMResponse(
                content="",
                token_usage=TokenUsage(),
                metadata={
                    "model_config_id": model_config_id,
                    "elapsed_time": elapsed_time,
                },
                error=error_msg,
            )
            
        except Exception as e:
            # 未知错误
            error_msg = f"Unexpected error: {str(e)}"
            elapsed_time = time.time() - start_time
            logger.error(f"[LLMService] ❌ Unexpected error: {error_msg}", exc_info=True)
            
            return LLMResponse(
                content="",
                token_usage=TokenUsage(),
                metadata={
                    "model_config_id": model_config_id,
                    "elapsed_time": elapsed_time,
                },
                error=error_msg,
            )

