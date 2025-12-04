"""
Logging utilities for consistent log formatting
"""
import logging
from typing import Optional, Dict, Any
from app.models.experiment import CeleryTaskLogLevel

logger = logging.getLogger(__name__)


class ServiceLogger:
    """Utility class for consistent service logging"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
    
    def _format_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Format log message with optional context"""
        if context:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            return f"[{self.service_name}] {message} ({context_str})"
        return f"[{self.service_name}] {message}"
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log info message"""
        self.logger.info(self._format_message(message, context))
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log error message"""
        self.logger.error(self._format_message(message, context), exc_info=exc_info)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        self.logger.warning(self._format_message(message, context))
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log debug message"""
        self.logger.debug(self._format_message(message, context))


def get_service_logger(service_name: str) -> ServiceLogger:
    """Get a service logger instance"""
    return ServiceLogger(service_name)


def log_celery_task_event(
    celery_log_service,
    experiment_id: int,
    run_id: int,
    task_id: str,
    level: CeleryTaskLogLevel,
    message: str,
    step_name: str,
    input_data: Optional[Dict[str, Any]] = None,
    output_data: Optional[Dict[str, Any]] = None,
):
    """
    Logs a Celery task event to the database using CeleryLogService.
    """
    celery_log_service.create_log(
        experiment_id=experiment_id,
        run_id=run_id,
        task_id=task_id,
        log_level=level,
        message=message,
        step_name=step_name,
        input_data=input_data,
        output_data=output_data,
    )

