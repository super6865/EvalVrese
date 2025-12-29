"""
Evaluator models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class EvaluatorType(str, enum.Enum):
    PROMPT = "prompt"
    CODE = "code"


class EvaluatorBoxType(str, enum.Enum):
    WHITE = "white"  # 白盒
    BLACK = "black"  # 黑盒


class EvaluatorVersionStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ARCHIVED = "archived"


class Evaluator(Base):
    __tablename__ = "evaluators"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    evaluator_type = Column(SQLEnum(EvaluatorType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    latest_version = Column(String(50), nullable=True)
    
    # New fields
    builtin = Column(Boolean, default=False, nullable=False)  # 是否内置评估器
    box_type = Column(SQLEnum(EvaluatorBoxType, values_callable=lambda x: [e.value for e in x]), nullable=True)  # 黑白盒类型
    evaluator_info = Column(JSON, nullable=True)  # benchmark, vendor, vendor_url, user_manual_url
    tags = Column(JSON, nullable=True)  # 标签系统，格式: {"zh-CN": {"Category": [...], ...}, "en-US": {...}}
    
    # Content fields (directly stored in evaluator, synced with versions for backward compatibility)
    prompt_content = Column(JSON, nullable=True)  # For Prompt evaluators: message_list, model_config, etc.
    code_content = Column(JSON, nullable=True)  # For Code evaluators: code_content, language_type, etc.
    input_schemas = Column(JSON, nullable=True)  # 输入 Schema 定义
    output_schemas = Column(JSON, nullable=True)  # 输出 Schema 定义
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)

    # Relationships
    versions = relationship("EvaluatorVersion", back_populates="evaluator", cascade="all, delete-orphan")


class EvaluatorVersion(Base):
    __tablename__ = "evaluator_versions"

    id = Column(Integer, primary_key=True, index=True)
    evaluator_id = Column(Integer, ForeignKey("evaluators.id"), nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(EvaluatorVersionStatus, values_callable=lambda x: [e.value for e in x]), default=EvaluatorVersionStatus.DRAFT, nullable=False)
    
    # Schema definitions
    input_schemas = Column(JSON, nullable=True)  # 输入 Schema 定义
    output_schemas = Column(JSON, nullable=True)  # 输出 Schema 定义
    
    # Type-specific content
    # For Prompt: message_list, model_config, tools, parse_type, prompt_suffix, receive_chat_history
    prompt_content = Column(JSON, nullable=True)
    # For Code: code_content, language_type, code_template_key, code_template_name
    code_content = Column(JSON, nullable=True)
    
    # Legacy content field (for backward compatibility)
    content = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)

    # Relationships
    evaluator = relationship("Evaluator", back_populates="versions")
    records = relationship("EvaluatorRecord", back_populates="evaluator_version", cascade="all, delete-orphan")

