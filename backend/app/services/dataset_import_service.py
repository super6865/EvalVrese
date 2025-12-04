"""
Dataset import service
Handles importing data from files into datasets
"""
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.dataset import Dataset, DatasetIOJob, DatasetItem
from app.services.dataset_service import DatasetService
from app.services.file_service import FileService
from app.utils.file_reader import FileReader
from app.utils.dataset_validator import DatasetValidator, ItemErrorGroup, ItemErrorType


class DatasetImportService:
    """Service for importing datasets from files"""
    
    BULK_SIZE = 100  # Process items in batches
    
    def __init__(self, db: Session, file_service: FileService):
        """
        Initialize import service
        
        Args:
            db: Database session
            file_service: File service instance
        """
        self.db = db
        self.file_service = file_service
        self.dataset_service = DatasetService(db)
    
    def create_import_job(
        self,
        dataset_id: int,
        file_path: str,
        file_format: str,
        field_mappings: List[Dict[str, str]],
        overwrite_dataset: bool = False,
        version_id: Optional[int] = None,
        created_by: Optional[str] = None
    ) -> DatasetIOJob:
        """
        Create an import job
        
        Args:
            dataset_id: Target dataset ID
            file_path: Path to the file to import
            file_format: File format ('csv' or 'jsonl')
            field_mappings: List of {source: str, target: str} mappings
            overwrite_dataset: Whether to overwrite existing data
            created_by: User who created the job
            
        Returns:
            Created DatasetIOJob
        """
        # Verify dataset exists
        dataset = self.dataset_service.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Verify field mappings
        schema = self.dataset_service.get_dataset_schema(dataset_id)
        if not schema:
            raise ValueError(f"Dataset {dataset_id} has no schema")
        
        # Get available field keys
        available_fields = {field.get('key') for field in schema.field_definitions if field.get('status') != 'Deleted'}
        target_fields = {mapping.get('target') for mapping in field_mappings}
        
        # Check if all target fields exist
        invalid_fields = target_fields - available_fields
        if invalid_fields:
            raise ValueError(f"Target fields not found in dataset: {', '.join(invalid_fields)}")
        
        # Create job
        job = DatasetIOJob(
            dataset_id=dataset_id,
            job_type="ImportFromFile",
            status="Pending",
            source_file={
                "provider": "LocalFS",
                "path": file_path,
                "format": file_format
            },
            target_dataset_id=dataset_id,
            field_mappings=field_mappings,
            option={"overwrite_dataset": overwrite_dataset, "version_id": version_id},
            processed=0,
            added=0,
            created_by=created_by
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        # Start import in background thread
        thread = threading.Thread(target=self._run_import, args=(job.id,), daemon=True)
        thread.start()
        
        return job
    
    def _run_import(self, job_id: int):
        """
        Run import job in background
        
        Args:
            job_id: Job ID to run
        """
        # Create new session for this thread
        from app.core.database import SessionLocal
        db = SessionLocal()
        
        try:
            job = db.query(DatasetIOJob).filter(DatasetIOJob.id == job_id).first()
            if not job:
                return
            
            # Update status to Running
            job.status = "Running"
            job.started_at = datetime.utcnow()
            db.commit()
            
            # Update dataset status
            dataset = db.query(Dataset).filter(Dataset.id == job.dataset_id).first()
            if dataset:
                dataset.status = "Importing"
                db.commit()
            
            # Clear dataset if overwrite
            if job.option and job.option.get("overwrite_dataset"):
                version_id = job.option.get("version_id") if job.option else None
                self._clear_dataset(db, job.dataset_id, version_id)
            
            # Process import
            try:
                self._process_import(db, job)
                job.status = "Completed"
            except Exception as e:
                job.status = "Failed"
                # Add error to job
                if not job.errors:
                    job.errors = []
                job.errors.append({
                    "type": "InternalError",
                    "summary": str(e),
                    "error_count": 1,
                    "details": [{"message": str(e)}]
                })
            finally:
                job.ended_at = datetime.utcnow()
                if dataset:
                    dataset.status = "Available"
                db.commit()
        
        except Exception as e:
            # Update job status to failed
            try:
                job = db.query(DatasetIOJob).filter(DatasetIOJob.id == job_id).first()
                if job:
                    job.status = "Failed"
                    job.ended_at = datetime.utcnow()
                    if not job.errors:
                        job.errors = []
                    job.errors.append({
                        "type": "InternalError",
                        "summary": str(e),
                        "error_count": 1,
                        "details": [{"message": str(e)}]
                    })
                    db.commit()
            except:
                pass
        finally:
            db.close()
    
    def _process_import(self, db: Session, job: DatasetIOJob):
        """
        Process import job
        
        Args:
            db: Database session
            job: Import job
        """
        file_path = job.source_file.get("path")
        file_format = job.source_file.get("format")
        field_mappings = job.field_mappings or []
        
        # Get version_id from job option
        version_id = None
        if job.option and isinstance(job.option, dict):
            version_id = job.option.get("version_id")
        
        # Build field mapping dictionary: source -> [targets]
        mapping_dict: Dict[str, List[str]] = {}
        for mapping in field_mappings:
            source = mapping.get("source")
            target = mapping.get("target")
            if source and target:
                if source not in mapping_dict:
                    mapping_dict[source] = []
                mapping_dict[source].append(target)
        
        # Open file reader
        reader = FileReader(file_path, file_format)
        reader.open()
        
        # Get dataset schema
        dataset = self.dataset_service.get_dataset(job.dataset_id)
        schema_obj = self.dataset_service.get_dataset_schema(job.dataset_id)
        schema = {"field_definitions": schema_obj.field_definitions} if schema_obj else None
        
        items_batch = []
        processed_count = 0
        added_count = 0
        errors = []
        
        try:
            # Read and process items
            for row_data in reader:
                processed_count += 1
                
                # Convert row to dataset item format
                item_data = self._convert_row_to_item(row_data, mapping_dict, schema)
                
                if item_data:
                    items_batch.append(item_data)
                
                # Process batch when it reaches bulk size
                if len(items_batch) >= self.BULK_SIZE:
                    batch_added, batch_errors = self._save_batch(
                        db, job.dataset_id, items_batch, schema, dataset.spec or {}, version_id
                    )
                    added_count += batch_added
                    errors.extend(batch_errors)
                    items_batch = []
                    
                    # Update job progress
                    self._update_job_progress(db, job, processed_count, added_count, errors)
            
            # Process remaining items
            if items_batch:
                batch_added, batch_errors = self._save_batch(
                    db, job.dataset_id, items_batch, schema, dataset.spec or {}, version_id
                )
                added_count += batch_added
                errors.extend(batch_errors)
            
            # Final progress update
            job.total = processed_count
            job.processed = processed_count
            job.added = added_count
            if errors:
                job.errors = self._group_errors(errors)
            job.updated_at = datetime.utcnow()
            db.commit()
        
        finally:
            reader.close()
    
    def _convert_row_to_item(
        self,
        row_data: Dict[str, Any],
        mapping_dict: Dict[str, List[str]],
        schema: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Convert row data to dataset item format
        
        Args:
            row_data: Raw row data from file
            mapping_dict: Field mapping dictionary
            schema: Dataset schema
            
        Returns:
            Item data in dataset format or None
        """
        field_data_list = []
        
        # Process each source field
        for source_field, value in row_data.items():
            if source_field not in mapping_dict:
                continue  # Skip unmapped fields
            
            targets = mapping_dict[source_field]
            
            # Get field definition for each target
            for target_field in targets:
                field_def = None
                if schema:
                    for fd in schema.get("field_definitions", []):
                        if fd.get("key") == target_field:
                            field_def = fd
                            break
                
                # Create field data
                field_data = {
                    "key": target_field,
                    "name": field_def.get("name", target_field) if field_def else target_field,
                    "content": {
                        "content_type": field_def.get("content_type", "Text") if field_def else "Text",
                        "format": field_def.get("default_display_format", "PlainText") if field_def else "PlainText",
                        "text": str(value) if value is not None else ""
                    }
                }
                
                field_data_list.append(field_data)
        
        if not field_data_list:
            return None
        
        # Create item in dataset format
        return {
            "data_content": {
                "turns": [{
                    "id": 1,
                    "field_data_list": field_data_list
                }]
            }
        }
    
    def _save_batch(
        self,
        db: Session,
        dataset_id: int,
        items: List[Dict[str, Any]],
        schema: Optional[Dict[str, Any]],
        spec: Dict[str, Any],
        version_id: Optional[int] = None
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Save a batch of items
        
        Args:
            db: Database session
            dataset_id: Dataset ID
            items: List of items to save
            schema: Dataset schema
            spec: Dataset spec
            version_id: Version ID to associate items with (None for draft items)
            
        Returns:
            (added_count, errors)
        """
        # Validate items
        error_groups = []
        if schema:
            items_to_validate = [item.get("data_content", {}) for item in items]
            error_groups = DatasetValidator.validate_items(items_to_validate, schema, spec)
        
        # Check for capacity errors
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset and spec.get("max_item_count"):
            current_count = dataset.item_count or 0
            if current_count + len(items) > spec.get("max_item_count"):
                # Capacity exceeded
                max_addable = spec.get("max_item_count") - current_count
                if max_addable > 0:
                    items = items[:max_addable]
                else:
                    error_groups.append({
                        "type": "ExceedDatasetCapacity",
                        "summary": "Dataset capacity exceeded",
                        "error_count": len(items),
                        "details": []
                    })
                    return 0, error_groups
        
        # Create items
        added_count = 0
        for item_data in items:
            try:
                item = DatasetItem(
                    dataset_id=dataset_id,
                    version_id=version_id,  # Associate with version if provided, otherwise None (draft)
                    data_content=item_data.get("data_content", {}),
                )
                db.add(item)
                added_count += 1
            except Exception as e:
                # Log error but continue
                error_groups.append({
                    "type": "InternalError",
                    "summary": str(e),
                    "error_count": 1,
                    "details": [{"message": str(e)}]
                })
        
        db.commit()
        
        # Update dataset item count
        if dataset:
            dataset.item_count = (dataset.item_count or 0) + added_count
            dataset.change_uncommitted = True
            db.commit()
        
        # Convert error groups to simple dict format
        errors = []
        for eg in error_groups:
            if isinstance(eg, ItemErrorGroup):
                errors.append({
                    "type": eg.type.name if hasattr(eg.type, 'name') else str(eg.type),
                    "summary": eg.summary,
                    "error_count": eg.error_count or 0,
                    "details": [d.to_dict() if hasattr(d, 'to_dict') else {"message": str(d)} for d in eg.details]
                })
            else:
                errors.append(eg)
        
        return added_count, errors
    
    def _update_job_progress(
        self,
        db: Session,
        job: DatasetIOJob,
        processed: int,
        added: int,
        errors: List[Dict[str, Any]]
    ):
        """Update job progress"""
        job.processed = processed
        job.added = added
        if errors:
            job.errors = self._group_errors(errors)
        job.updated_at = datetime.utcnow()
        db.commit()
    
    def _group_errors(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group errors by type"""
        error_groups: Dict[str, Dict[str, Any]] = {}
        
        for error in errors:
            error_type = error.get("type", "InternalError")
            if error_type not in error_groups:
                error_groups[error_type] = {
                    "type": error_type,
                    "summary": error.get("summary", ""),
                    "error_count": 0,
                    "details": []
                }
            
            error_groups[error_type]["error_count"] += error.get("error_count", 1)
            error_groups[error_type]["details"].extend(error.get("details", []))
            # Limit details to 10
            if len(error_groups[error_type]["details"]) > 10:
                error_groups[error_type]["details"] = error_groups[error_type]["details"][:10]
        
        return list(error_groups.values())
    
    def _clear_dataset(self, db: Session, dataset_id: int, version_id: Optional[int] = None):
        """Clear items from dataset (by version if specified, otherwise draft items)"""
        query = db.query(DatasetItem).filter(DatasetItem.dataset_id == dataset_id)
        
        if version_id is not None:
            # Delete items for specific version
            query = query.filter(DatasetItem.version_id == version_id)
        else:
            # Delete draft items (version_id is None)
            query = query.filter(DatasetItem.version_id.is_(None))
        
        deleted_count = query.delete(synchronize_session=False)
        
        # Update dataset item count
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            # Recalculate item count based on remaining items
            remaining_count = db.query(DatasetItem).filter(DatasetItem.dataset_id == dataset_id).count()
            dataset.item_count = remaining_count
            dataset.change_uncommitted = False
        
        db.commit()
    
    def get_import_job(self, job_id: int) -> Optional[DatasetIOJob]:
        """Get import job by ID"""
        return self.db.query(DatasetIOJob).filter(DatasetIOJob.id == job_id).first()

