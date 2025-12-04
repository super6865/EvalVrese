"""
Evaluator API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from app.core.database import get_db
from app.services.evaluator_service import EvaluatorService
from app.services.evaluator_record_service import EvaluatorRecordService
from app.utils.api_decorators import handle_api_errors, handle_not_found
from app.models.evaluator import (
    EvaluatorType,
    EvaluatorVersionStatus,
    EvaluatorBoxType,
)
from app.domain.entity.evaluator_entity import EvaluatorInputData

router = APIRouter()


# Request/Response models
class EvaluatorContentCreate(BaseModel):
    """Evaluator content for creation"""
    prompt_evaluator: Optional[Dict[str, Any]] = None
    code_evaluator: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"  # Allow extra fields


class CurrentVersionCreate(BaseModel):
    """Current version data for evaluator creation"""
    version: Optional[str] = None  # Default to 'v1.0' if not provided
    evaluator_content: EvaluatorContentCreate
    input_schemas: Optional[List[Dict[str, Any]]] = None
    output_schemas: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow extra fields


class EvaluatorCreate(BaseModel):
    name: str
    evaluator_type: EvaluatorType
    description: Optional[str] = None
    builtin: bool = False
    box_type: Optional[EvaluatorBoxType] = None
    evaluator_info: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, Any]] = None
    current_version: Optional[CurrentVersionCreate] = None  # New field for one-step creation


class EvaluatorUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    box_type: Optional[EvaluatorBoxType] = None
    evaluator_info: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, Any]] = None


class VersionCreate(BaseModel):
    version: str
    content: Optional[Dict[str, Any]] = None  # Legacy field
    prompt_content: Optional[Dict[str, Any]] = None
    code_content: Optional[Dict[str, Any]] = None
    input_schemas: Optional[List[Dict[str, Any]]] = None
    output_schemas: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None
    status: EvaluatorVersionStatus = EvaluatorVersionStatus.DRAFT


class RunEvaluatorRequest(BaseModel):
    input_data: Dict[str, Any]
    experiment_id: Optional[int] = None
    experiment_run_id: Optional[int] = None
    dataset_item_id: Optional[int] = None
    turn_id: Optional[int] = None
    disable_tracing: bool = False


class DebugRequest(BaseModel):
    input_data: Dict[str, Any]


class BatchDebugRequest(BaseModel):
    evaluator_type: str  # 'prompt' or 'code'
    evaluator_content: Dict[str, Any]  # { code_evaluator: {...} } or { prompt_evaluator: {...} }
    input_data: List[Dict[str, Any]]  # List of EvaluatorInputData
    workspace_id: Optional[str] = None


# Evaluator CRUD
@router.get("")
async def list_evaluators(skip: int = 0, limit: int = 100, name: Optional[str] = None, db: Session = Depends(get_db)):
    """List all evaluators with optional name filter"""
    service = EvaluatorService(db)
    evaluators, total = service.list_evaluators(skip=skip, limit=limit, name=name)
    return {"evaluators": evaluators, "total": total}


@router.post("")
async def create_evaluator(data: EvaluatorCreate, db: Session = Depends(get_db)):
    """Create a new evaluator (with optional version in one step)"""
    service = EvaluatorService(db)
    
    # If current_version is provided, create evaluator and version in one transaction
    if data.current_version:
        evaluator = service.create_evaluator_with_version(
            name=data.name,
            evaluator_type=data.evaluator_type,
            description=data.description,
            builtin=data.builtin,
            box_type=data.box_type,
            evaluator_info=data.evaluator_info,
            tags=data.tags,
            current_version=data.current_version,
        )
    else:
        # Legacy: create evaluator only
        evaluator = service.create_evaluator(
            name=data.name,
            evaluator_type=data.evaluator_type,
            description=data.description,
            builtin=data.builtin,
            box_type=data.box_type,
            evaluator_info=data.evaluator_info,
            tags=data.tags,
        )
    return evaluator


@router.get("/{evaluator_id}")
@handle_not_found("Evaluator not found")
async def get_evaluator(evaluator_id: int, db: Session = Depends(get_db)):
    """Get evaluator by ID"""
    service = EvaluatorService(db)
    return service.get_evaluator(evaluator_id)


@router.put("/{evaluator_id}")
@handle_api_errors
@handle_not_found("Evaluator not found")
async def update_evaluator(evaluator_id: int, data: EvaluatorUpdate, db: Session = Depends(get_db)):
    """Update evaluator"""
    service = EvaluatorService(db)
    evaluator = service.update_evaluator(
        evaluator_id=evaluator_id,
        name=data.name,
        description=data.description,
    )
    # Update additional fields
    if data.box_type is not None:
        evaluator.box_type = data.box_type
    if data.evaluator_info is not None:
        evaluator.evaluator_info = data.evaluator_info
    if data.tags is not None:
        evaluator.tags = data.tags
    
    db.commit()
    db.refresh(evaluator)
    return evaluator


@router.delete("/{evaluator_id}")
@handle_api_errors
async def delete_evaluator(evaluator_id: int, db: Session = Depends(get_db)):
    """Delete evaluator"""
    service = EvaluatorService(db)
    success = service.delete_evaluator(evaluator_id)
    if not success:
        raise HTTPException(status_code=404, detail="Evaluator not found")
    return {"message": "Evaluator deleted successfully"}


# Version management
@router.post("/{evaluator_id}/versions")
async def create_version(evaluator_id: int, data: VersionCreate, db: Session = Depends(get_db)):
    """Create a new evaluator version"""
    service = EvaluatorService(db)
    # Verify evaluator exists
    evaluator = service.get_evaluator(evaluator_id)
    if not evaluator:
        raise HTTPException(status_code=404, detail="Evaluator not found")
    
    try:
        version = service.create_version(
            evaluator_id=evaluator_id,
            version=data.version,
            content=data.content,
            prompt_content=data.prompt_content,
            code_content=data.code_content,
            input_schemas=data.input_schemas,
            output_schemas=data.output_schemas,
            description=data.description,
            status=data.status,
        )
        return version
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{evaluator_id}/versions")
async def list_versions(evaluator_id: int, db: Session = Depends(get_db)):
    """List all versions of an evaluator"""
    service = EvaluatorService(db)
    versions = service.list_versions(evaluator_id)
    return {"versions": versions}


@router.get("/versions/{version_id}")
async def get_version(version_id: int, db: Session = Depends(get_db)):
    """Get evaluator version by ID"""
    service = EvaluatorService(db)
    version = service.get_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


# Version management
@router.post("/versions/{version_id}/submit")
async def submit_version(version_id: int, description: Optional[str] = None, db: Session = Depends(get_db)):
    """Submit an evaluator version"""
    service = EvaluatorService(db)
    try:
        version = service.submit_version(version_id, description)
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        return version
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Run evaluator
@router.post("/versions/{version_id}/run")
async def run_evaluator(version_id: int, data: RunEvaluatorRequest, db: Session = Depends(get_db)):
    """Run an evaluator version"""
    service = EvaluatorService(db)
    record_service = EvaluatorRecordService(db)
    
    try:
        # Convert input data
        input_data = EvaluatorInputData(**data.input_data)
        
        # Run evaluator
        output_data = await service.run_evaluator(
            version_id=version_id,
            input_data=input_data,
            experiment_id=data.experiment_id,
            experiment_run_id=data.experiment_run_id,
            dataset_item_id=data.dataset_item_id,
            turn_id=data.turn_id,
            disable_tracing=data.disable_tracing,
        )
        
        # Create record
        from app.models.evaluator_record import EvaluatorRunStatus
        status = EvaluatorRunStatus.SUCCESS if output_data.evaluator_result else EvaluatorRunStatus.FAIL
        record = record_service.create_record(
            evaluator_version_id=version_id,
            input_data=data.input_data,
            output_data=output_data.dict() if hasattr(output_data, 'dict') else output_data,
            status=status,
            experiment_id=data.experiment_id,
            experiment_run_id=data.experiment_run_id,
            dataset_item_id=data.dataset_item_id,
            turn_id=data.turn_id,
        )
        
        return {
            "record_id": record.id,
            "output_data": output_data.dict() if hasattr(output_data, 'dict') else output_data,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation error: {str(e)}")


# Debug/Test evaluator
@router.post("/versions/{version_id}/debug")
async def debug_evaluator(version_id: int, data: DebugRequest, db: Session = Depends(get_db)):
    """Debug/test an evaluator version"""
    service = EvaluatorService(db)
    try:
        # Convert input data
        input_data = EvaluatorInputData(**data.input_data)
        
        result = await service.debug_evaluator(
            version_id=version_id,
            input_data=input_data,
        )
        return result.dict() if hasattr(result, 'dict') else result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation error: {str(e)}")


# Batch debug evaluator
@router.post("/batch_debug")
async def batch_debug_evaluator(data: BatchDebugRequest, db: Session = Depends(get_db)):
    """Batch debug evaluator without creating a version"""
    service = EvaluatorService(db)
    try:
        # Convert input data list
        input_data_list = [EvaluatorInputData(**item) for item in data.input_data]
        
        # Call batch debug service
        results = await service.batch_debug_evaluator(
            evaluator_type=data.evaluator_type,
            evaluator_content=data.evaluator_content,
            input_data_list=input_data_list,
        )
        
        # Convert results to dict format
        output_data = []
        for result in results:
            if hasattr(result, 'dict'):
                output_data.append(result.dict())
            else:
                output_data.append(result)
        
        return {"evaluator_output_data": output_data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch evaluation error: {str(e)}")
