"""
Tracer implementation for creating and managing traces
"""
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from app.infra.tracer.span import Span
from app.infra.tracer.provider import TracerProvider


class Tracer:
    """Interface for creating and managing traces"""
    
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
        raise NotImplementedError
    
    def finish_span(self, span: Span, db=None):
        """
        Finish a span and report it
        
        Args:
            span: Span to finish
            db: Optional database session (for DatabaseTracer)
        """
        raise NotImplementedError


class DefaultTracer(Tracer):
    """Default tracer implementation that stores spans in memory"""
    
    def __init__(self):
        self._spans: list = []
    
    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        kind: str = "INTERNAL",
        start_time: Optional[datetime] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new span"""
        # Generate trace_id if not provided
        if trace_id is None:
            trace_id = self._generate_trace_id()
        
        span = Span(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            start_time=start_time,
        )
        
        if attributes:
            span.set_attributes(attributes)
        
        return span
    
    def finish_span(self, span: Span, db=None):
        """Finish a span"""
        span.finish()
        self._spans.append(span)
    
    @staticmethod
    def _generate_trace_id() -> str:
        """Generate a unique trace ID"""
        return format(uuid.uuid4().int & (1 << 128) - 1, '032x')
    
    def get_spans(self) -> list:
        """Get all finished spans (for testing/debugging)"""
        return self._spans.copy()
    
    def clear(self):
        """Clear all spans (for testing)"""
        self._spans.clear()


# Global tracer functions
def get_tracer() -> Tracer:
    """Get the global tracer instance"""
    return TracerProvider.get_tracer()


def init_tracer(tracer: Optional[Tracer] = None):
    """Initialize the global tracer"""
    if tracer:
        TracerProvider.set_tracer(tracer)
    else:
        TracerProvider.set_tracer(DefaultTracer())

