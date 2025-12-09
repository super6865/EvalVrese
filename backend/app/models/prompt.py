"""
Prompt models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    prompt_key = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Version info
    latest_version = Column(String(50), nullable=True)
    latest_committed_at = Column(DateTime, nullable=True)
    
    # Draft info (stored as JSON)
    draft_detail = Column(JSON, nullable=True)  # Contains: messages, variables, model_config, tools
    draft_updated_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    
    # Status
    status = Column(String(20), default="active", index=True)  # active, deleted
    
    # Relationships
    versions = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan")
    executions = relationship("PromptExecution", back_populates="prompt", cascade="all, delete-orphan")


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    version = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Version content (stored as JSON)
    content = Column(JSON, nullable=False)  # Contains: messages, variables, model_config, tools
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    
    # Relationships
    prompt = relationship("Prompt", back_populates="versions")


class PromptExecution(Base):
    __tablename__ = "prompt_executions"

    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False, index=True)
    
    # Execution input/output
    input_data = Column(JSON, nullable=True)  # Input messages, variables
    output_content = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    
    # Usage and performance
    usage = Column(JSON, nullable=True)  # {input_tokens, output_tokens}
    time_consuming_ms = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    prompt = relationship("Prompt", back_populates="executions")
