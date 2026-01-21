"""
Model set API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.core.database import get_db
from app.services.model_set_service import ModelSetService
from app.utils.api_decorators import handle_api_errors, handle_not_found

router = APIRouter()


# Request/Response models
class ModelSetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # agent_api, llm_model
    config: Dict[str, Any]
    created_by: Optional[str] = None


class ModelSetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None


class DebugRequest(BaseModel):
    test_data: Dict[str, Any]


@router.get("", response_model=Dict[str, Any])
async def get_all_model_sets(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all model sets with pagination and search"""
    service = ModelSetService(db)
    model_sets, total = service.get_all_model_sets(skip=skip, limit=limit, name=name)
    return {
        "success": True,
        "data": model_sets,
        "total": total,
        "message": "Get model sets successfully"
    }


@router.get("/{model_set_id}", response_model=Dict[str, Any])
@handle_not_found("Model set not found")
async def get_model_set_by_id(
    model_set_id: int,
    db: Session = Depends(get_db)
):
    """Get model set by ID"""
    service = ModelSetService(db)
    model_set = service.get_model_set_by_id(model_set_id)
    return {
        "success": True,
        "data": model_set,
        "message": "Get model set successfully"
    }


@router.post("", response_model=Dict[str, Any])
@handle_api_errors
async def create_model_set(
    data: ModelSetCreate,
    db: Session = Depends(get_db)
):
    """Create a new model set"""
    service = ModelSetService(db)
    result = service.create_model_set(data.dict())
    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('message', 'Failed to create model set')
        )
    return result


@router.put("/{model_set_id}", response_model=Dict[str, Any])
async def update_model_set(
    model_set_id: int,
    data: ModelSetUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing model set"""
    service = ModelSetService(db)
    
    # Only include fields that are provided
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    result = service.update_model_set(model_set_id, update_data)
    
    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('message', 'Failed to update model set')
        )
    
    return result


@router.delete("/{model_set_id}", response_model=Dict[str, Any])
async def delete_model_set(
    model_set_id: int,
    db: Session = Depends(get_db)
):
    """Delete a model set"""
    service = ModelSetService(db)
    result = service.delete_model_set(model_set_id)
    
    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('message', 'Failed to delete model set')
        )
    
    return result


@router.post("/{model_set_id}/debug", response_model=Dict[str, Any])
async def debug_model_set(
    model_set_id: int,
    data: DebugRequest,
    db: Session = Depends(get_db)
):
    """Debug a model set"""
    service = ModelSetService(db)
    result = await service.debug_model_set(model_set_id, data.test_data)
    
    # Always return the result, even if success is False
    # This allows the frontend to display the target API's error response
    # Only raise exception for critical errors (e.g., model set not found, invalid config)
    if not result.get('success'):
        # Check if this is a critical error that should be raised as HTTP exception
        # vs. a target API error that should be returned to the frontend
        error_type = result.get('error_type') or ''
        message = result.get('message', 'Debug failed')
        
        # Critical errors: model set not found, invalid configuration, etc.
        if 'not found' in message.lower() or 'required' in message.lower() or 'invalid' in message.lower():
            raise HTTPException(
                status_code=400,
                detail=message
            )
        # For target API errors, return the result so frontend can display the error response
        # This includes cases where the target API returns HTTP 200 but with error code in body
    
    return result

