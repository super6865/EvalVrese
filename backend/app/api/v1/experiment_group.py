"""
Experiment Group API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.core.database import get_db
from app.services.experiment_group_service import ExperimentGroupService
from app.utils.api_decorators import handle_api_errors, handle_not_found

router = APIRouter()


# Request/Response models
class ExperimentGroupCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None
    description: Optional[str] = None


class ExperimentGroupUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None


class ExperimentGroupResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    description: Optional[str] = None
    created_at: str
    updated_at: str
    children: Optional[List['ExperimentGroupResponse']] = None

    model_config = ConfigDict(from_attributes=True)


# Fix forward reference
ExperimentGroupResponse.model_rebuild()


@router.get("")
@handle_api_errors
async def list_groups(db: Session = Depends(get_db)):
    """List all groups as a flat list"""
    service = ExperimentGroupService(db)
    groups = service.list_groups()
    return {
        "groups": [
            {
                "id": g.id,
                "name": g.name,
                "parent_id": g.parent_id,
                "description": g.description,
                "created_at": g.created_at.isoformat() if g.created_at else None,
                "updated_at": g.updated_at.isoformat() if g.updated_at else None,
            }
            for g in groups
        ]
    }


@router.get("/tree")
@handle_api_errors
async def get_groups_tree(db: Session = Depends(get_db)):
    """Get all groups as a tree structure"""
    service = ExperimentGroupService(db)
    tree = service.get_tree()
    return {"groups": tree}


@router.post("")
@handle_api_errors
async def create_group(data: ExperimentGroupCreate, db: Session = Depends(get_db)):
    """Create a new experiment group"""
    service = ExperimentGroupService(db)
    try:
        group = service.create_group(
            name=data.name,
            parent_id=data.parent_id,
            description=data.description
        )
        return {
            "id": group.id,
            "name": group.name,
            "parent_id": group.parent_id,
            "description": group.description,
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "updated_at": group.updated_at.isoformat() if group.updated_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{group_id}")
@handle_not_found("Group not found")
@handle_api_errors
async def get_group(group_id: int, db: Session = Depends(get_db)):
    """Get a group by ID"""
    service = ExperimentGroupService(db)
    group = service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return {
        "id": group.id,
        "name": group.name,
        "parent_id": group.parent_id,
        "description": group.description,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None,
    }


@router.put("/{group_id}")
@handle_not_found("Group not found")
@handle_api_errors
async def update_group(group_id: int, data: ExperimentGroupUpdate, db: Session = Depends(get_db)):
    """Update a group"""
    service = ExperimentGroupService(db)
    try:
        group = service.update_group(
            group_id=group_id,
            name=data.name,
            parent_id=data.parent_id,
            description=data.description
        )
        return {
            "id": group.id,
            "name": group.name,
            "parent_id": group.parent_id,
            "description": group.description,
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "updated_at": group.updated_at.isoformat() if group.updated_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{group_id}")
@handle_not_found("Group not found")
@handle_api_errors
async def delete_group(group_id: int, db: Session = Depends(get_db)):
    """Delete a group"""
    service = ExperimentGroupService(db)
    try:
        success = service.delete_group(group_id)
        if not success:
            raise HTTPException(status_code=404, detail="Group not found")
        return {"message": "Group deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

