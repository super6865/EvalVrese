"""
LLM配置管理器
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.model_config import ModelConfig
from app.utils.crypto import decrypt_api_key
from app.domain.entity.llm_entity import LLMConfig
import logging

logger = logging.getLogger(__name__)


class LLMConfigManager:
    """LLM配置管理器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def load_config(self, model_config_id: int) -> Optional[LLMConfig]:
        """
        从数据库加载模型配置并转换为LLMConfig
        
        Args:
            model_config_id: 模型配置ID
            
        Returns:
            LLMConfig对象，如果配置不存在则返回None
        """
        config = self.db.query(ModelConfig).filter(ModelConfig.id == model_config_id).first()
        
        if not config:
            logger.warning(f"Model configuration {model_config_id} not found")
            return None
        
        # 解密API key
        api_key = decrypt_api_key(config.api_key) if config.api_key else None
        
        if not api_key:
            logger.error(f"Failed to decrypt API key for model configuration {model_config_id}")
            return None
        
        # 转换为LLMConfig
        llm_config = LLMConfig(
            model_type=config.model_type,
            model_version=config.model_version,
            api_key=api_key,
            api_base=config.api_base,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout or 120,
        )
        
        logger.debug(f"Loaded LLM config: {config.config_name} (id={model_config_id})")
        return llm_config

