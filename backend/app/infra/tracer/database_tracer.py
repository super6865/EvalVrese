"""
DatabaseTracer implementation that automatically saves spans to database
This follows coze-loop's pattern where spans are automatically saved when finished
"""
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import logging
from sqlalchemy.orm import Session
from app.infra.tracer.tracer import Tracer
from app.infra.tracer.span import Span

logger = logging.getLogger(__name__)


class DatabaseTracer(Tracer):
    """
    DatabaseTracer that automatically saves spans to database when finished.
    
    This follows coze-loop's pattern:
    - When span.Finish() is called, the span is automatically exported/saved
    - No need to manually collect spans into a list
    - Each span is saved individually when finished
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize DatabaseTracer
        
        Args:
            db: Database session. If None, must be provided in finish_span
        """
        self._db = db
    
    def set_db(self, db: Session):
        """Set database session"""
        self._db = db
    
    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        kind: str = "INTERNAL",
        start_time: Optional[datetime] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """
        Start a new span
        
        Args:
            name: Span name
            trace_id: Trace ID (if None, creates a new trace)
            parent_span_id: Parent span ID (if None, creates a root span)
            kind: Span kind (INTERNAL, SERVER, CLIENT, etc.)
            start_time: Start time (if None, uses current time)
            attributes: Initial attributes
            
        Returns:
            Span instance
        """
        # Generate trace_id if not provided
        if trace_id is None:
            trace_id = self._generate_trace_id()
        
        # Get database session (use self._db if available)
        db_session = self._db
        
        span = Span(
            trace_id=trace_id,
            span_id=None,  # Let Span generate its own span_id
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            start_time=start_time,
            db=db_session,  # Pass db session to span for auto-saving
        )
        
        if attributes:
            span.set_attributes(attributes)
        
        # Log span creation
        is_root = not parent_span_id or parent_span_id == ""
        logger.info(f"[DatabaseTracer] Created span: span_id={span.span_id}, name={name}, trace_id={trace_id}, parent_span_id={parent_span_id}, is_root={is_root}")
        
        return span
    
    def finish_span(self, span: Span, db: Optional[Session] = None):
        """
        Finish a span (following coze-loop's pattern).
        
        This follows coze-loop's pattern where span.Finish(ctx) automatically
        triggers export/save to database. The actual saving is handled by Span.finish().
        
        Args:
            span: Span to finish
            db: Optional database session. If provided, sets it on the span before finishing.
                If None, span uses its internal _db if set.
        """
        # Set db session on span if provided
        if db:
            span.set_db(db)
        elif self._db and not span._db:
            # If span doesn't have db but tracer does, set it
            span.set_db(self._db)
        
        # Finish the span - it will automatically save itself (following coze-loop's pattern)
        session_to_use = db or self._db
        logger.info(f"[DatabaseTracer] 🔄 Finishing span: span_id={span.span_id}, name={span.name}, trace_id={span.trace_id}, parent_span_id={span.parent_span_id}, has_db_session={session_to_use is not None}")
        if not session_to_use:
            logger.error(f"[DatabaseTracer] ❌ CRITICAL: No database session available for span {span.span_id}! Span will NOT be saved!")
        span.finish(db=session_to_use)
        logger.info(f"[DatabaseTracer] ✅ Span.finish() called for span_id={span.span_id} (should be auto-saved by Span.finish())")
    
    @staticmethod
    def _generate_trace_id() -> str:
        """Generate a unique trace ID"""
        return format(uuid.uuid4().int & (1 << 128) - 1, '032x')

