"""
Dataset service - Extended with coze-loop capabilities
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from typing import List, Optional, Dict, Any, Tuple
from app.models.dataset import Dataset, DatasetVersion, DatasetSchema, DatasetItem
from app.utils.dataset_validator import (
    DatasetValidator, ItemErrorGroup, ItemErrorDetail, ItemErrorType
)
from datetime import datetime
import json


class DatasetService:
    def __init__(self, db: Session):
        self.db = db

    # ========== Dataset CRUD ==========
    
    def create_dataset(
        self, 
        name: str, 
        description: Optional[str] = None, 
        created_by: Optional[str] = None,
        field_schemas: Optional[List[Dict[str, Any]]] = None,
        biz_category: Optional[str] = None,
        spec: Optional[Dict[str, Any]] = None,
        features: Optional[Dict[str, Any]] = None
    ) -> Dataset:
        """Create a new dataset with schema support"""
        # Check if name already exists (excluding deleted datasets)
        existing = self.db.query(Dataset).filter(
            Dataset.name == name,
            Dataset.status != "Deleted"
        ).first()
        if existing:
            raise ValueError("已存在对应数据集，请修改名称")
        
        dataset = Dataset(
            name=name,
            description=description,
            created_by=created_by,
            status="Available",
            item_count=0,
            change_uncommitted=False,
            next_version_num=1,
            biz_category=biz_category,
            spec=spec or {},
            features=features or {"editSchema": True, "repeatedData": False, "multiModal": False}
        )
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        
        # Create initial schema if field_schemas provided
        if field_schemas:
            self.create_schema(
                dataset_id=dataset.id,
                name="default",
                field_definitions=field_schemas,
                description="Default schema"
            )
        
        return dataset

    def get_dataset(self, dataset_id: int, include_deleted: bool = False) -> Optional[Dataset]:
        query = self.db.query(Dataset).filter(Dataset.id == dataset_id)
        if not include_deleted:
            query = query.filter(Dataset.status != "Deleted")
        return query.first()

    def batch_get_datasets(
        self, 
        dataset_ids: List[int], 
        include_deleted: bool = False
    ) -> List[Dataset]:
        query = self.db.query(Dataset).filter(Dataset.id.in_(dataset_ids))
        if not include_deleted:
            query = query.filter(Dataset.status != "Deleted")
        return query.all()

    def list_datasets(
        self,
        skip: int = 0,
        limit: int = 100,
        name: Optional[str] = None,
        creators: Optional[List[str]] = None,
        dataset_ids: Optional[List[int]] = None,
        order_by: Optional[str] = None,
        order_asc: bool = True,
        include_deleted: bool = False
    ) -> Tuple[List[Dataset], int]:
        """List datasets with filtering and pagination"""
        query = self.db.query(Dataset)
        
        if not include_deleted:
            query = query.filter(Dataset.status != "Deleted")
        
        if name:
            query = query.filter(Dataset.name.ilike(f"%{name}%"))
        
        if creators:
            query = query.filter(Dataset.created_by.in_(creators))
        
        if dataset_ids:
            query = query.filter(Dataset.id.in_(dataset_ids))
        
        # Ordering
        if order_by:
            if order_by == "created_at":
                query = query.order_by(asc(Dataset.created_at) if order_asc else desc(Dataset.created_at))
            elif order_by == "updated_at":
                query = query.order_by(asc(Dataset.updated_at) if order_asc else desc(Dataset.updated_at))
            elif order_by == "name":
                query = query.order_by(asc(Dataset.name) if order_asc else desc(Dataset.name))
        
        total = query.count()
        datasets = query.offset(skip).limit(limit).all()
        
        return datasets, total

    def update_dataset(
        self, 
        dataset_id: int, 
        name: Optional[str] = None, 
        description: Optional[str] = None
    ) -> Optional[Dataset]:
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            return None
        
        if name is not None:
            # Check if name is already used by another dataset (excluding deleted datasets)
            existing = self.db.query(Dataset).filter(
                Dataset.name == name,
                Dataset.id != dataset_id,
                Dataset.status != "Deleted"
            ).first()
            if existing:
                raise ValueError("已存在对应数据集，请修改名称")
            
            dataset.name = name
        if description is not None:
            dataset.description = description
        dataset.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def delete_dataset(self, dataset_id: int) -> bool:
        """Soft delete dataset (set status to Deleted)"""
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            return False
        
        dataset.status = "Deleted"
        dataset.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    # ========== Schema Management ==========
    
    def create_schema(
        self, 
        dataset_id: int, 
        name: str, 
        field_definitions: List[Dict[str, Any]], 
        description: Optional[str] = None
    ) -> DatasetSchema:
        """Create a dataset schema"""
        schema = DatasetSchema(
            dataset_id=dataset_id,
            name=name,
            description=description,
            field_definitions=field_definitions,
        )
        self.db.add(schema)
        self.db.commit()
        self.db.refresh(schema)
        return schema

    def get_schema(self, schema_id: int) -> Optional[DatasetSchema]:
        """Get schema by ID"""
        return self.db.query(DatasetSchema).filter(DatasetSchema.id == schema_id).first()
    
    def get_dataset_schema(self, dataset_id: int) -> Optional[DatasetSchema]:
        """Get the latest schema for a dataset"""
        return self.db.query(DatasetSchema).filter(
            DatasetSchema.dataset_id == dataset_id
        ).order_by(desc(DatasetSchema.created_at)).first()

    def update_dataset_schema(
        self, 
        dataset_id: int, 
        field_schemas: List[Dict[str, Any]]
    ) -> Optional[DatasetSchema]:
        """Update dataset schema"""
        schema = self.get_dataset_schema(dataset_id)
        if not schema:
            # Create new schema if none exists
            schema = self.create_schema(
                dataset_id=dataset_id,
                name="default",
                field_definitions=field_schemas
            )
        else:
            schema.field_definitions = field_schemas
            schema.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(schema)
        
        return schema

    def validate_schema(self, schema: Dict[str, Any]) -> List[str]:
        """Validate schema structure"""
        errors = []
        field_definitions = schema.get("field_definitions", [])
        
        if not isinstance(field_definitions, list):
            errors.append("field_definitions must be a list")
            return errors
        
        seen_keys = set()
        for idx, field in enumerate(field_definitions):
            if not isinstance(field, dict):
                errors.append(f"Field {idx} must be a dictionary")
                continue
            
            key = field.get("key")
            if not key:
                errors.append(f"Field {idx} missing required 'key'")
            elif key in seen_keys:
                errors.append(f"Duplicate field key: {key}")
            else:
                seen_keys.add(key)
        
        return errors

    # ========== Version Management ==========
    
    def create_version(
        self, 
        dataset_id: int, 
        version: Optional[str] = None,
        schema_id: Optional[int] = None,
        description: Optional[str] = None, 
        created_by: Optional[str] = None
    ) -> DatasetVersion:
        """Create a new dataset version"""
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Auto-generate version if not provided
        if not version:
            version = f"v{dataset.next_version_num}"
        
        # Get schema snapshot
        schema = None
        schema_snapshot = None
        if schema_id:
            schema = self.get_schema(schema_id)
        else:
            schema = self.get_dataset_schema(dataset_id)
        
        if schema:
            schema_snapshot = {
                "id": schema.id,
                "field_definitions": schema.field_definitions
            }
        
        # Count items in current version (draft items)
        item_count = self.db.query(func.count(DatasetItem.id)).filter(
            DatasetItem.dataset_id == dataset_id,
            DatasetItem.version_id.is_(None)  # Draft items
        ).scalar() or 0
        
        dataset_version = DatasetVersion(
            dataset_id=dataset_id,
            version=version,
            schema_id=schema_id,
            description=description,
            created_by=created_by,
            version_num=dataset.next_version_num,
            item_count=item_count,
            evaluation_set_schema=schema_snapshot,
            status="active"
        )
        self.db.add(dataset_version)
        self.db.flush()  # Flush to get the version ID
        
        # Associate draft items to the new version
        if item_count > 0:
            self.db.query(DatasetItem).filter(
                DatasetItem.dataset_id == dataset_id,
                DatasetItem.version_id.is_(None)
            ).update({DatasetItem.version_id: dataset_version.id}, synchronize_session=False)
        
        # Recalculate actual item count after association
        actual_item_count = self.db.query(func.count(DatasetItem.id)).filter(
            DatasetItem.version_id == dataset_version.id
        ).scalar() or 0
        
        dataset_version.item_count = actual_item_count
        
        # Update dataset
        dataset.latest_version = version
        dataset.next_version_num += 1
        dataset.change_uncommitted = False
        
        self.db.commit()
        self.db.refresh(dataset_version)
        return dataset_version

    def recalculate_version_item_count(self, version_id: int) -> int:
        """Recalculate item count for a version based on actual items"""
        count = self.db.query(func.count(DatasetItem.id)).filter(
            DatasetItem.version_id == version_id
        ).scalar() or 0
        
        version = self.db.query(DatasetVersion).filter(DatasetVersion.id == version_id).first()
        if version:
            version.item_count = count
            self.db.commit()
        
        return count

    def get_version(self, version_id: int, include_deleted: bool = False) -> Optional[DatasetVersion]:
        """Get dataset version by ID"""
        query = self.db.query(DatasetVersion).filter(DatasetVersion.id == version_id)
        version = query.first()
        
        if version:
            # Always recalculate item_count to ensure accuracy
            actual_count = self.db.query(func.count(DatasetItem.id)).filter(
                DatasetItem.version_id == version_id
            ).scalar() or 0
            
            if version.item_count != actual_count:
                version.item_count = actual_count
                self.db.commit()
                self.db.refresh(version)
        
        return version

    def list_versions(
        self,
        dataset_id: int,
        skip: int = 0,
        limit: int = 100,
        version_like: Optional[str] = None,
        versions: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        order_asc: bool = False
    ) -> Tuple[List[DatasetVersion], int]:
        """List dataset versions with filtering"""
        query = self.db.query(DatasetVersion).filter(
            DatasetVersion.dataset_id == dataset_id
        )
        
        if version_like:
            query = query.filter(DatasetVersion.version.ilike(f"%{version_like}%"))
        
        if versions:
            query = query.filter(DatasetVersion.version.in_(versions))
        
        # Ordering (default: newest first)
        if order_by == "version_num":
            query = query.order_by(asc(DatasetVersion.version_num) if order_asc else desc(DatasetVersion.version_num))
        else:
            query = query.order_by(desc(DatasetVersion.created_at))
        
        total = query.count()
        version_list = query.offset(skip).limit(limit).all()
        
        # Always recalculate item_count for all versions to ensure accuracy
        for version in version_list:
            actual_count = self.db.query(func.count(DatasetItem.id)).filter(
                DatasetItem.version_id == version.id
            ).scalar() or 0
            
            if version.item_count != actual_count:
                version.item_count = actual_count
                self.db.commit()
        
        return version_list, total

    def batch_get_versions(
        self,
        version_ids: List[int],
        include_deleted: bool = False
    ) -> List[DatasetVersion]:
        """Batch get versions by IDs"""
        query = self.db.query(DatasetVersion).filter(DatasetVersion.id.in_(version_ids))
        return query.all()

    # ========== Item Management ==========
    
    def create_item(
        self, 
        dataset_id: int, 
        version_id: Optional[int],
        data_content: Dict[str, Any], 
        item_key: Optional[str] = None,
        schema_id: Optional[int] = None
    ) -> DatasetItem:
        """Create a dataset item"""
        # If version_id is None, it's a draft item
        item = DatasetItem(
            dataset_id=dataset_id,
            version_id=version_id,
            schema_id=schema_id,
            item_key=item_key,
            data_content=data_content,
        )
        self.db.add(item)
        
        # Update dataset item count if not draft
        if version_id:
            dataset = self.get_dataset(dataset_id)
            if dataset:
                dataset.item_count = (dataset.item_count or 0) + 1
                dataset.change_uncommitted = True
        
        self.db.commit()
        self.db.refresh(item)
        return item

    def batch_create_items(
        self,
        dataset_id: int,
        version_id: Optional[int],
        items: List[Dict[str, Any]],
        skip_invalid_items: bool = False,
        allow_partial_add: bool = False,
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[DatasetItem], List[ItemErrorGroup], Dict[int, int]]:
        """Batch create dataset items with validation"""
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Get schema for validation
        if not schema:
            schema_obj = self.get_dataset_schema(dataset_id)
            if schema_obj:
                schema = {"field_definitions": schema_obj.field_definitions}
        
        # Validate items
        spec = dataset.spec or {}
        error_groups = []
        if schema:
            # Extract data_content for validation (validator expects {turns: [...]} format)
            items_to_validate = [item.get("data_content", {}) for item in items]
            error_groups = DatasetValidator.validate_items(items_to_validate, schema, spec)
        
        # Check capacity
        if spec.get("max_item_count"):
            can_add, max_addable = DatasetValidator.check_capacity(
                dataset.item_count or 0,
                len(items),
                spec.get("max_item_count")
            )
            if not can_add:
                if not allow_partial_add:
                    capacity_error = ItemErrorGroup(
                        error_type=ItemErrorType.ExceedDatasetCapacity,
                        summary=f"Dataset capacity exceeded. Can add at most {max_addable} items.",
                        error_count=len(items) - max_addable,
                        details=[]
                    )
                    error_groups.append(capacity_error)
                    if not skip_invalid_items:
                        return [], error_groups, {}
                else:
                    items = items[:max_addable]
        
        # Filter out invalid items if skip_invalid_items
        valid_items = []
        if skip_invalid_items and error_groups:
            # Simple validation: skip items with errors
            error_indices = set()
            for error_group in error_groups:
                for detail in error_group.details:
                    if detail.index is not None:
                        error_indices.add(detail.index)
            
            for idx, item in enumerate(items):
                if idx not in error_indices:
                    valid_items.append(item)
        else:
            if error_groups and not skip_invalid_items:
                return [], error_groups, {}
            valid_items = items
        
        # Create items
        created_items = []
        id_map = {}  # Map from input index to created item ID
        for idx, item_data in enumerate(valid_items):
            item = DatasetItem(
                dataset_id=dataset_id,
                version_id=version_id,
                item_key=item_data.get("item_key"),
                data_content=item_data.get("data_content", {}),
            )
            self.db.add(item)
            created_items.append((idx, item))
        
        self.db.commit()
        
        # Build id_map and update item counts
        for idx, item in created_items:
            self.db.refresh(item)
            id_map[idx] = item.id
        
        # Update dataset and version item count
        if version_id:
            dataset.item_count = (dataset.item_count or 0) + len(created_items)
            dataset.change_uncommitted = True
            
            # Update version item count
            version = self.get_version(version_id)
            if version:
                version.item_count = (version.item_count or 0) + len(created_items)
            
            self.db.commit()
        
        return [item for _, item in created_items], error_groups, id_map

    def batch_update_items(
        self,
        dataset_id: int,
        items: List[Dict[str, Any]],
        skip_invalid_items: bool = False,
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[DatasetItem], List[ItemErrorGroup]]:
        """Batch update dataset items"""
        # Get schema for validation
        if not schema:
            schema_obj = self.get_dataset_schema(dataset_id)
            if schema_obj:
                schema = {"field_definitions": schema_obj.field_definitions}
        
        # Validate items
        error_groups = []
        if schema:
            items_to_validate = [item.get("data_content", {}) for item in items]
            error_groups = DatasetValidator.validate_items(items_to_validate, schema)
        
        if error_groups and not skip_invalid_items:
            return [], error_groups
        
        # Update items
        updated_items = []
        for item_data in items:
            item_id = item_data.get("id")
            if not item_id:
                continue
            
            item = self.get_item(item_id)
            if item and item.dataset_id == dataset_id:
                if "data_content" in item_data:
                    item.data_content = item_data["data_content"]
                item.updated_at = datetime.utcnow()
                updated_items.append(item)
        
        self.db.commit()
        for item in updated_items:
            self.db.refresh(item)
        
        return updated_items, error_groups

    def update_item(
        self, 
        item_id: int, 
        data_content: Optional[Dict[str, Any]] = None,
        turns: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[DatasetItem]:
        """Update dataset item (supports Turn structure)"""
        item = self.get_item(item_id)
        if not item:
            return None
        
        if turns is not None:
            item.data_content = {"turns": turns}
        elif data_content is not None:
            item.data_content = data_content
        
        item.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(item)
        return item

    def batch_delete_items(
        self,
        dataset_id: int,
        item_ids: List[int]
    ) -> int:
        """Batch delete dataset items"""
        # Get version_ids of items to be deleted before deletion
        items_to_delete = self.db.query(DatasetItem).filter(
            DatasetItem.id.in_(item_ids),
            DatasetItem.dataset_id == dataset_id
        ).all()
        
        version_item_counts = {}  # Map version_id to count
        for item in items_to_delete:
            if item.version_id:
                version_item_counts[item.version_id] = version_item_counts.get(item.version_id, 0) + 1
        
        # Delete related experiment_results first to avoid foreign key constraint errors
        # experiment_results has a foreign key to dataset_items
        from app.models.experiment import ExperimentResult
        self.db.query(ExperimentResult).filter(
            ExperimentResult.dataset_item_id.in_(item_ids)
        ).delete(synchronize_session=False)
        
        # Delete items
        deleted_count = self.db.query(DatasetItem).filter(
            DatasetItem.id.in_(item_ids),
            DatasetItem.dataset_id == dataset_id
        ).delete(synchronize_session=False)
        
        # Update dataset item count
        dataset = self.get_dataset(dataset_id)
        if dataset:
            dataset.item_count = max(0, (dataset.item_count or 0) - deleted_count)
            dataset.change_uncommitted = True
        
        # Update version item counts
        for version_id, count in version_item_counts.items():
            version = self.get_version(version_id)
            if version:
                version.item_count = max(0, (version.item_count or 0) - count)
        
        self.db.commit()
        return deleted_count

    def delete_item(self, item_id: int) -> bool:
        """Delete dataset item"""
        item = self.get_item(item_id)
        if not item:
            return False
        
        dataset_id = item.dataset_id
        version_id = item.version_id
        
        # Delete related experiment_results first to avoid foreign key constraint errors
        # experiment_results has a foreign key to dataset_items
        from app.models.experiment import ExperimentResult
        self.db.query(ExperimentResult).filter(
            ExperimentResult.dataset_item_id == item_id
        ).delete()
        
        self.db.delete(item)
        
        # Update dataset item count
        dataset = self.get_dataset(dataset_id)
        if dataset:
            dataset.item_count = max(0, (dataset.item_count or 0) - 1)
            dataset.change_uncommitted = True
        
        # Update version item count
        if version_id:
            version = self.get_version(version_id)
            if version:
                version.item_count = max(0, (version.item_count or 0) - 1)
        
        self.db.commit()
        return True

    def get_item(self, item_id: int) -> Optional[DatasetItem]:
        """Get dataset item by ID"""
        return self.db.query(DatasetItem).filter(DatasetItem.id == item_id).first()

    def list_items(
        self,
        dataset_id: int,
        version_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        item_ids_not_in: Optional[List[int]] = None,
        order_by: Optional[str] = None,
        order_asc: bool = True
    ) -> Tuple[List[DatasetItem], int]:
        """List items in a dataset (optionally by version)"""
        query = self.db.query(DatasetItem).filter(
            DatasetItem.dataset_id == dataset_id
        )
        
        if version_id is not None:
            query = query.filter(DatasetItem.version_id == version_id)
        else:
            # Draft items (version_id is None)
            query = query.filter(DatasetItem.version_id.is_(None))
        
        if item_ids_not_in:
            query = query.filter(~DatasetItem.id.in_(item_ids_not_in))
        
        # Ordering
        if order_by == "created_at":
            query = query.order_by(asc(DatasetItem.created_at) if order_asc else desc(DatasetItem.created_at))
        elif order_by == "updated_at":
            query = query.order_by(asc(DatasetItem.updated_at) if order_asc else desc(DatasetItem.updated_at))
        else:
            query = query.order_by(desc(DatasetItem.id))
        
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        
        return items, total

    def batch_get_items(
        self,
        dataset_id: int,
        item_ids: List[int],
        version_id: Optional[int] = None
    ) -> List[DatasetItem]:
        """Batch get items by IDs"""
        query = self.db.query(DatasetItem).filter(
            DatasetItem.id.in_(item_ids),
            DatasetItem.dataset_id == dataset_id
        )
        
        if version_id is not None:
            query = query.filter(DatasetItem.version_id == version_id)
        
        return query.all()

    def clear_draft_items(self, dataset_id: int) -> int:
        """Clear draft items (items without version_id)"""
        deleted_count = self.db.query(DatasetItem).filter(
            DatasetItem.dataset_id == dataset_id,
            DatasetItem.version_id.is_(None)
        ).delete(synchronize_session=False)
        
        dataset = self.get_dataset(dataset_id)
        if dataset:
            dataset.change_uncommitted = False
        
        self.db.commit()
        return deleted_count
