"""
Dataset export service
"""
import csv
import io
import os
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.dataset import Dataset, DatasetVersion, DatasetItem, DatasetSchema


class DatasetExportService:
    """Service for exporting dataset items to CSV"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def export_dataset_items_csv(
        self,
        dataset_id: int,
        version_id: Optional[int] = None
    ) -> Tuple[str, str]:
        """
        Export dataset items to CSV file
        
        Args:
            dataset_id: Dataset ID
            version_id: Optional version ID (if None, exports draft items)
        
        Returns:
            Tuple of (file_path, file_name)
        """
        # Get dataset
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Get version info if version_id is provided
        version = None
        if version_id is not None:
            version = self.db.query(DatasetVersion).filter(
                DatasetVersion.id == version_id,
                DatasetVersion.dataset_id == dataset_id
            ).first()
            if not version:
                raise ValueError(f"Version {version_id} not found for dataset {dataset_id}")
        
        # Get schema
        schema = self.db.query(DatasetSchema).filter(
            DatasetSchema.dataset_id == dataset_id
        ).order_by(DatasetSchema.created_at.desc()).first()
        
        field_schemas = []
        if schema and schema.field_definitions:
            field_schemas = schema.field_definitions
        elif version and version.evaluation_set_schema:
            # Fallback to version schema
            eval_schema = version.evaluation_set_schema
            if isinstance(eval_schema, dict) and 'field_definitions' in eval_schema:
                field_schemas = eval_schema['field_definitions']
        
        # Get all items for the version (no pagination)
        query = self.db.query(DatasetItem).filter(
            DatasetItem.dataset_id == dataset_id
        )
        
        if version_id is not None:
            query = query.filter(DatasetItem.version_id == version_id)
        else:
            # Draft items (version_id is None)
            query = query.filter(DatasetItem.version_id.is_(None))
        
        items = query.all()
        
        if not items:
            raise ValueError("No items to export")
        
        # Build CSV data
        csv_data = self._build_csv_data(items, field_schemas)
        
        # Create CSV file
        file_path, file_name = self._create_csv_file(dataset, version, csv_data)
        
        return file_path, file_name
    
    def _build_csv_data(
        self,
        items: List[DatasetItem],
        field_schemas: List[Dict[str, Any]]
    ) -> List[List[str]]:
        """Build CSV data from items"""
        if not items:
            return []
        
        # Build header from field schemas
        # Use field keys as column names, with fallback to field names
        header = ["ID", "Item Key"]
        
        # Create a map of field keys to field schemas for quick lookup
        field_schema_map = {}
        for schema in field_schemas:
            key = schema.get('key', '')
            if key:
                field_schema_map[key] = schema
        
        # Add field columns based on schemas
        field_keys = []
        for schema in field_schemas:
            key = schema.get('key', '')
            if key and not schema.get('hidden', False):
                field_keys.append(key)
                field_name = schema.get('name', key)
                header.append(field_name)
        
        # If no schemas, try to infer from first item
        if not field_keys and items:
            first_item = items[0]
            if first_item.data_content and 'turns' in first_item.data_content:
                turns = first_item.data_content.get('turns', [])
                if turns and len(turns) > 0:
                    first_turn = turns[0]
                    field_data_list = first_turn.get('field_data_list', [])
                    for field_data in field_data_list:
                        key = field_data.get('key', '')
                        if key and key not in field_keys:
                            field_keys.append(key)
                            field_name = field_data.get('name', key)
                            header.append(field_name)
        
        # Build rows
        rows = []
        for item in items:
            row = [
                str(item.id),
                item.item_key or ""
            ]
            
            # Extract field values from turns
            field_values = {}
            if item.data_content and 'turns' in item.data_content:
                turns = item.data_content.get('turns', [])
                # For CSV, we'll use the first turn's data
                # If there are multiple turns, they would need special handling
                if turns and len(turns) > 0:
                    first_turn = turns[0]
                    field_data_list = first_turn.get('field_data_list', [])
                    for field_data in field_data_list:
                        key = field_data.get('key', '')
                        if key:
                            content = field_data.get('content', {})
                            value = self._extract_field_value(content)
                            field_values[key] = value
            
            # Add field values in schema order
            for key in field_keys:
                value = field_values.get(key, "")
                row.append(str(value) if value is not None else "")
            
            rows.append(row)
        
        return [header] + rows
    
    def _extract_field_value(self, content: Dict[str, Any]) -> str:
        """Extract text value from field content"""
        if not content:
            return ""
        
        content_type = content.get('content_type', 'Text')
        
        if content_type == 'Text':
            return content.get('text', '')
        elif content_type == 'Image':
            image = content.get('image', {})
            if isinstance(image, dict):
                # Return URL if available, otherwise name
                return image.get('url', '') or image.get('uri', '') or image.get('name', '')
            return str(image) if image else ""
        elif content_type == 'Audio':
            audio = content.get('audio', {})
            if isinstance(audio, dict):
                return audio.get('url', '')
            return str(audio) if audio else ""
        elif content_type == 'MultiPart':
            multi_part = content.get('multi_part', [])
            if isinstance(multi_part, list):
                # Combine all parts
                parts = []
                for part in multi_part:
                    if isinstance(part, dict):
                        part_value = self._extract_field_value(part)
                        if part_value:
                            parts.append(part_value)
                return " | ".join(parts)
            return str(multi_part) if multi_part else ""
        else:
            # Fallback: try to get text or convert to string
            return content.get('text', '') or str(content)
    
    def _create_csv_file(
        self,
        dataset: Dataset,
        version: Optional[DatasetVersion],
        csv_data: List[List[str]]
    ) -> Tuple[str, str]:
        """Create CSV file from data"""
        # Generate file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = dataset.name or f"dataset_{dataset.id}"
        
        if version:
            version_str = version.version or f"v{version.version_num or 'unknown'}"
            file_name = f"{dataset_name}_{version_str}_{timestamp}.csv"
        else:
            file_name = f"{dataset_name}_draft_{timestamp}.csv"
        
        # Sanitize filename (remove invalid characters)
        file_name = "".join(c for c in file_name if c.isalnum() or c in (' ', '-', '_', '.')).strip()
        
        # Create exports directory in uploads folder (similar to experiment exports)
        base_dir = Path(__file__).parent.parent.parent  # Go up to project root
        exports_dir = base_dir / "uploads" / "dataset_exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = exports_dir / file_name
        absolute_path = str(file_path.absolute())
        
        # Write CSV file with UTF-8 BOM (for Excel compatibility)
        with open(absolute_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            for row in csv_data:
                writer.writerow(row)
        
        return absolute_path, file_name

