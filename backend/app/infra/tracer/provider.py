"""
Tracer provider for managing tracer instances
"""
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.infra.tracer.tracer import Tracer


class TracerProvider:
    """Provider for tracer instances"""
    
    _instance: Optional['Tracer'] = None
    
    @classmethod
    def get_tracer(cls) -> 'Tracer':
        """Get the global tracer instance"""
        if cls._instance is None:
            # Lazy import to avoid circular dependency
            from app.infra.tracer.tracer import DefaultTracer
            cls._instance = DefaultTracer()
        return cls._instance
    
    @classmethod
    def set_tracer(cls, tracer: 'Tracer'):
        """Set the global tracer instance"""
        cls._instance = tracer
    
    @classmethod
    def reset(cls):
        """Reset the tracer instance (mainly for testing)"""
        cls._instance = None

