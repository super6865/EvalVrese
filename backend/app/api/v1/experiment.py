"""
Experiment API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from app.core.database import get_db
from app.services.experiment_service import ExperimentService
from app.services.observability_service import ObservabilityService
from app.services.celery_log_service import CeleryLogService
from app.models.experiment import ExperimentStatus, RetryMode, ExportStatus, CeleryTaskLog
from app.tasks.experiment_tasks import execute_experiment_task, export_experiment_results_task
from app.services.experiment_export_service import ExperimentExportService
from app.services.experiment_comparison_service import ExperimentComparisonService
from app.utils.api_decorators import handle_api_errors, handle_not_found
from fastapi.responses import FileResponse
import os

router = APIRouter()


# Request/Response models
class ExperimentCreate(BaseModel):
    name: str
    dataset_version_id: int
    evaluation_target_config: Optional[Dict[str, Any]] = None  # Optional, can be skipped
    evaluator_version_ids: Optional[List[int]] = None  # Optional, but should have at least one when provided
    description: Optional[str] = None


class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ExportRecordResponse(BaseModel):
    """Response model for export records"""
    id: int
    experiment_id: int
    status: str
    file_name: Optional[str] = None
    file_url: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ExperimentClone(BaseModel):
    name: Optional[str] = None


class ExperimentRetry(BaseModel):
    retry_mode: Optional[str] = "retry_all"  # retry_all, retry_failure, retry_target_items
    item_ids: Optional[List[int]] = None


class CheckNameRequest(BaseModel):
    name: str
    exclude_id: Optional[int] = None


class CheckNameResponse(BaseModel):
    available: bool
    message: Optional[str] = None


class BatchDeleteRequest(BaseModel):
    experiment_ids: List[int]


class CompareExperimentsRequest(BaseModel):
    experiment_ids: List[int]
    run_ids: Optional[Dict[int, int]] = None


# Experiment CRUD
@router.get("")
async def list_experiments(skip: int = 0, limit: int = 100, name: Optional[str] = None, db: Session = Depends(get_db)):
    """List all experiments with optional name filter"""
    service = ExperimentService(db)
    experiments, total = service.list_experiments(skip=skip, limit=limit, name=name)
    return {"experiments": experiments, "total": total}


@router.get("/with-celery-logs")
async def list_experiments_with_logs(
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """List experiments that have Celery logs"""
    from app.models.experiment import Experiment
    from sqlalchemy import distinct, func
    
    # Get distinct experiment IDs that have logs
    experiment_ids = (
        db.query(distinct(CeleryTaskLog.experiment_id))
        .all()
    )
    
    if not experiment_ids:
        return {"experiments": [], "total": 0}
    
    # Extract IDs from tuples
    exp_ids = [exp_id[0] for exp_id in experiment_ids]
    total = len(exp_ids)
    
    # Get experiments with pagination
    experiments = (
        db.query(Experiment)
        .filter(Experiment.id.in_(exp_ids))
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Convert to dict format (same as list_experiments)
    experiments_list = []
    for exp in experiments:
        experiments_list.append({
            "id": exp.id,
            "name": exp.name,
            "description": exp.description,
            "dataset_version_id": exp.dataset_version_id,
            "evaluation_target_config": exp.evaluation_target_config,
            "evaluator_version_ids": exp.evaluator_version_ids,
            "status": exp.status.value if hasattr(exp.status, 'value') else str(exp.status),
            "progress": exp.progress,
            "created_at": exp.created_at.isoformat() if exp.created_at else None,
            "updated_at": exp.updated_at.isoformat() if exp.updated_at else None,
            "created_by": exp.created_by,
        })
    
    return {"experiments": experiments_list, "total": total}


@router.post("")
async def create_experiment(data: ExperimentCreate, db: Session = Depends(get_db)):
    """Create a new experiment"""
    # Validate evaluator_version_ids
    if not data.evaluator_version_ids or len(data.evaluator_version_ids) == 0:
        raise HTTPException(status_code=400, detail="At least one evaluator version is required")
    
    service = ExperimentService(db)
    experiment = service.create_experiment(
        name=data.name,
        dataset_version_id=data.dataset_version_id,
        evaluation_target_config=data.evaluation_target_config,
        evaluator_version_ids=data.evaluator_version_ids or [],
        description=data.description,
    )
    return experiment


@router.get("/{experiment_id}")
@handle_not_found("Experiment not found")
async def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """Get experiment by ID"""
    service = ExperimentService(db)
    return service.get_experiment(experiment_id)


@router.put("/{experiment_id}")
@handle_api_errors
@handle_not_found("Experiment not found")
async def update_experiment(experiment_id: int, data: ExperimentUpdate, db: Session = Depends(get_db)):
    """Update experiment"""
    service = ExperimentService(db)
    return service.update_experiment(
        experiment_id=experiment_id,
        name=data.name,
        description=data.description,
    )


@router.delete("/{experiment_id}")
@handle_api_errors
async def delete_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """Delete experiment"""
    service = ExperimentService(db)
    success = service.delete_experiment(experiment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"message": "Experiment deleted successfully"}


# Run management
@router.post("/{experiment_id}/runs")
async def create_run(experiment_id: int, db: Session = Depends(get_db)):
    """Create a new experiment run"""
    service = ExperimentService(db)
    try:
        run = service.create_run(experiment_id)
        return run
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{experiment_id}/runs")
async def list_runs(experiment_id: int, db: Session = Depends(get_db)):
    """List all runs of an experiment"""
    service = ExperimentService(db)
    experiment = service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"runs": experiment.runs}


@router.get("/runs/{run_id}")
async def get_run(run_id: int, db: Session = Depends(get_db)):
    """Get experiment run by ID"""
    service = ExperimentService(db)
    run = service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{experiment_id}/run")
async def run_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """Run an experiment (creates a run and starts execution)"""
    service = ExperimentService(db)
    
    # Verify experiment exists
    experiment = service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Create a new run
    run = service.create_run(experiment_id)
    
    # Start async task
    task = execute_experiment_task.delay(experiment_id, run.id)
    
    # Update run with task_id
    run.task_id = task.id
    db.commit()
    
    return {
        "run_id": run.id,
        "task_id": task.id,
        "message": "Experiment started",
    }


@router.post("/{experiment_id}/stop")
async def stop_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """Stop a running experiment"""
    service = ExperimentService(db)
    experiment = service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Update status to stopped
    service.update_experiment_status(experiment_id, ExperimentStatus.STOPPED)
    
    # Also stop the latest run if it's running
    if experiment.runs:
        latest_run = max(experiment.runs, key=lambda r: r.run_number)
        if latest_run.status == ExperimentStatus.RUNNING:
            service.update_run_status(latest_run.id, ExperimentStatus.STOPPED)
    
    return {"message": "Experiment stopped"}


# Results
@router.get("/{experiment_id}/results")
async def get_results(experiment_id: int, run_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get experiment results"""
    from app.models.dataset import DatasetItem
    
    service = ExperimentService(db)
    results = service.get_results(experiment_id, run_id=run_id)
    
    # Get unique dataset item IDs
    dataset_item_ids = list(set([r.dataset_item_id for r in results]))
    
    # Load dataset items
    dataset_items = {}
    if dataset_item_ids:
        items = db.query(DatasetItem).filter(DatasetItem.id.in_(dataset_item_ids)).all()
        dataset_items = {item.id: item for item in items}
    
    # Enrich results with input and reference_output from dataset items
    enriched_results = []
    for result in results:
        result_dict = {
            "id": result.id,
            "experiment_id": result.experiment_id,
            "run_id": result.run_id,
            "dataset_item_id": result.dataset_item_id,
            "evaluator_version_id": result.evaluator_version_id,
            "score": result.score,
            "reason": result.reason,
            "details": result.details,
            "actual_output": result.actual_output,
            "execution_time_ms": result.execution_time_ms,
            "error_message": result.error_message,
            "trace_id": result.trace_id,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "input": "",
            "reference_output": "",
        }
        
        # Extract input and reference_output from dataset item
        dataset_item = dataset_items.get(result.dataset_item_id)
        if dataset_item and dataset_item.data_content:
            data_content = dataset_item.data_content
            
            # Try to extract from simple format first
            if isinstance(data_content, dict):
                # Simple format: {"input": "...", "reference_output": "..."}
                result_dict["input"] = str(data_content.get("input", ""))
                # 优先使用 reference_output，如果不存在则使用 answer（排除 output，因为 output 可能是实际输出）
                result_dict["reference_output"] = str(
                    data_content.get("reference_output") or 
                    data_content.get("answer") or 
                    ""
                )
                
                # If not found in simple format, try to extract from turns format
                if ("turns" in data_content) and (not result_dict["input"] or not result_dict["reference_output"]):
                    turns = data_content.get("turns", [])
                    if turns and len(turns) > 0:
                        turn = turns[0]
                        field_data_list = turn.get("field_data_list", [])
                        for field_data in field_data_list:
                            field_key = field_data.get("key", "")
                            field_name = field_data.get("name", "")
                            field_content = field_data.get("content", {})
                            field_text = field_content.get("text", "") if isinstance(field_content, dict) else str(field_content)
                            
                            # Try to match by key or name
                            if not result_dict["input"]:
                                if field_key == "input" or field_name == "input" or field_key.lower() == "input":
                                    result_dict["input"] = str(field_text)
                            
                            if not result_dict["reference_output"]:
                                # 按优先级顺序匹配参考输出字段（排除 output，因为 output 可能是实际输出）
                                # 优先使用 reference_output，然后使用 answer
                                reference_field_priority = ["reference_output", "answer", "reference"]
                                for ref_field in reference_field_priority:
                                    if (field_key == ref_field or field_name == ref_field or 
                                        field_key.lower() == ref_field.lower()):
                                        result_dict["reference_output"] = str(field_text)
                                        break  # 找到第一个匹配的字段就停止
        
        enriched_results.append(result_dict)
    
    return {"results": enriched_results, "total": len(enriched_results)}


# Extended endpoints
@router.post("/check_name")
async def check_experiment_name(data: CheckNameRequest, db: Session = Depends(get_db)):
    """Check if experiment name is available"""
    service = ExperimentService(db)
    available = service.check_experiment_name(data.name, exclude_id=data.exclude_id)
    return CheckNameResponse(
        available=available,
        message="Name is available" if available else "Name already exists"
    )


@router.post("/batch_delete")
async def batch_delete_experiments(data: BatchDeleteRequest, db: Session = Depends(get_db)):
    """Batch delete experiments"""
    service = ExperimentService(db)
    deleted_count = service.batch_delete_experiments(data.experiment_ids)
    return {"message": f"Deleted {deleted_count} experiments", "deleted_count": deleted_count}


@router.post("/{experiment_id}/clone")
async def clone_experiment(experiment_id: int, data: ExperimentClone, db: Session = Depends(get_db)):
    """Clone an experiment"""
    service = ExperimentService(db)
    try:
        cloned = service.clone_experiment(experiment_id, new_name=data.name)
        return cloned
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{experiment_id}/retry")
async def retry_experiment(experiment_id: int, data: ExperimentRetry, db: Session = Depends(get_db)):
    """Retry an experiment"""
    service = ExperimentService(db)
    
    # Verify experiment exists
    experiment = service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    # Parse retry mode
    try:
        retry_mode = RetryMode(data.retry_mode)
    except ValueError:
        retry_mode = RetryMode.RETRY_ALL
    
    # Create new run
    run = service.retry_experiment(experiment_id, retry_mode, data.item_ids)
    
    # Start async task
    task = execute_experiment_task.delay(experiment_id, run.id)
    
    return {
        "run_id": run.id,
        "task_id": task.id,
        "message": "Experiment retry started",
    }


@router.get("/{experiment_id}/aggregate_results")
async def get_aggregate_results(
    experiment_id: int,
    run_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get aggregate results for an experiment"""
    service = ExperimentService(db)
    experiment = service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    results = service.calculate_aggregate_results(experiment_id, run_id, save=True)
    return {"aggregate_results": results}


@router.get("/{experiment_id}/statistics")
async def get_experiment_statistics(
    experiment_id: int,
    run_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get experiment statistics"""
    service = ExperimentService(db)
    try:
        statistics = service.get_experiment_statistics(experiment_id, run_id)
        return statistics
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Export endpoints
@router.post("/{experiment_id}/export")
async def create_export(
    experiment_id: int,
    run_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Create a new export task"""
    try:
        export_service = ExperimentExportService(db)
        experiment_service = ExperimentService(db)
        
        # Verify experiment exists
        experiment = experiment_service.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        
        # Create export task
        export = export_service.create_export_task(experiment_id)
        
        # Start async task
        task_id = None
        celery_available = False
        try:
            task = export_experiment_results_task.delay(experiment_id, export.id, run_id)
            task_id = task.id if task else None
            celery_available = True
        except Exception as task_error:
            # If Celery task creation fails, use thread-based execution as fallback
            import logging
            import threading
            from app.core.database import SessionLocal
            
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to start Celery task for export {export.id}: {str(task_error)}")
            logger.info(f"Falling back to thread-based execution for export {export.id}")
            
            def run_export():
                """Run export in a separate thread"""
                thread_db = SessionLocal()
                thread_service = None
                try:
                    thread_service = ExperimentExportService(thread_db)
                    thread_service.export_experiment_results_csv(experiment_id, export.id, run_id)
                    logger.info(f"Export {export.id} completed successfully via thread")
                except Exception as e:
                    logger.error(f"Export {export.id} failed in thread: {str(e)}", exc_info=True)
                    # Update status to failed
                    try:
                        if thread_service is None:
                            thread_service = ExperimentExportService(thread_db)
                        thread_service.update_export_status(
                            export.id, 
                            ExportStatus.FAILED, 
                            error_message=str(e)
                        )
                    except Exception as update_error:
                        logger.error(f"Failed to update export status: {str(update_error)}", exc_info=True)
                finally:
                    thread_db.close()
            
            # Start export in background thread
            thread = threading.Thread(target=run_export, daemon=True)
            thread.start()
        
        return {
            "export_id": export.id,
            "task_id": task_id,
            "status": export.status,
            "message": "Export task created" + (" (using Celery)" if celery_available else " (using thread)")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create export task: {str(e)}")


@router.get("/{experiment_id}/exports")
async def list_exports(
    experiment_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List export tasks for an experiment"""
    try:
        export_service = ExperimentExportService(db)
        exports = export_service.list_exports(experiment_id, skip=skip, limit=limit)
        
        # Convert SQLAlchemy models to Pydantic models
        export_responses = [ExportRecordResponse.model_validate(exp) for exp in exports]
        
        return {"exports": export_responses, "total": len(export_responses)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list exports: {str(e)}")


@router.get("/exports/{export_id}")
async def get_export(export_id: int, db: Session = Depends(get_db)):
    """Get export task details"""
    try:
        export_service = ExperimentExportService(db)
        export = export_service.get_export(export_id)
        if not export:
            raise HTTPException(status_code=404, detail="Export not found")
        return ExportRecordResponse.model_validate(export)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get export: {str(e)}")


@router.get("/exports/{export_id}/download")
async def download_export(export_id: int, db: Session = Depends(get_db)):
    """Download exported CSV file"""
    try:
        export_service = ExperimentExportService(db)
        export = export_service.get_export(export_id)
        if not export:
            raise HTTPException(status_code=404, detail="Export not found")
        
        # Compare with enum value (database returns string, enum value is also string)
        if export.status != ExportStatus.SUCCESS.value:
            raise HTTPException(status_code=400, detail="Export not completed yet")
        
        if not export.file_url:
            raise HTTPException(status_code=404, detail="Export file URL not found")
        
        # Check if file exists
        file_path = Path(export.file_url)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Export file not found: {export.file_url}")
        
        # Get filename and handle Chinese characters
        filename = export.file_name or f"export_{export_id}.csv"
        
        # Create ASCII-compatible fallback filename (remove non-ASCII characters)
        fallback_filename = filename.encode('ascii', 'ignore').decode('ascii') or f"export_{export_id}.csv"
        
        # URL encode the filename for UTF-8 support (RFC 5987)
        encoded_filename = quote(filename, safe='')
        
        # Set Content-Disposition header with RFC 5987 format
        # Format: attachment; filename="fallback.csv"; filename*=UTF-8''encoded_filename.csv
        content_disposition = f'attachment; filename="{fallback_filename}"; filename*=UTF-8\'\'{encoded_filename}'
        
        # Return file with proper headers for download
        return FileResponse(
            path=str(file_path),
            media_type="text/csv; charset=utf-8",
            filename=fallback_filename,  # Fallback for older browsers
            headers={
                "Content-Disposition": content_disposition
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download export: {str(e)}")


# Comparison endpoints
@router.post("/compare")
async def compare_experiments(
    data: CompareExperimentsRequest,
    db: Session = Depends(get_db)
):
    """Compare multiple experiments"""
    comparison_service = ExperimentComparisonService(db)
    try:
        comparison = comparison_service.compare_experiments(
            data.experiment_ids,
            data.run_ids
        )
        return comparison
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/compare/summary")
async def get_comparison_summary(
    data: CompareExperimentsRequest,
    db: Session = Depends(get_db)
):
    """Get summary comparison of experiments"""
    comparison_service = ExperimentComparisonService(db)
    try:
        summary = comparison_service.get_comparison_summary(
            data.experiment_ids,
            data.run_ids
        )
        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Trace endpoints
@router.get("/{experiment_id}/traces")
async def get_experiment_traces(
    experiment_id: int,
    run_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get all traces for an experiment"""
    service = ExperimentService(db)
    experiment = service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    observability_service = ObservabilityService(db)
    traces = observability_service.get_traces_by_experiment_id(experiment_id, run_id)
    return {"traces": traces, "total": len(traces)}


@router.get("/{experiment_id}/runs/{run_id}/traces")
async def get_run_traces(
    experiment_id: int,
    run_id: int,
    db: Session = Depends(get_db)
):
    """Get all traces for a specific experiment run"""
    service = ExperimentService(db)
    experiment = service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    run = service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    observability_service = ObservabilityService(db)
    traces = observability_service.get_traces_by_run_id(run_id)
    return {"traces": traces, "total": len(traces)}


@router.get("/{experiment_id}/runs/{run_id}/celery-logs")
async def get_celery_logs(
    experiment_id: int,
    run_id: int,
    db: Session = Depends(get_db)
):
    """Get Celery task logs for a specific experiment run"""
    service = ExperimentService(db)
    experiment = service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    run = service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    celery_log_service = CeleryLogService(db)
    logs = celery_log_service.get_logs_by_run(experiment_id, run_id)
    
    # Convert to dict format
    log_list = [
        {
            "id": log.id,
            "experiment_id": log.experiment_id,
            "run_id": log.run_id,
            "task_id": log.task_id,
            "log_level": log.log_level.value if hasattr(log.log_level, 'value') else str(log.log_level),
            "message": log.message,
            "step_name": log.step_name,
            "input_data": log.input_data,
            "output_data": log.output_data,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
    
    return {"logs": log_list, "total": len(log_list)}
