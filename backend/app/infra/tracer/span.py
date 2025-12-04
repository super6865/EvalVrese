"""
Span implementation for tracing
"""
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import json
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class Span:
    """Represents a single span in a trace"""
    
    def __init__(
        self,
        trace_id: str,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        name: str = "",
        kind: str = "INTERNAL",
        start_time: Optional[datetime] = None,
        db: Optional[Session] = None,
    ):
        self.trace_id = trace_id
        self.span_id = span_id or self._generate_span_id()
        self.parent_span_id = parent_span_id
        self.name = name
        self.kind = kind
        self.start_time = start_time or datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.duration_ms: Optional[float] = None
        self.status_code: Optional[str] = None
        self.status_message: Optional[str] = None
        self.attributes: Dict[str, Any] = {}
        self.events: list = []
        self.links: list = []
        self._is_finished = False
        self._db: Optional[Session] = db  # Database session for auto-saving
        
    @staticmethod
    def _generate_span_id() -> str:
        return format(uuid.uuid4().int & (1 << 64) - 1, '016x')
    
    def set_attribute(self, key: str, value: Any):
        if not self._is_finished:
            self.attributes[key] = value
    
    def set_attributes(self, attributes: Dict[str, Any]):
        if not self._is_finished:
            self.attributes.update(attributes)
    
    def set_input(self, input_data: Any):
        if not self._is_finished:
            if isinstance(input_data, (dict, list)):
                self.attributes["input"] = input_data
            else:
                self.attributes["input"] = str(input_data)
    
    def set_output(self, output_data: Any):
        if not self._is_finished:
            if isinstance(output_data, (dict, list)):
                self.attributes["output"] = output_data
            else:
                self.attributes["output"] = str(output_data)
    
    def set_error(self, error: Exception):
        if not self._is_finished:
            self.status_code = "ERROR"
            self.status_message = str(error)
            self.attributes["error"] = {
                "type": type(error).__name__,
                "message": str(error),
            }
    
    def set_status_code(self, code: str):
        if not self._is_finished:
            self.status_code = code
    
    def add_event(self, name: str, timestamp: Optional[datetime] = None, attributes: Optional[Dict[str, Any]] = None):
        if not self._is_finished:
            event = {
                "name": name,
                "timestamp": (timestamp or datetime.utcnow()).isoformat(),
                "attributes": attributes or {},
            }
            self.events.append(event)
    
    def set_db(self, db: Session):
        self._db = db
    
    def finish(self, end_time: Optional[datetime] = None, db: Optional[Session] = None):
        """
        Finish the span and automatically save to database (following coze-loop's pattern).
        
        This matches coze-loop's behavior where span.Finish(ctx) automatically triggers
        export/save to database.
        
        Args:
            end_time: Optional end time. If None, uses current time.
            db: Optional database session. If None, uses self._db if set.
        """
        if self._is_finished:
            return
        
        self.end_time = end_time or datetime.utcnow()
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.duration_ms = delta.total_seconds() * 1000
        
        if not self.status_code:
            self.status_code = "OK"
        
        self._is_finished = True
        
        # Automatically save to database (following coze-loop's pattern)
        session = db or self._db
        if session:
            try:
                # Lazy import to avoid circular dependency
                from app.services.observability_service import ObservabilityService
                
                # Log span details before saving
                is_root = not self.parent_span_id or self.parent_span_id == ""
                logger.info(f"[Span] Auto-saving span on finish: span_id={self.span_id}, name={self.name}, trace_id={self.trace_id}, parent_span_id={self.parent_span_id}, is_root={is_root}")
                
                # Save span to database (like coze-loop's exporter)
                observability_service = ObservabilityService(session)
                saved_span = observability_service.save_span(self)
                
                if saved_span:
                    logger.info(f"[Span] ✅ Successfully auto-saved span {self.span_id} (name={self.name}, is_root={is_root}) to database")
                else:
                    logger.error(f"[Span] ❌ CRITICAL: save_span returned None! span_id={self.span_id}, name={self.name}")
                    
            except Exception as e:
                logger.error(f"[Span] ❌ CRITICAL ERROR auto-saving span {self.span_id} (name={self.name}, trace_id={self.trace_id}): {str(e)}", exc_info=True)
                logger.error(f"[Span]   - Exception type: {type(e).__name__}")
                logger.error(f"[Span]   - Exception args: {e.args}")
                # Don't raise - span finishing should not fail the operation
        else:
            logger.warning(f"[Span] ⚠️ No database session available, span {self.span_id} not auto-saved (this is OK if saving manually)")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status_code": self.status_code,
            "status_message": self.status_message,
            "attributes": self.attributes,
            "events": self.events,
            "links": self.links,
        }
    
    def get_trace_id(self) -> str:
        return self.trace_id
    
    def get_span_id(self) -> str:
        return self.span_id

