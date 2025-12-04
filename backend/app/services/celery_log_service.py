"""
Celery task log service
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.experiment import CeleryTaskLog, CeleryTaskLogLevel
from datetime import datetime


class CeleryLogService:
    def __init__(self, db: Session):
        self.db = db

    def create_log(
        self,
        experiment_id: int,
        run_id: int,
        task_id: str,
        log_level: CeleryTaskLogLevel,
        message: str,
        step_name: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
    ) -> CeleryTaskLog:
        """Create a new Celery task log entry"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        log = CeleryTaskLog(
            experiment_id=experiment_id,
            run_id=run_id,
            task_id=task_id,
            log_level=log_level,
            message=message,
            step_name=step_name,
            input_data=input_data,
            output_data=output_data,
            timestamp=timestamp,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_logs_by_run(
        self,
        experiment_id: int,
        run_id: int,
        skip: int = 0,
        limit: int = 1000,
    ) -> List[CeleryTaskLog]:
        """Get logs for a specific experiment run"""
        logs = (
            self.db.query(CeleryTaskLog)
            .filter(
                CeleryTaskLog.experiment_id == experiment_id,
                CeleryTaskLog.run_id == run_id,
            )
            .order_by(CeleryTaskLog.timestamp.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return logs

    def get_logs_by_experiment(
        self,
        experiment_id: int,
        skip: int = 0,
        limit: int = 1000,
    ) -> List[CeleryTaskLog]:
        """Get logs for a specific experiment (all runs)"""
        logs = (
            self.db.query(CeleryTaskLog)
            .filter(CeleryTaskLog.experiment_id == experiment_id)
            .order_by(CeleryTaskLog.timestamp.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return logs

    def get_logs_by_task_id(
        self,
        task_id: str,
        skip: int = 0,
        limit: int = 1000,
    ) -> List[CeleryTaskLog]:
        """Get logs for a specific Celery task ID"""
        logs = (
            self.db.query(CeleryTaskLog)
            .filter(CeleryTaskLog.task_id == task_id)
            .order_by(CeleryTaskLog.timestamp.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return logs

    def get_experiments_with_logs(self) -> List[int]:
        """Get list of experiment IDs that have Celery logs"""
        from sqlalchemy import distinct
        experiment_ids = (
            self.db.query(distinct(CeleryTaskLog.experiment_id))
            .all()
        )
        return [exp_id[0] for exp_id in experiment_ids]

