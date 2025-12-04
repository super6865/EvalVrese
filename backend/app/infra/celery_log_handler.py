"""
Custom logging handler for Celery task logs
Captures detailed logs and stores them in the database
"""
import logging
from app.core.database import SessionLocal


class CeleryLogHandler(logging.Handler):
    """Custom handler that stores logs to database
    
    Note: emit() is disabled - only manual logs via _log_to_db() are recorded.
    This handler is kept for backward compatibility but does not actively process logs.
    """
    
    def __init__(self):
        super().__init__()
        self._db = None
        
    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def set_context(self, experiment_id: int, run_id: int, task_id: str):
        # Context is no longer used since emit() is disabled
        pass
    
    def clear_context(self):
        if self._db:
            self._db.close()
            self._db = None
    
    def emit(self, record: logging.LogRecord):
        return


# Global handler instance
_celery_log_handler = None


def get_celery_log_handler() -> CeleryLogHandler:
    global _celery_log_handler
    if _celery_log_handler is None:
        _celery_log_handler = CeleryLogHandler()
    return _celery_log_handler

