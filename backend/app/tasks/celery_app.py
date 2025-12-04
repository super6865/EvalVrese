"""
Celery application configuration
"""
from celery import Celery
from celery.signals import setup_logging
from app.core.config import settings
import logging

celery_app = Celery(
    "evalverse",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Auto-discover tasks in app.tasks package
    include=['app.tasks.experiment_tasks'],
    # Logging configuration
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
    worker_hijack_root_logger=False,  # Don't hijack root logger
)


@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery workers"""
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Configure console handler if not already present
    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '[%(asctime)s: %(levelname)s/%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Set specific loggers to INFO level
    logging.getLogger('app.services.experiment_service').setLevel(logging.INFO)
    logging.getLogger('app.tasks.experiment_tasks').setLevel(logging.INFO)
    logging.getLogger('app.infra.tracer.database_tracer').setLevel(logging.INFO)
    logging.getLogger('app.infra.tracer.span').setLevel(logging.INFO)  # Added for span logging
    logging.getLogger('app.services.observability_service').setLevel(logging.INFO)

# Import tasks to ensure they are registered
from app.tasks import experiment_tasks  # noqa: F401

