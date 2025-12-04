"""
Evaluator record API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import get_db
from app.services.evaluator_record_service import EvaluatorRecordService
from app.models.evaluator_record import EvaluatorRunStatus
from app.domain.entity.evaluator_entity import Correction
from app.utils.api_decorators import handle_api_errors, handle_not_found

router = APIRouter()


class CorrectionRequest(BaseModel):
    score: Optional[float] = None
    explain: Optional[str] = None


@router.get("/{record_id}")
@handle_not_found("Record not found")
async def get_record(record_id: int, db: Session = Depends(get_db)):
    """Get evaluator record by ID"""
    service = EvaluatorRecordService(db)
    return service.get_record(record_id)


@router.get("/")
async def list_records(
    evaluator_version_id: Optional[int] = Query(None),
    experiment_id: Optional[int] = Query(None),
    experiment_run_id: Optional[int] = Query(None),
    status: Optional[EvaluatorRunStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List evaluator records"""
    service = EvaluatorRecordService(db)
    records = service.list_records(
        evaluator_version_id=evaluator_version_id,
        experiment_id=experiment_id,
        experiment_run_id=experiment_run_id,
        status=status,
        skip=skip,
        limit=limit,
    )
    return {"records": records, "total": len(records)}


@router.post("/{record_id}/correct")
@handle_api_errors
@handle_not_found("Record not found")
async def correct_record(
    record_id: int,
    data: CorrectionRequest,
    updated_by: str = Query(..., description="User who is making the correction"),
    db: Session = Depends(get_db),
):
    """Correct an evaluator record"""
    service = EvaluatorRecordService(db)
    correction = Correction(
        score=data.score,
        explain=data.explain,
        updated_by=updated_by,
    )
    return service.correct_record(record_id, correction, updated_by)

