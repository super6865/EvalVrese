"""
Model configuration API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.core.database import get_db
from app.services.model_config_service import ModelConfigService
from app.utils.api_decorators import handle_api_errors, handle_not_found

router = APIRouter()


# Request/Response models
class ModelConfigCreate(BaseModel):
    config_name: str
    model_type: str
    model_version: str
    api_key: str
    api_base: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_enabled: Optional[bool] = False
    created_by: Optional[str] = None


class ModelConfigUpdate(BaseModel):
    config_name: Optional[str] = None
    model_type: Optional[str] = None
    model_version: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_enabled: Optional[bool] = None
    created_by: Optional[str] = None


class ToggleEnabledRequest(BaseModel):
    enabled: bool


@router.get("", response_model=Dict[str, Any])
async def get_all_configs(
    include_sensitive: bool = False,
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all model configurations with pagination and search"""
    service = ModelConfigService(db)
    configs, total = service.get_all_configs(include_sensitive=include_sensitive, skip=skip, limit=limit, name=name)
    return {
        "success": True,
        "data": configs,
        "total": total,
        "message": "Get configurations successfully"
    }


@router.get("/{config_id}", response_model=Dict[str, Any])
@handle_not_found("Configuration not found")
async def get_config_by_id(
    config_id: int,
    include_sensitive: bool = False,
    db: Session = Depends(get_db)
):
    """Get model configuration by ID"""
    service = ModelConfigService(db)
    config = service.get_config_by_id(config_id, include_sensitive=include_sensitive)
    return {
        "success": True,
        "data": config,
        "message": "Get configuration successfully"
    }


@router.post("", response_model=Dict[str, Any])
async def create_config(
    data: ModelConfigCreate,
    db: Session = Depends(get_db)
):
    """Create a new model configuration"""
    service = ModelConfigService(db)
    result = service.create_config(data.dict())
    
    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('message', 'Failed to create configuration')
        )
    
    return result


@router.put("/{config_id}", response_model=Dict[str, Any])
async def update_config(
    config_id: int,
    data: ModelConfigUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing model configuration"""
    service = ModelConfigService(db)
    
    # Only include fields that are provided
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    result = service.update_config(config_id, update_data)
    
    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('message', 'Failed to update configuration')
        )
    
    return result


@router.delete("/{config_id}", response_model=Dict[str, Any])
async def delete_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """Delete a model configuration"""
    service = ModelConfigService(db)
    result = service.delete_config(config_id)
    
    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('message', 'Failed to delete configuration')
        )
    
    return result


@router.put("/{config_id}/toggle-enabled", response_model=Dict[str, Any])
async def toggle_enabled(
    config_id: int,
    data: ToggleEnabledRequest,
    db: Session = Depends(get_db)
):
    """Toggle the enabled status of a model configuration"""
    service = ModelConfigService(db)
    result = service.toggle_enabled(config_id, data.enabled)
    
    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('message', 'Failed to toggle configuration status')
        )
    
    return result

