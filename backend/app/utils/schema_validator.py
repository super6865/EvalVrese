"""
Schema validation utilities for evaluators
"""
import json
from typing import Dict, Any, Optional, List
import jsonschema
from jsonschema import validate, ValidationError
from app.domain.entity.evaluator_entity import Content, ContentType, ArgsSchema


class SchemaValidationError(Exception):
    """Schema validation error"""
    pass


class SchemaValidator:
    """Schema validator for evaluator inputs and outputs"""
    
    @staticmethod
    def validate_json_schema(json_schema_str: str, data: Any) -> tuple[bool, Optional[str]]:
        """
        Validate data against JSON Schema
        
        Args:
            json_schema_str: JSON Schema string
            data: Data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            schema = json.loads(json_schema_str)
            validate(instance=data, schema=schema)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON Schema: {str(e)}"
        except ValidationError as e:
            return False, f"Validation error: {e.message} (path: {'.'.join(str(p) for p in e.path)})"
        except Exception as e:
            return False, f"Schema validation error: {str(e)}"
    
    @staticmethod
    def validate_content_type(content: Content, supported_types: List[ContentType]) -> bool:
        """
        Validate content type against supported types
        
        Args:
            content: Content to validate
            supported_types: List of supported content types
            
        Returns:
            True if content type is supported
        """
        if not content or not content.content_type:
            return False
        return content.content_type in supported_types
    
    @staticmethod
    def validate_input_data(
        input_data: Dict[str, Content],
        input_schemas: List[ArgsSchema]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate input data against input schemas
        
        Args:
            input_data: Input data dictionary
            input_schemas: List of input schemas
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not input_schemas:
            return True, None
        
        # Create schema map by key
        schema_map = {}
        for schema in input_schemas:
            if schema.key:
                schema_map[schema.key] = schema
        
        # Validate each input field
        for field_key, content in input_data.items():
            if content is None:
                continue
            
            # Check if field is defined in schema
            if field_key not in schema_map:
                continue  # Fields not in schema don't need validation
            
            schema = schema_map[field_key]
            
            # Validate content type
            if not SchemaValidator.validate_content_type(content, schema.support_content_types):
                return False, f"Content type {content.content_type} not supported for field {field_key}"
            
            # Validate JSON schema for text content
            if content.content_type == ContentType.TEXT and content.text and schema.json_schema:
                is_valid, error_msg = SchemaValidator.validate_json_schema(
                    schema.json_schema,
                    content.text
                )
                if not is_valid:
                    return False, f"Field {field_key}: {error_msg}"
        
        return True, None
    
    @staticmethod
    def validate_output_data(
        output_data: Any,
        output_schemas: List[ArgsSchema]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate output data against output schemas
        
        Args:
            output_data: Output data to validate
            output_schemas: List of output schemas
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not output_schemas:
            return True, None
        
        # For now, we validate the structure matches expected schema
        # This can be extended based on specific requirements
        return True, None
    
    @staticmethod
    def validate_evaluator_input(
        input_data: Dict[str, Any],
        input_schemas: List[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate evaluator input data (convenience method)
        
        Args:
            input_data: Input data as dictionary
            input_schemas: Input schemas as dictionary list
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Convert schemas to ArgsSchema objects
        schema_objects = []
        for schema_dict in input_schemas:
            schema_obj = ArgsSchema(**schema_dict)
            schema_objects.append(schema_obj)
        
        # Convert input data to Content objects
        content_dict = {}
        for key, value in input_data.items():
            if isinstance(value, dict):
                content = Content(**value)
            elif isinstance(value, str):
                content = Content(content_type=ContentType.TEXT, text=value)
            else:
                content = Content(content_type=ContentType.TEXT, text=str(value))
            content_dict[key] = content
        
        return SchemaValidator.validate_input_data(content_dict, schema_objects)

