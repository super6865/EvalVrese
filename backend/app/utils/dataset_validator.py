"""
Dataset validation utilities
"""
from typing import List, Dict, Any, Optional, Tuple
from enum import IntEnum


class ItemErrorType(IntEnum):
    """Item error types"""
    MismatchSchema = 1
    EmptyData = 2
    ExceedMaxItemSize = 3
    ExceedDatasetCapacity = 4
    MalformedFile = 5
    IllegalContent = 6
    MissingRequiredField = 7
    ExceedMaxNestedDepth = 8
    TransformItemFailed = 9
    ExceedMaxImageCount = 10
    ExceedMaxImageSize = 11
    GetImageFailed = 12
    IllegalExtension = 13
    InternalError = 100
    UploadImageFailed = 103


class ItemErrorDetail:
    """Item error detail"""
    def __init__(self, message: Optional[str] = None, index: Optional[int] = None,
                 start_index: Optional[int] = None, end_index: Optional[int] = None):
        self.message = message
        self.index = index
        self.start_index = start_index
        self.end_index = end_index

    def to_dict(self):
        return {
            "message": self.message,
            "index": self.index,
            "start_index": self.start_index,
            "end_index": self.end_index
        }


class ItemErrorGroup:
    """Item error group"""
    def __init__(self, error_type: ItemErrorType, summary: Optional[str] = None,
                 error_count: Optional[int] = None, details: Optional[List[ItemErrorDetail]] = None):
        self.type = error_type
        self.summary = summary
        self.error_count = error_count
        self.details = details or []

    def to_dict(self):
        return {
            "type": self.type.value,
            "type_name": self.type.name,
            "summary": self.summary,
            "error_count": self.error_count,
            "details": [detail.to_dict() for detail in self.details]
        }


class DatasetValidator:
    """Dataset validation utilities"""
    
    @staticmethod
    def validate_item_size(item: Dict[str, Any], max_size: Optional[int] = None) -> Optional[ItemErrorDetail]:
        """Validate item size"""
        if max_size is None:
            return None
        
        import json
        item_size = len(json.dumps(item).encode('utf-8'))
        if item_size > max_size:
            return ItemErrorDetail(
                message=f"Item size {item_size} exceeds maximum {max_size}",
                index=None
            )
        return None
    
    @staticmethod
    def validate_nested_depth(data: Any, max_depth: int = 10, current_depth: int = 0) -> Tuple[bool, int]:
        """Validate nested depth of data structure"""
        if current_depth > max_depth:
            return False, current_depth
        
        if isinstance(data, dict):
            max_found = current_depth
            for value in data.values():
                valid, depth = DatasetValidator.validate_nested_depth(value, max_depth, current_depth + 1)
                if not valid:
                    return False, depth
                max_found = max(max_found, depth)
            return True, max_found
        elif isinstance(data, list):
            max_found = current_depth
            for item in data:
                valid, depth = DatasetValidator.validate_nested_depth(item, max_depth, current_depth + 1)
                if not valid:
                    return False, depth
                max_found = max(max_found, depth)
            return True, max_found
        else:
            return True, current_depth
    
    @staticmethod
    def validate_required_fields(item: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Validate required fields in item against schema"""
        missing_fields = []
        field_schemas = schema.get("field_definitions", [])
        
        for field_schema in field_schemas:
            if field_schema.get("is_required", False):
                field_key = field_schema.get("key")
                if field_key and not DatasetValidator._has_field_in_turns(item, field_key):
                    missing_fields.append(field_key)
        
        return missing_fields
    
    @staticmethod
    def _has_field_in_turns(item: Dict[str, Any], field_key: str) -> bool:
        """Check if field exists in item turns"""
        turns = item.get("turns", [])
        for turn in turns:
            field_data_list = turn.get("field_data_list", [])
            for field_data in field_data_list:
                if field_data.get("key") == field_key:
                    return True
        return False
    
    @staticmethod
    def validate_item_against_schema(item: Dict[str, Any], schema: Dict[str, Any]) -> List[ItemErrorDetail]:
        """Validate item against schema"""
        errors = []
        
        # Check required fields
        missing_fields = DatasetValidator.validate_required_fields(item, schema)
        for field_key in missing_fields:
            errors.append(ItemErrorDetail(
                message=f"Missing required field: {field_key}",
                index=None
            ))
        
        # Check nested depth
        spec = schema.get("spec", {})
        max_depth = spec.get("max_item_data_nested_depth")
        if max_depth:
            valid, depth = DatasetValidator.validate_nested_depth(item, max_depth)
            if not valid:
                errors.append(ItemErrorDetail(
                    message=f"Item nested depth {depth} exceeds maximum {max_depth}",
                    index=None
                ))
        
        return errors
    
    @staticmethod
    def validate_items(items: List[Dict[str, Any]], schema: Dict[str, Any],
                       spec: Optional[Dict[str, Any]] = None) -> List[ItemErrorGroup]:
        """Validate multiple items and return error groups"""
        error_groups: Dict[ItemErrorType, ItemErrorGroup] = {}
        
        for idx, item in enumerate(items):
            # Check empty data
            turns = item.get("turns") if item else None
            if not item or not turns or not isinstance(turns, list) or len(turns) == 0:
                error_type = ItemErrorType.EmptyData
                if error_type not in error_groups:
                    error_groups[error_type] = ItemErrorGroup(
                        error_type=error_type,
                        summary="Empty data items",
                        error_count=0,
                        details=[]
                    )
                error_groups[error_type].error_count += 1
                if len(error_groups[error_type].details) < 5:
                    error_groups[error_type].details.append(
                        ItemErrorDetail(message="Item is empty or has no turns", index=idx)
                    )
                continue
            
            # Check if turns have field_data_list
            has_data = False
            for turn in turns:
                if turn and isinstance(turn, dict):
                    field_data_list = turn.get("field_data_list")
                    if field_data_list and isinstance(field_data_list, list) and len(field_data_list) > 0:
                        has_data = True
                        break
            
            if not has_data:
                error_type = ItemErrorType.EmptyData
                if error_type not in error_groups:
                    error_groups[error_type] = ItemErrorGroup(
                        error_type=error_type,
                        summary="Empty data items",
                        error_count=0,
                        details=[]
                    )
                error_groups[error_type].error_count += 1
                if len(error_groups[error_type].details) < 5:
                    error_groups[error_type].details.append(
                        ItemErrorDetail(message="Item has no field data", index=idx)
                    )
                continue
            
            # Validate against schema
            schema_errors = DatasetValidator.validate_item_against_schema(item, schema)
            if schema_errors:
                error_type = ItemErrorType.MismatchSchema
                if error_type not in error_groups:
                    error_groups[error_type] = ItemErrorGroup(
                        error_type=error_type,
                        summary="Schema mismatch",
                        error_count=0,
                        details=[]
                    )
                error_groups[error_type].error_count += len(schema_errors)
                for error in schema_errors[:5]:  # Limit to 5 details
                    error.index = idx
                    error_groups[error_type].details.append(error)
            
            # Validate item size
            if spec:
                max_size = spec.get("max_item_size")
                if max_size:
                    size_error = DatasetValidator.validate_item_size(item, max_size)
                    if size_error:
                        error_type = ItemErrorType.ExceedMaxItemSize
                        if error_type not in error_groups:
                            error_groups[error_type] = ItemErrorGroup(
                                error_type=error_type,
                                summary="Item size exceeds limit",
                                error_count=0,
                                details=[]
                            )
                        error_groups[error_type].error_count += 1
                        size_error.index = idx
                        if len(error_groups[error_type].details) < 5:
                            error_groups[error_type].details.append(size_error)
        
        return list(error_groups.values())
    
    @staticmethod
    def check_capacity(current_count: int, new_items_count: int, max_count: Optional[int] = None) -> Tuple[bool, Optional[int]]:
        """Check if dataset has capacity for new items"""
        if max_count is None:
            return True, None
        
        total_count = current_count + new_items_count
        if total_count > max_count:
            return False, max_count - current_count  # Return how many can be added
        return True, None

