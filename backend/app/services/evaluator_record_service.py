"""
Evaluator record service
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.evaluator_record import EvaluatorRecord, EvaluatorRunStatus
from app.domain.entity.evaluator_entity import (
    EvaluatorInputData,
    EvaluatorOutputData,
    Correction,
)
from datetime import datetime


class EvaluatorRecordService:
    """评估器记录服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_record(
        self,
        evaluator_version_id: int,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        status: EvaluatorRunStatus = EvaluatorRunStatus.UNKNOWN,
        experiment_id: Optional[int] = None,
        experiment_run_id: Optional[int] = None,
        dataset_item_id: Optional[int] = None,
        turn_id: Optional[int] = None,
        trace_id: Optional[str] = None,
        log_id: Optional[str] = None,
        ext: Optional[Dict[str, str]] = None,
        created_by: Optional[str] = None,
    ) -> EvaluatorRecord:
        """
        创建评估器记录
        
        Args:
            evaluator_version_id: 评估器版本ID
            input_data: 输入数据
            output_data: 输出数据
            status: 运行状态
            experiment_id: 实验ID
            experiment_run_id: 实验运行ID
            dataset_item_id: 数据集项ID
            turn_id: 轮次ID
            trace_id: 追踪ID
            log_id: 日志ID
            ext: 扩展字段
            created_by: 创建人
            
        Returns:
            评估器记录
        """
        record = EvaluatorRecord(
            evaluator_version_id=evaluator_version_id,
            input_data=input_data,
            output_data=output_data,
            status=status,
            experiment_id=experiment_id,
            experiment_run_id=experiment_run_id,
            dataset_item_id=dataset_item_id,
            turn_id=turn_id,
            trace_id=trace_id,
            log_id=log_id,
            ext=ext,
            created_by=created_by,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
    
    def get_record(self, record_id: int) -> Optional[EvaluatorRecord]:
        """获取评估器记录"""
        return self.db.query(EvaluatorRecord).filter(EvaluatorRecord.id == record_id).first()
    
    def batch_get_records(self, record_ids: List[int]) -> List[EvaluatorRecord]:
        """批量获取评估器记录"""
        return self.db.query(EvaluatorRecord).filter(
            EvaluatorRecord.id.in_(record_ids)
        ).all()
    
    def list_records(
        self,
        evaluator_version_id: Optional[int] = None,
        experiment_id: Optional[int] = None,
        experiment_run_id: Optional[int] = None,
        status: Optional[EvaluatorRunStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[EvaluatorRecord]:
        """列出评估器记录"""
        query = self.db.query(EvaluatorRecord)
        
        if evaluator_version_id:
            query = query.filter(EvaluatorRecord.evaluator_version_id == evaluator_version_id)
        if experiment_id:
            query = query.filter(EvaluatorRecord.experiment_id == experiment_id)
        if experiment_run_id:
            query = query.filter(EvaluatorRecord.experiment_run_id == experiment_run_id)
        if status:
            query = query.filter(EvaluatorRecord.status == status)
        
        return query.order_by(EvaluatorRecord.created_at.desc()).offset(skip).limit(limit).all()
    
    def correct_record(
        self,
        record_id: int,
        correction: Correction,
        updated_by: str,
    ) -> Optional[EvaluatorRecord]:
        """
        修正评估器记录
        
        Args:
            record_id: 记录ID
            correction: 修正信息
            updated_by: 更新人
            
        Returns:
            更新后的记录
        """
        record = self.get_record(record_id)
        if not record:
            return None
        
        # Update output data with correction
        output_data = record.output_data or {}
        if "evaluator_result" not in output_data:
            output_data["evaluator_result"] = {}
        
        output_data["evaluator_result"]["correction"] = {
            "score": correction.score,
            "explain": correction.explain,
            "updated_by": updated_by,
        }
        
        record.output_data = output_data
        self.db.commit()
        self.db.refresh(record)
        return record

