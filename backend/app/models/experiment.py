"""
Experiment models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class ExperimentStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"
    TERMINATED = "terminated"
    TERMINATING = "terminating"


class ExperimentType(str, enum.Enum):
    OFFLINE = "OFFLINE"  # Database enum uses uppercase
    ONLINE = "ONLINE"  # Database enum uses uppercase


class RetryMode(str, enum.Enum):
    RETRY_ALL = "retry_all"
    RETRY_FAILURE = "retry_failure"
    RETRY_TARGET_ITEMS = "retry_target_items"


class ExportStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ExperimentGroup(Base):
    __tablename__ = "experiment_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("experiment_groups.id"), nullable=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = relationship("ExperimentGroup", remote_side=[id], backref="children")
    experiments = relationship("Experiment", back_populates="group")


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    dataset_version_id = Column(Integer, ForeignKey("dataset_versions.id"), nullable=False)
    
    # Evaluation target configuration (JSON)
    # {type: "prompt"|"api"|"none", config: {...}}
    # If None, no evaluation target is used (directly use dataset items)
    evaluation_target_config = Column(JSON, nullable=True)
    
    # List of evaluator version IDs
    evaluator_version_ids = Column(JSON, nullable=False)  # [1, 2, 3]
    
    # Group association
    group_id = Column(Integer, ForeignKey("experiment_groups.id"), nullable=True, index=True)
    
    status = Column(SQLEnum(ExperimentStatus, values_callable=lambda x: [e.value for e in x]), default=ExperimentStatus.PENDING)
    progress = Column(Integer, default=0)  # 0-100
    
    # Extended fields from coze-loop
    item_concur_num = Column(Integer, default=1)  # Concurrent number of items
    expt_type = Column(SQLEnum(ExperimentType, values_callable=lambda x: [e.value for e in x]), default=ExperimentType.OFFLINE)  # Experiment type
    max_alive_time = Column(Integer, nullable=True)  # Maximum alive time in seconds
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)

    # Relationships
    group = relationship("ExperimentGroup", back_populates="experiments")
    runs = relationship("ExperimentRun", back_populates="experiment", cascade="all, delete-orphan")
    results = relationship("ExperimentResult", back_populates="experiment", cascade="all, delete-orphan")
    aggregate_results = relationship("ExperimentAggregateResult", back_populates="experiment", cascade="all, delete-orphan")
    exports = relationship("ExperimentResultExport", back_populates="experiment", cascade="all, delete-orphan")


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    run_number = Column(Integer, nullable=False)  # Sequential run number
    status = Column(SQLEnum(ExperimentStatus, values_callable=lambda x: [e.value for e in x]), default=ExperimentStatus.PENDING)
    progress = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    task_id = Column(String(255), nullable=True, index=True)  # Celery task ID
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    experiment = relationship("Experiment", back_populates="runs")
    results = relationship("ExperimentResult", back_populates="run", cascade="all, delete-orphan")


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    run_id = Column(Integer, ForeignKey("experiment_runs.id"), nullable=False)
    dataset_item_id = Column(Integer, ForeignKey("dataset_items.id"), nullable=False)
    evaluator_version_id = Column(Integer, ForeignKey("evaluator_versions.id"), nullable=False)
    
    # Evaluation results
    score = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)  # Additional evaluation details
    
    # Execution metadata
    actual_output = Column(Text, nullable=True)  # Output from evaluation target
    execution_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    trace_id = Column(String(64), nullable=True, index=True)  # Trace ID for observability
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    experiment = relationship("Experiment", back_populates="results")
    run = relationship("ExperimentRun", back_populates="results")


class ExperimentAggregateResult(Base):
    __tablename__ = "experiment_aggregate_results"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False, index=True)
    evaluator_version_id = Column(Integer, ForeignKey("evaluator_versions.id"), nullable=False, index=True)
    
    # Aggregate results (JSON)
    # Contains: average, sum, max, min, distribution
    aggregate_data = Column(JSON, nullable=False)
    
    # Average score (for quick access)
    average_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    experiment = relationship("Experiment", back_populates="aggregate_results")


class ExperimentResultExport(Base):
    __tablename__ = "experiment_result_exports"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False, index=True)
    
    status = Column(SQLEnum(ExportStatus, values_callable=lambda x: [e.value for e in x]), default=ExportStatus.PENDING)
    file_url = Column(String(500), nullable=True)  # URL to exported file
    file_name = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)

    # Relationships
    experiment = relationship("Experiment", back_populates="exports")


class CeleryTaskLogLevel(str, enum.Enum):
    INFO = "INFO"
    ERROR = "ERROR"
    WARNING = "WARNING"
    DEBUG = "DEBUG"


class CeleryTaskLog(Base):
    __tablename__ = "celery_task_logs"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("experiment_runs.id"), nullable=False, index=True)
    task_id = Column(String(255), nullable=False, index=True)  # Celery task ID
    log_level = Column(SQLEnum(CeleryTaskLogLevel, values_callable=lambda x: [e.value for e in x]), nullable=False)
    message = Column(Text, nullable=False)
    step_name = Column(String(100), nullable=True)  # Step name like "task_start", "process_item", etc.
    input_data = Column(JSON, nullable=True)  # Input data for this step
    output_data = Column(JSON, nullable=True)  # Output data for this step
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

