"""
Evaluator record models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class EvaluatorRunStatus(str, enum.Enum):
    UNKNOWN = "UNKNOWN"
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


class EvaluatorRecord(Base):
    __tablename__ = "evaluator_records"

    id = Column(Integer, primary_key=True, index=True)
    evaluator_version_id = Column(Integer, ForeignKey("evaluator_versions.id"), nullable=False, index=True)
    
    # Experiment context (optional)
    experiment_id = Column(Integer, nullable=True, index=True)
    experiment_run_id = Column(Integer, nullable=True, index=True)
    dataset_item_id = Column(Integer, nullable=True, index=True)
    turn_id = Column(Integer, nullable=True, index=True)
    
    # Input and output data
    input_data = Column(JSON, nullable=False)  # EvaluatorInputData
    output_data = Column(JSON, nullable=False)  # EvaluatorOutputData
    
    # Status and tracking
    status = Column(SQLEnum(EvaluatorRunStatus, values_callable=lambda x: [e.value for e in x]), default=EvaluatorRunStatus.UNKNOWN, nullable=False)
    trace_id = Column(String(255), nullable=True, index=True)
    log_id = Column(String(255), nullable=True)
    
    # Extension fields
    ext = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_by = Column(String(100), nullable=True)

    # Relationships
    evaluator_version = relationship("EvaluatorVersion", back_populates="records")

