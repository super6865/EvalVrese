"""
Experiment execution tasks
"""
from celery import Task
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import InvalidRequestError, PendingRollbackError
from app.core.database import SessionLocal
from app.tasks.celery_app import celery_app
from app.services.experiment_service import ExperimentService
from app.services.experiment_export_service import ExperimentExportService
from app.services.celery_log_service import CeleryLogService
from app.models.experiment import ExperimentStatus, ExportStatus, CeleryTaskLogLevel
from app.infra.celery_log_handler import get_celery_log_handler
import time
import logging

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Task with database session"""
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db


def _log_to_db(db: Session, experiment_id: int, run_id: int, task_id: str, log_level: CeleryTaskLogLevel, message: str, step_name: str = None):
    """Helper function to log to both console and database"""
    try:
        log_service = CeleryLogService(db)
        log_service.create_log(
            experiment_id=experiment_id,
            run_id=run_id,
            task_id=task_id,
            log_level=log_level,
            message=message,
            step_name=step_name,
        )
    except Exception as e:
        # Don't fail the main task if logging fails
        logger.warning(f"Failed to log to database: {str(e)}")


@celery_app.task(bind=True, base=DatabaseTask)
def execute_experiment_task(self, experiment_id: int, run_id: int):
    """
    Execute an experiment task
    
    Args:
        experiment_id: Experiment ID
        run_id: Experiment run ID
    """
    import asyncio
    task_id = self.request.id
    
    # Setup logging handler to capture all logs
    log_handler = get_celery_log_handler()
    log_handler.set_context(experiment_id, run_id, task_id)
    
    # Add handler to relevant loggers
    relevant_loggers = [
        logging.getLogger('app.services.experiment_service'),
        logging.getLogger('app.services.prompt_evaluator_service'),
        logging.getLogger('app.tasks.experiment_tasks'),
        logging.getLogger('app.services.evaluator_service'),
    ]
    
    for log in relevant_loggers:
        if log_handler not in log.handlers:
            log.addHandler(log_handler)
            log.setLevel(logging.INFO)
    
    logger.info(f"========== Starting experiment execution ==========")
    logger.info(f"Experiment ID: {experiment_id}, Run ID: {run_id}")
    logger.info(f"Task ID: {task_id}")
    
    db = self.db
    try:
        # Log task start
        _log_to_db(db, experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO, 
                  f"开始执行实验 - 实验ID: {experiment_id}, 运行ID: {run_id}", 
                  "task_start")
        
        service = ExperimentService(db)
        
        # Run async function in event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new task
            import nest_asyncio
            nest_asyncio.apply()
            logger.debug("Event loop was already running, applied nest_asyncio")
        
        loop.run_until_complete(service.execute_experiment(experiment_id=experiment_id, run_id=run_id))
        
        _log_to_db(db, experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO, 
                  "实验执行完成", 
                  "task_completed")
    except Exception as e:
        error_msg = f"实验执行失败: {str(e)}"
        logger.error(f"========== Experiment execution failed ==========")
        logger.error(f"Error: {str(e)}", exc_info=True)
        
        # Try to recover database session if it's in invalid state
        try:
            # Check if session is in invalid state
            if not db.is_active:
                db.rollback()
                logger.info(f"[ExperimentTask] Rolled back inactive session")
            else:
                transaction = db.get_transaction()
                if transaction and hasattr(transaction, '_state'):
                    state = getattr(transaction, '_state', None)
                    if state == 'prepared':
                        db.rollback()
                        logger.info(f"[ExperimentTask] Rolled back session in prepared state")
        except Exception as session_error:
            logger.warning(f"[ExperimentTask] Failed to recover session: {str(session_error)}")
            # Try to create a new session if recovery failed
            try:
                db.close()
                db = SessionLocal()
                logger.info(f"[ExperimentTask] Created new database session after recovery failure")
            except Exception as new_session_error:
                logger.error(f"[ExperimentTask] Failed to create new session: {str(new_session_error)}")
        
        # Log error to database (with error handling)
        try:
            _log_to_db(db, experiment_id, run_id, task_id, CeleryTaskLogLevel.ERROR, 
                      error_msg, "task_failed")
        except Exception as log_error:
            logger.error(f"[ExperimentTask] Failed to log error to database: {str(log_error)}")
        
        # Update experiment status to failed (with error handling)
        try:
            service = ExperimentService(db)
            service.update_experiment_status(experiment_id, ExperimentStatus.FAILED, error_message=str(e))
        except Exception as status_error:
            logger.error(f"[ExperimentTask] Failed to update experiment status: {str(status_error)}")
            # Try one more time with a fresh session
            try:
                db.close()
                db = SessionLocal()
                service = ExperimentService(db)
                service.update_experiment_status(experiment_id, ExperimentStatus.FAILED, error_message=str(e))
            except Exception as retry_error:
                logger.error(f"[ExperimentTask] Failed to update experiment status with new session: {str(retry_error)}")
        
        raise
    finally:
        # Remove handler and clear context
        for log in relevant_loggers:
            if log_handler in log.handlers:
                log.removeHandler(log_handler)
        log_handler.clear_context()
        
        # Safely close database session
        try:
            if db:
                db.close()
                logger.info(f"Database session closed")
        except Exception as close_error:
            logger.warning(f"Error closing database session: {str(close_error)}")


@celery_app.task(bind=True, base=DatabaseTask)
def export_experiment_results_task(self, experiment_id: int, export_id: int, run_id: int = None):
    """
    Export experiment results to CSV
    
    Args:
        experiment_id: Experiment ID
        export_id: Export task ID
        run_id: Optional run ID
    """
    logger.info(f"========== Starting experiment export ==========")
    logger.info(f"Experiment ID: {experiment_id}, Export ID: {export_id}, Run ID: {run_id}")
    logger.info(f"Task ID: {self.request.id}")
    
    db = self.db
    try:
        service = ExperimentExportService(db)
        logger.info(f"Exporting experiment results to CSV...")
        service.export_experiment_results_csv(experiment_id, export_id, run_id)
        logger.info(f"========== Experiment export completed successfully ==========")
    except Exception as e:
        logger.error(f"========== Experiment export failed ==========")
        logger.error(f"Error: {str(e)}", exc_info=True)
        # Update export status to failed
        service = ExperimentExportService(db)
        service.update_export_status(export_id, ExportStatus.FAILED, error_message=str(e))
        raise
    finally:
        db.close()
        logger.info(f"Database session closed")

