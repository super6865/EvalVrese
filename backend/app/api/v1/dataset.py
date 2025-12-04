"""
Dataset API endpoints - Extended with coze-loop capabilities
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from app.core.database import get_db
from app.services.dataset_service import DatasetService
from app.services.file_service import FileService
from app.services.dataset_import_service import DatasetImportService
from app.utils.api_decorators import handle_api_errors, handle_not_found

router = APIRouter()


# ========== Request/Response Models ==========

class DatasetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    status: str
    item_count: int
    change_uncommitted: bool
    latest_version: Optional[str] = None
    next_version_num: int
    biz_category: Optional[str] = None
    spec: Optional[Dict[str, Any]] = None
    features: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    field_schemas: Optional[List[Dict[str, Any]]] = None
    biz_category: Optional[str] = None
    spec: Optional[Dict[str, Any]] = None
    features: Optional[Dict[str, Any]] = None


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DatasetListRequest(BaseModel):
    name: Optional[str] = None
    creators: Optional[List[str]] = None
    dataset_ids: Optional[List[int]] = None
    page_number: Optional[int] = 1
    page_size: Optional[int] = 100
    order_by: Optional[str] = None
    order_asc: Optional[bool] = True
    include_deleted: Optional[bool] = False


class SchemaUpdateRequest(BaseModel):
    field_schemas: List[Dict[str, Any]]


class VersionCreateRequest(BaseModel):
    version: Optional[str] = None
    schema_id: Optional[int] = None
    description: Optional[str] = None


class VersionListRequest(BaseModel):
    version_like: Optional[str] = None
    versions: Optional[List[str]] = None
    page_number: Optional[int] = 1
    page_size: Optional[int] = 100
    order_by: Optional[str] = None
    order_asc: Optional[bool] = False


class ItemCreate(BaseModel):
    data_content: Dict[str, Any]
    item_key: Optional[str] = None


class ItemUpdate(BaseModel):
    data_content: Optional[Dict[str, Any]] = None
    turns: Optional[List[Dict[str, Any]]] = None


class BatchItemCreate(BaseModel):
    items: List[ItemCreate]
    skip_invalid_items: Optional[bool] = False
    allow_partial_add: Optional[bool] = False


class BatchItemUpdate(BaseModel):
    items: List[Dict[str, Any]]  # Each item should have 'id' and 'data_content'
    skip_invalid_items: Optional[bool] = False


class BatchItemDelete(BaseModel):
    item_ids: List[int]


class ItemListRequest(BaseModel):
    version_id: Optional[int] = None
    page_number: Optional[int] = 1
    page_size: Optional[int] = 100
    item_ids_not_in: Optional[List[int]] = None
    order_by: Optional[str] = None
    order_asc: Optional[bool] = True


class BatchItemGetRequest(BaseModel):
    item_ids: List[int]
    version_id: Optional[int] = None


# ========== Dataset CRUD ==========

@router.post("/", response_model=DatasetResponse)
@handle_api_errors
async def create_dataset(data: DatasetCreate, db: Session = Depends(get_db)):
    """Create a new dataset"""
    service = DatasetService(db)
    dataset = service.create_dataset(
        name=data.name,
        description=data.description,
        field_schemas=data.field_schemas,
        biz_category=data.biz_category,
        spec=data.spec,
        features=data.features
    )
    return dataset


@router.get("/{dataset_id}", response_model=DatasetResponse)
@handle_not_found("Dataset not found")
async def get_dataset(
    dataset_id: int,
    include_deleted: bool = Query(False, alias="include_deleted"),
    db: Session = Depends(get_db)
):
    """Get dataset by ID"""
    service = DatasetService(db)
    return service.get_dataset(dataset_id, include_deleted=include_deleted)


@router.post("/batch_get")
async def batch_get_datasets(
    dataset_ids: List[int],
    include_deleted: bool = Query(False, alias="include_deleted"),
    db: Session = Depends(get_db)
):
    """Batch get datasets by IDs"""
    service = DatasetService(db)
    datasets = service.batch_get_datasets(dataset_ids, include_deleted=include_deleted)
    return {"datasets": datasets}


@router.post("/list")
async def list_datasets(data: DatasetListRequest, db: Session = Depends(get_db)):
    """List datasets with filtering and pagination"""
    service = DatasetService(db)
    skip = (data.page_number - 1) * data.page_size if data.page_number else 0
    limit = data.page_size or 100
    
    datasets, total = service.list_datasets(
        skip=skip,
        limit=limit,
        name=data.name,
        creators=data.creators,
        dataset_ids=data.dataset_ids,
        order_by=data.order_by,
        order_asc=data.order_asc if data.order_asc is not None else True,
        include_deleted=data.include_deleted or False
    )
    
    return {
        "datasets": datasets,
        "total": total,
        "page_number": data.page_number or 1,
        "page_size": data.page_size or 100
    }


@router.put("/{dataset_id}")
@handle_api_errors
@handle_not_found("Dataset not found")
async def update_dataset(
    dataset_id: int,
    data: DatasetUpdate,
    db: Session = Depends(get_db)
):
    """Update dataset"""
    service = DatasetService(db)
    return service.update_dataset(
        dataset_id=dataset_id,
        name=data.name,
        description=data.description
    )


@router.delete("/{dataset_id}")
@handle_api_errors
async def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Delete dataset (soft delete)"""
    service = DatasetService(db)
    success = service.delete_dataset(dataset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"message": "Dataset deleted successfully"}


# ========== Schema Management ==========

@router.patch("/{dataset_id}/schema")
async def update_dataset_schema(
    dataset_id: int,
    data: SchemaUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update dataset schema"""
    service = DatasetService(db)
    # Verify dataset exists
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Validate schema
    schema_dict = {"field_definitions": data.field_schemas}
    errors = service.validate_schema(schema_dict)
    if errors:
        raise HTTPException(status_code=400, detail=f"Schema validation errors: {errors}")
    
    schema = service.update_dataset_schema(dataset_id, data.field_schemas)
    return schema


@router.get("/{dataset_id}/schema")
@handle_not_found("Schema not found")
async def get_dataset_schema(dataset_id: int, db: Session = Depends(get_db)):
    """Get dataset schema"""
    service = DatasetService(db)
    return service.get_dataset_schema(dataset_id)


# ========== Version Management ==========

@router.post("/{dataset_id}/versions")
@handle_api_errors
async def create_version(
    dataset_id: int,
    data: VersionCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new dataset version"""
    service = DatasetService(db)
    return service.create_version(
        dataset_id=dataset_id,
        version=data.version,
        schema_id=data.schema_id,
        description=data.description
    )


@router.get("/{dataset_id}/versions/{version_id}")
async def get_version(
    dataset_id: int,
    version_id: int,
    include_deleted: bool = Query(False, alias="include_deleted"),
    db: Session = Depends(get_db)
):
    """Get dataset version by ID"""
    service = DatasetService(db)
    version = service.get_version(version_id, include_deleted=include_deleted)
    if not version or version.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Get associated dataset
    dataset = service.get_dataset(dataset_id)
    return {
        "version": version,
        "dataset": dataset
    }


@router.post("/{dataset_id}/versions/list")
async def list_versions(
    dataset_id: int,
    data: VersionListRequest,
    db: Session = Depends(get_db)
):
    """List dataset versions with filtering"""
    service = DatasetService(db)
    skip = (data.page_number - 1) * data.page_size if data.page_number else 0
    limit = data.page_size or 100
    
    versions, total = service.list_versions(
        dataset_id=dataset_id,
        skip=skip,
        limit=limit,
        version_like=data.version_like,
        versions=data.versions,
        order_by=data.order_by,
        order_asc=data.order_asc if data.order_asc is not None else False
    )
    
    return {
        "versions": versions,
        "total": total,
        "page_number": data.page_number or 1,
        "page_size": data.page_size or 100
    }


@router.post("/versions/batch_get")
async def batch_get_versions(
    version_ids: List[int],
    include_deleted: bool = Query(False, alias="include_deleted"),
    db: Session = Depends(get_db)
):
    """Batch get versions by IDs"""
    service = DatasetService(db)
    versions = service.batch_get_versions(version_ids, include_deleted=include_deleted)
    
    # Get associated datasets
    dataset_ids = list(set([v.dataset_id for v in versions]))
    datasets = service.batch_get_datasets(dataset_ids)
    dataset_map = {d.id: d for d in datasets}
    
    result = []
    for version in versions:
        result.append({
            "version": version,
            "dataset": dataset_map.get(version.dataset_id)
        })
    
    return {"versioned_datasets": result}


# ========== Item Management ==========

@router.post("/{dataset_id}/items/batch_create")
async def batch_create_items(
    dataset_id: int,
    data: BatchItemCreate,
    version_id: Optional[int] = Query(None, alias="version_id"),
    db: Session = Depends(get_db)
):
    """Batch create dataset items"""
    service = DatasetService(db)
    # Verify dataset exists
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Prepare items data
    items_data = [
        {
            "data_content": item.data_content,
            "item_key": item.item_key
        }
        for item in data.items
    ]
    
    try:
        items, error_groups, id_map = service.batch_create_items(
            dataset_id=dataset_id,
            version_id=version_id,
            items=items_data,
            skip_invalid_items=data.skip_invalid_items or False,
            allow_partial_add=data.allow_partial_add or False
        )
        
        return {
            "items": items,
            "added_items": id_map,
            "errors": [eg.to_dict() for eg in error_groups],
            "count": len(items)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{dataset_id}/items/batch_update")
async def batch_update_items(
    dataset_id: int,
    data: BatchItemUpdate,
    db: Session = Depends(get_db)
):
    """Batch update dataset items"""
    service = DatasetService(db)
    # Verify dataset exists
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    items, error_groups = service.batch_update_items(
        dataset_id=dataset_id,
        items=data.items,
        skip_invalid_items=data.skip_invalid_items or False
    )
    
    return {
        "items": items,
        "errors": [eg.to_dict() for eg in error_groups],
        "count": len(items)
    }


@router.put("/{dataset_id}/items/{item_id}")
async def update_item(
    dataset_id: int,
    item_id: int,
    data: ItemUpdate,
    db: Session = Depends(get_db)
):
    """Update dataset item"""
    service = DatasetService(db)
    # Verify item belongs to dataset
    item = service.get_item(item_id)
    if not item or item.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Item not found")
    
    updated_item = service.update_item(
        item_id=item_id,
        data_content=data.data_content,
        turns=data.turns
    )
    if not updated_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated_item


@router.post("/{dataset_id}/items/batch_delete")
async def batch_delete_items(
    dataset_id: int,
    data: BatchItemDelete,
    db: Session = Depends(get_db)
):
    """Batch delete dataset items"""
    service = DatasetService(db)
    deleted_count = service.batch_delete_items(dataset_id, data.item_ids)
    return {
        "message": f"Deleted {deleted_count} items",
        "deleted_count": deleted_count
    }


@router.post("/{dataset_id}/items/list")
async def list_items(
    dataset_id: int,
    data: ItemListRequest,
    db: Session = Depends(get_db)
):
    """List items in a dataset"""
    service = DatasetService(db)
    skip = (data.page_number - 1) * data.page_size if data.page_number else 0
    limit = data.page_size or 100
    
    items, total = service.list_items(
        dataset_id=dataset_id,
        version_id=data.version_id,
        skip=skip,
        limit=limit,
        item_ids_not_in=data.item_ids_not_in,
        order_by=data.order_by,
        order_asc=data.order_asc if data.order_asc is not None else True
    )
    
    return {
        "items": items,
        "total": total,
        "page_number": data.page_number or 1,
        "page_size": data.page_size or 100
    }


@router.post("/{dataset_id}/items/batch_get")
async def batch_get_items(
    dataset_id: int,
    data: BatchItemGetRequest,
    db: Session = Depends(get_db)
):
    """Batch get items by IDs"""
    service = DatasetService(db)
    items = service.batch_get_items(
        dataset_id=dataset_id,
        item_ids=data.item_ids,
        version_id=data.version_id
    )
    return {"items": items}


@router.post("/{dataset_id}/items/clear")
async def clear_draft_items(dataset_id: int, db: Session = Depends(get_db)):
    """Clear draft items (items without version_id)"""
    service = DatasetService(db)
    deleted_count = service.clear_draft_items(dataset_id)
    return {
        "message": f"Cleared {deleted_count} draft items",
        "deleted_count": deleted_count
    }


@router.get("/items/{item_id}")
async def get_item(item_id: int, db: Session = Depends(get_db)):
    """Get dataset item by ID"""
    service = DatasetService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/items/{item_id}")
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Delete dataset item"""
    service = DatasetService(db)
    success = service.delete_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}


# ========== Import/Export ==========

class FieldMapping(BaseModel):
    source: str
    target: str


class ImportDatasetRequest(BaseModel):
    file_path: str
    file_format: str  # csv, jsonl
    field_mappings: List[FieldMapping]
    overwrite_dataset: Optional[bool] = False
    version_id: Optional[int] = None


@router.post("/{dataset_id}/upload")
async def upload_file(
    dataset_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload file for dataset import"""
    # Verify dataset exists
    service = DatasetService(db)
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Upload file
    file_service = FileService()
    try:
        file_path, file_uri = file_service.save_file(file, dataset_id=dataset_id)
        
        # Get file format
        file_format = file_service.get_file_format(file.filename)
        if not file_format:
            raise HTTPException(status_code=400, detail="Unable to determine file format")
        
        # For CSV, XLSX, XLS, and ZIP files, read headers
        headers = []
        if file_format in ['csv', 'xlsx', 'xls', 'zip']:
            from app.utils.file_reader import FileReader
            import logging
            logger = logging.getLogger(__name__)
            try:
                reader = FileReader(file_path, file_format)
                reader.open()
                headers = reader.get_fields()
                reader.close()
            except Exception as e:
                logger.warning(f"Failed to read headers from {file_path}: {str(e)}")
                # Return empty headers, let user configure manually
        
        return {
            "file_path": file_path,
            "file_uri": file_uri,
            "file_format": file_format,
            "headers": headers,
            "filename": file.filename
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/{dataset_id}/import")
async def import_dataset(
    dataset_id: int,
    data: ImportDatasetRequest,
    db: Session = Depends(get_db)
):
    """Import data from file into dataset"""
    # Verify dataset exists
    service = DatasetService(db)
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Verify file exists - file_path is absolute path from upload endpoint
    file_path = Path(data.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {data.file_path}")
    
    file_service = FileService()
    
    # Create import job
    import_service = DatasetImportService(db, file_service)
    try:
        # Convert field mappings
        field_mappings = [{"source": m.source, "target": m.target} for m in data.field_mappings]
        
        job = import_service.create_import_job(
            dataset_id=dataset_id,
            file_path=data.file_path,
            file_format=data.file_format,
            field_mappings=field_mappings,
            overwrite_dataset=data.overwrite_dataset or False,
            version_id=data.version_id
        )
        
        return {
            "job_id": job.id,
            "status": job.status,
            "message": "Import job created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/io_jobs/{job_id}")
async def get_import_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get import job status"""
    from app.models.dataset import DatasetIOJob
    
    job = db.query(DatasetIOJob).filter(DatasetIOJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "dataset_id": job.dataset_id,
        "job_type": job.job_type,
        "status": job.status,
        "total": job.total,
        "processed": job.processed,
        "added": job.added,
        "errors": job.errors,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None
    }


@router.get("/{dataset_id}/io_jobs")
async def list_import_jobs(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """List import jobs for a dataset"""
    from app.models.dataset import DatasetIOJob
    
    jobs = db.query(DatasetIOJob).filter(
        DatasetIOJob.dataset_id == dataset_id
    ).order_by(DatasetIOJob.created_at.desc()).limit(50).all()
    
    return {
        "jobs": [{
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "total": job.total,
            "processed": job.processed,
            "added": job.added,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None
        } for job in jobs]
    }
