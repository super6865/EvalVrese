"""
Trace models for observability
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, Index
from datetime import datetime
from app.core.database import Base


class Trace(Base):
    __tablename__ = "traces"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String(64), nullable=False, unique=True, index=True)
    service_name = Column(String(255), nullable=True, index=True)
    operation_name = Column(String(255), nullable=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    status_code = Column(String(20), nullable=True)
    attributes = Column(JSON, nullable=True)  # Additional trace attributes
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_trace_service_time', 'service_name', 'start_time'),
    )


class Span(Base):
    __tablename__ = "spans"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String(64), nullable=False, index=True)
    span_id = Column(String(64), nullable=False, unique=True, index=True)
    parent_span_id = Column(String(64), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    kind = Column(String(50), nullable=True)  # SERVER, CLIENT, etc.
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    status_code = Column(String(20), nullable=True)
    status_message = Column(Text, nullable=True)
    attributes = Column(JSON, nullable=True)
    events = Column(JSON, nullable=True)  # List of events
    links = Column(JSON, nullable=True)  # List of links
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_span_trace_id', 'trace_id'),
        Index('idx_span_parent', 'parent_span_id'),
    )

