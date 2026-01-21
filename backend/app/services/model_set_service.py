"""
Model set service
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.model_set import ModelSet
from app.utils.crypto import encrypt_api_key, decrypt_api_key, mask_api_key
import logging
import json
import httpx
from autogen import ConversableAgent
import asyncio

logger = logging.getLogger(__name__)


class ModelSetService:
    """Service for managing model sets"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_model_sets(self, skip: int = 0, limit: int = 100, name: Optional[str] = None) -> tuple[List[Dict[str, Any]], int]:
        """
        Get all model sets with pagination and search
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            name: Optional search term for name (partial match)
        
        Returns:
            Tuple of (list of model sets, total count)
        """
        # Build query with optional name filter
        query = self.db.query(ModelSet)
        if name:
            query = query.filter(ModelSet.name.ilike(f'%{name}%'))
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        model_sets = query.order_by(ModelSet.id.asc()).offset(skip).limit(limit).all()
        
        result = []
        for model_set in model_sets:
            result.append(self._model_set_to_dict(model_set))
        
        return result, total
    
    def get_model_set_by_id(self, model_set_id: int) -> Optional[Dict[str, Any]]:
        """
        Get model set by ID
        
        Args:
            model_set_id: Model set ID
            
        Returns:
            Model set dictionary or None
        """
        model_set = self.db.query(ModelSet).filter(ModelSet.id == model_set_id).first()
        
        if not model_set:
            return None
        
        return self._model_set_to_dict(model_set)
    
    def create_model_set(self, model_set_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new model set
        
        Args:
            model_set_data: Model set data dictionary
            
        Returns:
            Result dictionary with success status and message
        """
        # Validate required fields
        validation_errors = self.validate_model_set(model_set_data)
        if validation_errors:
            return {
                'success': False,
                'message': 'Model set validation failed',
                'errors': validation_errors
            }
        
        # Check if name already exists
        existing = self.db.query(ModelSet).filter(
            ModelSet.name == model_set_data['name']
        ).first()
        
        if existing:
            return {
                'success': False,
                'message': f'Model set name "{model_set_data["name"]}" already exists'
            }
        
        try:
            # Encrypt API key in config if present
            config = model_set_data['config'].copy() if model_set_data.get('config') else {}
            if model_set_data['type'] == 'llm_model' and 'api_key' in config and config['api_key']:
                config['api_key'] = encrypt_api_key(config['api_key'])
            
            model_set = ModelSet(
                name=model_set_data['name'],
                description=model_set_data.get('description'),
                type=model_set_data['type'],
                config=config,
                created_by=model_set_data.get('created_by'),
            )
            
            self.db.add(model_set)
            self.db.commit()
            self.db.refresh(model_set)
            
            logger.info(f"Model set created: {model_set.name}")
            return {
                'success': True,
                'message': 'Model set created successfully',
                'data': self._model_set_to_dict(model_set)
            }
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create model set: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to create model set: {str(e)}'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create model set: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to create model set: {str(e)}'
            }
    
    def update_model_set(self, model_set_id: int, model_set_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing model set
        
        Args:
            model_set_id: Model set ID
            model_set_data: Model set data dictionary
            
        Returns:
            Result dictionary with success status and message
        """
        model_set = self.db.query(ModelSet).filter(ModelSet.id == model_set_id).first()
        
        if not model_set:
            return {
                'success': False,
                'message': 'Model set not found'
            }
        
        # Validate required fields
        validation_errors = self.validate_model_set(model_set_data, exclude_id=model_set_id)
        if validation_errors:
            return {
                'success': False,
                'message': 'Model set validation failed',
                'errors': validation_errors
            }
        
        # Check if name already exists (excluding current model set)
        if 'name' in model_set_data:
            existing = self.db.query(ModelSet).filter(
                ModelSet.name == model_set_data['name'],
                ModelSet.id != model_set_id
            ).first()
            
            if existing:
                return {
                    'success': False,
                    'message': f'Model set name "{model_set_data["name"]}" already exists'
                }
        
        try:
            # Update fields
            if 'name' in model_set_data:
                model_set.name = model_set_data['name']
            if 'description' in model_set_data:
                model_set.description = model_set_data.get('description')
            if 'type' in model_set_data:
                model_set.type = model_set_data['type']
            if 'config' in model_set_data:
                # Encrypt API key in config if present
                config = model_set_data['config'].copy()
                if model_set_data.get('type', model_set.type) == 'llm_model':
                    # If api_key is provided and not empty, encrypt it
                    # Otherwise, preserve the existing encrypted value
                    if 'api_key' in config and config['api_key']:
                        config['api_key'] = encrypt_api_key(config['api_key'])
                    elif 'api_key' not in config and model_set.config and 'api_key' in model_set.config:
                        # Preserve existing encrypted API key if not provided
                        config['api_key'] = model_set.config['api_key']
                model_set.config = config
            if 'created_by' in model_set_data:
                model_set.created_by = model_set_data.get('created_by')
            
            self.db.commit()
            self.db.refresh(model_set)
            
            logger.info(f"Model set updated: {model_set.name}")
            return {
                'success': True,
                'message': 'Model set updated successfully',
                'data': self._model_set_to_dict(model_set)
            }
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to update model set: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to update model set: {str(e)}'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update model set: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to update model set: {str(e)}'
            }
    
    def delete_model_set(self, model_set_id: int) -> Dict[str, Any]:
        """
        Delete a model set
        
        Args:
            model_set_id: Model set ID
            
        Returns:
            Result dictionary with success status and message
        """
        model_set = self.db.query(ModelSet).filter(ModelSet.id == model_set_id).first()
        
        if not model_set:
            return {
                'success': False,
                'message': 'Model set not found'
            }
        
        try:
            model_set_name = model_set.name
            self.db.delete(model_set)
            self.db.commit()
            
            logger.info(f"Model set deleted: {model_set_name}")
            return {
                'success': True,
                'message': f'Model set "{model_set_name}" deleted successfully'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete model set: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to delete model set: {str(e)}'
            }
    
    async def debug_model_set(self, model_set_id: int, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Debug a model set by calling it with test data
        
        Args:
            model_set_id: Model set ID
            test_data: Test data dictionary
            
        Returns:
            Debug result dictionary
        """
        model_set = self.db.query(ModelSet).filter(ModelSet.id == model_set_id).first()
        
        if not model_set:
            return {
                'success': False,
                'message': 'Model set not found'
            }
        
        try:
            if model_set.type == 'agent_api':
                return await self._debug_agent_api(model_set.config, test_data)
            elif model_set.type == 'llm_model':
                return await self._debug_model(model_set.config, test_data)
            else:
                return {
                    'success': False,
                    'message': f'Unknown model set type: {model_set.type}'
                }
        except Exception as e:
            logger.error(f"Failed to debug model set: {str(e)}")
            return {
                'success': False,
                'message': f'Debug failed: {str(e)}',
                'error': str(e)
            }
    
    async def _debug_agent_api(self, config: Dict[str, Any], test_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Debug agent API by making HTTP request
        
        Args:
            config: Agent API configuration
            test_data: Test data
            
        Returns:
            Debug result
        """
        api_url = config.get('api_url')
        api_method = config.get('api_method', 'POST')
        api_headers = config.get('api_headers', {})
        api_body_template = config.get('api_body_template', {})
        input_mapping = config.get('input_mapping', {})
        
        logger.info(f"[DebugAgentAPI] Starting debug with URL: {api_url}, method: {api_method}")
        logger.info(f"[DebugAgentAPI] Test data keys: {list(test_data.keys())}")
        logger.info(f"[DebugAgentAPI] Input mapping: {json.dumps(input_mapping, ensure_ascii=False)}")
        logger.info(f"[DebugAgentAPI] API body template: {json.dumps(api_body_template, ensure_ascii=False, indent=2)}")
        
        if not api_url:
            logger.error("[DebugAgentAPI] API URL is required but not provided")
            return {
                'success': False,
                'message': 'API URL is required'
            }
        
        # Map test data to API body using input_mapping
        mapped_data = {}
        if input_mapping:
            for api_key, test_key in input_mapping.items():
                if test_key in test_data:
                    mapped_data[api_key] = test_data[test_key]
        else:
            # If no mapping, use test_data directly
            mapped_data = test_data
        
        # Build request body from template using JSON string replacement
        # This approach handles nested structures correctly (e.g., param_map.content)
        if api_body_template:
            logger.info(f"[DebugAgentAPI] Processing api_body_template with mapped_data keys: {list(mapped_data.keys())}")
            # Convert template to JSON string
            body_str = json.dumps(api_body_template, ensure_ascii=False)
            logger.info(f"[DebugAgentAPI] Template JSON string (before replacement): {body_str}")
            logger.info(f"[DebugAgentAPI] Mapped data values: {json.dumps({k: str(v)[:100] + '...' if len(str(v)) > 100 else str(v) for k, v in mapped_data.items()}, ensure_ascii=False)}")
            
            # Replace placeholders with actual values
            # The placeholder is inside a JSON string value, so we need to replace it carefully
            # For example: "content": "{content}" should become "content": "actual value"
            # json.dumps() adds quotes for strings, but since the placeholder is already inside quotes,
            # we need to remove the outer quotes from json.dumps() result for strings
            # 
            # IMPORTANT: We need to detect if the placeholder is inside quotes or not
            # - If inside quotes: escape the string and remove outer quotes from json.dumps() result
            # - If not inside quotes: use json.dumps() result directly (for JSON objects/values)
            def _find_placeholder_context(json_str: str, placeholder: str) -> tuple:
                """
                Find placeholder in JSON string and determine if it's inside quotes.
                Returns: (is_inside_quotes, position)
                """
                pos = json_str.find(placeholder)
                if pos == -1:
                    return False, -1
                
                # Check if we're inside a string value (between quotes)
                # Count unescaped quotes before the placeholder
                quote_count = 0
                escaped = False
                for i in range(pos):
                    char = json_str[i]
                    if escaped:
                        escaped = False
                        continue
                    if char == '\\':
                        escaped = True
                        continue
                    if char == '"':
                        quote_count += 1
                
                # If odd number of quotes before placeholder, we're inside a string
                is_inside_quotes = (quote_count % 2 == 1)
                return is_inside_quotes, pos
            
            for key, value in mapped_data.items():
                placeholder = f"{{{key}}}"
                if placeholder in body_str:
                    logger.info(f"[DebugAgentAPI] Replacing placeholder {placeholder} with value type: {type(value).__name__}")
                    
                    # Find all occurrences of the placeholder
                    placeholder_positions = []
                    start = 0
                    while True:
                        pos = body_str.find(placeholder, start)
                        if pos == -1:
                            break
                        placeholder_positions.append(pos)
                        start = pos + 1
                    
                    # Replace from end to start to maintain positions
                    for pos in reversed(placeholder_positions):
                        # Check context for this occurrence
                        is_inside_quotes, _ = _find_placeholder_context(body_str[:pos + len(placeholder)], placeholder)
                        
                        if isinstance(value, str):
                            if is_inside_quotes:
                                # Placeholder is inside quotes - escape the string and remove outer quotes
                                escaped_json = json.dumps(value, ensure_ascii=False)
                                # Remove outer quotes: "value" -> value (but properly escaped)
                                if len(escaped_json) >= 2 and escaped_json[0] == '"' and escaped_json[-1] == '"':
                                    escaped_value = escaped_json[1:-1]
                                else:
                                    escaped_value = escaped_json
                                logger.info(f"[DebugAgentAPI] Placeholder in quotes - escaped value (first 200 chars): {escaped_value[:200]}...")
                            else:
                                # Placeholder is NOT in quotes - treat as JSON value
                                # If value looks like JSON, try to parse and use as object
                                value_stripped = value.strip()
                                if (value_stripped.startswith('{') and value_stripped.endswith('}')) or \
                                   (value_stripped.startswith('[') and value_stripped.endswith(']')):
                                    try:
                                        # Value is JSON - parse it and use json.dumps() to get proper JSON representation
                                        parsed_value = json.loads(value)
                                        escaped_value = json.dumps(parsed_value, ensure_ascii=False)
                                        logger.info(f"[DebugAgentAPI] Placeholder not in quotes - parsed JSON value")
                                    except (json.JSONDecodeError, ValueError):
                                        # Not valid JSON, escape as string
                                        escaped_json = json.dumps(value, ensure_ascii=False)
                                        escaped_value = escaped_json
                                        logger.info(f"[DebugAgentAPI] Placeholder not in quotes - value not valid JSON, escaped as string")
                                else:
                                    # Not JSON-like, escape as string
                                    escaped_json = json.dumps(value, ensure_ascii=False)
                                    escaped_value = escaped_json
                                    logger.info(f"[DebugAgentAPI] Placeholder not in quotes - escaped as string")
                            
                            # Replace this occurrence
                            body_str = body_str[:pos] + escaped_value + body_str[pos + len(placeholder):]
                        else:
                            # For non-string values (dict, list, numbers, booleans, null)
                            # Need to check if placeholder is inside quotes
                            if is_inside_quotes:
                                # Placeholder is inside quotes - need to escape the JSON string
                                # Serialize the value to JSON, then escape it as a string
                                value_json = json.dumps(value, ensure_ascii=False)
                                # Escape the JSON string and remove outer quotes
                                escaped_json = json.dumps(value_json, ensure_ascii=False)
                                if len(escaped_json) >= 2 and escaped_json[0] == '"' and escaped_json[-1] == '"':
                                    escaped_value = escaped_json[1:-1]
                                else:
                                    escaped_value = escaped_json
                                logger.info(f"[DebugAgentAPI] Non-string value in quotes - escaped JSON (first 200 chars): {escaped_value[:200]}...")
                                body_str = body_str[:pos] + escaped_value + body_str[pos + len(placeholder):]
                            else:
                                # Placeholder is NOT in quotes - use JSON directly
                                # For numbers, booleans, null, json.dumps() returns the value directly
                                # For dict/list, json.dumps() returns the JSON object representation
                                value_json = json.dumps(value, ensure_ascii=False)
                                logger.info(f"[DebugAgentAPI] Non-string value not in quotes - JSON: {value_json[:200] if len(value_json) > 200 else value_json}...")
                                body_str = body_str[:pos] + value_json + body_str[pos + len(placeholder):]
            
            logger.info(f"[DebugAgentAPI] Template JSON string (after replacement): {body_str}")
            
            # Parse the final JSON string back to dict
            try:
                api_body = json.loads(body_str)
                logger.info(f"[DebugAgentAPI] Final api_body keys: {list(api_body.keys()) if isinstance(api_body, dict) else 'not a dict'}")
                
                # Post-process: If a field value is a JSON string but should be an object, parse it
                # Common field names that typically expect JSON objects: paramMap, params, parameters, data, body, etc.
                json_object_fields = ['paramMap', 'params', 'parameters', 'data', 'body', 'input', 'inputs', 'inputs_content', 'content']
                if isinstance(api_body, dict):
                    # First, check known field names
                    for field_name in json_object_fields:
                        if field_name in api_body and isinstance(api_body[field_name], str):
                            try:
                                parsed = json.loads(api_body[field_name])
                                logger.info(f"[DebugAgentAPI] Parsed {field_name} from JSON string to object")
                                api_body[field_name] = parsed
                            except (json.JSONDecodeError, ValueError):
                                # Not a valid JSON string, keep as is
                                logger.debug(f"[DebugAgentAPI] Field {field_name} is not a valid JSON string, keeping as is")
                                pass
                    
                    # Then, check all string fields that look like JSON
                    # This helps catch fields that might be JSON strings but aren't in the known list
                    for field_name, field_value in api_body.items():
                        if isinstance(field_value, str) and field_name not in json_object_fields:
                            # Check if the string looks like JSON (starts with { or [)
                            stripped = field_value.strip()
                            if (stripped.startswith('{') and stripped.endswith('}')) or \
                               (stripped.startswith('[') and stripped.endswith(']')):
                                try:
                                    parsed = json.loads(field_value)
                                    logger.info(f"[DebugAgentAPI] Parsed {field_name} (detected as JSON string) from JSON string to object")
                                    api_body[field_name] = parsed
                                except (json.JSONDecodeError, ValueError):
                                    # Not a valid JSON string, keep as is
                                    logger.debug(f"[DebugAgentAPI] Field {field_name} looks like JSON but is not valid, keeping as is")
                                pass
                
                logger.info(f"[DebugAgentAPI] Final api_body: {json.dumps(api_body, ensure_ascii=False, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"[DebugAgentAPI] Failed to parse api_body_template after replacement: {e}")
                logger.error(f"[DebugAgentAPI] JSON decode error at position {e.pos}: {e.msg}")
                logger.error(f"[DebugAgentAPI] Original template: {json.dumps(api_body_template, ensure_ascii=False, indent=2)}")
                logger.error(f"[DebugAgentAPI] Mapped data keys: {list(mapped_data.keys())}")
                logger.error(f"[DebugAgentAPI] Mapped data types: {[(k, type(v).__name__, str(v)[:100] + '...' if len(str(v)) > 100 else str(v)) for k, v in mapped_data.items()]}")
                logger.error(f"[DebugAgentAPI] Invalid JSON string (first 500 chars): {body_str[:500]}")
                logger.error(f"[DebugAgentAPI] Invalid JSON string (around error position): {body_str[max(0, e.pos-50):e.pos+50] if e.pos else 'N/A'}")
                logger.error(f"[DebugAgentAPI] Invalid JSON string (full length): {len(body_str)} chars")
                
                # Try to provide more helpful error message
                error_context = body_str[max(0, e.pos-50):e.pos+50] if e.pos else ''
                error_msg = (
                    f'Invalid api_body_template after placeholder replacement: {str(e)}. '
                    f'Error at position {e.pos}: {e.msg}. '
                    f'Context: {error_context}. '
                    f'This usually happens when a placeholder value contains JSON that breaks the template structure. '
                    f'Check if placeholder values need to be escaped or if the template structure is correct.'
                )
                logger.error(f"[DebugAgentAPI] {error_msg}")
                return {
                    'success': False,
                    'message': error_msg,
                    'error_details': {
                        'json_error': str(e),
                        'error_position': e.pos,
                        'error_message': e.msg,
                        'template_before': json.dumps(api_body_template, ensure_ascii=False, indent=2),
                        'json_after_first_500': body_str[:500],
                        'json_after_around_error': body_str[max(0, e.pos-50):e.pos+50] if e.pos else 'N/A',
                        'mapped_data_keys': list(mapped_data.keys()),
                        'mapped_data_types': [(k, type(v).__name__) for k, v in mapped_data.items()]
                    }
                }
        else:
            # If no template, use mapped_data directly
            api_body = mapped_data
            logger.info(f"[DebugAgentAPI] No template, using mapped_data directly. Keys: {list(api_body.keys())}")
        
        # Log the final request details before sending
        logger.info(f"[DebugAgentAPI] Sending {api_method} request to {api_url}")
        logger.debug(f"[DebugAgentAPI] Request headers: {json.dumps(api_headers, ensure_ascii=False, indent=2)}")
        logger.debug(f"[DebugAgentAPI] Request body: {json.dumps(api_body, ensure_ascii=False, indent=2)}")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if api_method.upper() == 'POST':
                    response = await client.post(api_url, json=api_body, headers=api_headers)
                elif api_method.upper() == 'GET':
                    response = await client.get(api_url, params=api_body, headers=api_headers)
                elif api_method.upper() == 'PUT':
                    response = await client.put(api_url, json=api_body, headers=api_headers)
                elif api_method.upper() == 'PATCH':
                    response = await client.patch(api_url, json=api_body, headers=api_headers)
                else:
                    logger.error(f"[DebugAgentAPI] Unsupported HTTP method: {api_method}")
                    return {
                        'success': False,
                        'message': f'Unsupported HTTP method: {api_method}'
                    }
                
                logger.info(f"[DebugAgentAPI] Response status: {response.status_code}")
                
                # Parse response body first (before checking HTTP status)
                # This allows us to check for business-level errors even when HTTP status is 200
                try:
                    result = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                except Exception as parse_error:
                    # If response body parsing fails, check HTTP status
                    if not (200 <= response.status_code < 300):
                        error_msg = f'HTTP {response.status_code} error: Failed to parse response body'
                        logger.error(f"[DebugAgentAPI] {error_msg}")
                        return {
                            'success': False,
                            'message': error_msg,
                            'error': str(parse_error),
                            'status_code': response.status_code,
                            'response': response.text[:500] if hasattr(response, 'text') else None
                        }
                    # If HTTP status is 2xx but parsing failed, return error
                    logger.error(f"[DebugAgentAPI] Failed to parse response body: {str(parse_error)}")
                    return {
                        'success': False,
                        'message': f'Failed to parse response body: {str(parse_error)}',
                        'error': str(parse_error),
                        'status_code': response.status_code,
                        'response': response.text[:500] if hasattr(response, 'text') else None
                    }
                
                # Check for business-level errors in response (even if HTTP status is 200)
                # Some APIs return HTTP 200 but include error codes in the response body
                if isinstance(result, dict):
                    error_code = result.get('code')
                    error_msg = result.get('msg') or result.get('message')
                    
                    # Check if response indicates an error (common patterns: code != 0, code >= 4000, or has error message)
                    if error_code is not None and (error_code != 0 and error_code != 200):
                        logger.error(f"[DebugAgentAPI] Business error in response: code={error_code}, msg={error_msg}")
                        logger.error(f"[DebugAgentAPI] Full response: {json.dumps(result, ensure_ascii=False)}")
                        return {
                            'success': False,
                            'message': f'API returned business error: {error_msg or f"Error code {error_code}"}',
                            'response': result,
                            'status_code': response.status_code,
                            'error_code': error_code,
                            'error_message': error_msg
                        }
                    elif error_msg and ('error' in error_msg.lower() or '异常' in error_msg or '失败' in error_msg):
                        # Also check for error keywords in message
                        logger.error(f"[DebugAgentAPI] Error message detected in response: {error_msg}")
                        logger.error(f"[DebugAgentAPI] Full response: {json.dumps(result, ensure_ascii=False)}")
                        return {
                            'success': False,
                            'message': f'API returned error: {error_msg}',
                            'response': result,
                            'status_code': response.status_code,
                            'error_message': error_msg
                        }
                
                # If no business errors detected, check HTTP status code
                if not (200 <= response.status_code < 300):
                    error_msg = f'HTTP {response.status_code} error'
                    logger.error(f"[DebugAgentAPI] {error_msg}")
                    return {
                        'success': False,
                        'message': error_msg,
                        'status_code': response.status_code,
                        'response': result
                        }
                
                logger.info(f"[DebugAgentAPI] Request successful, response: {json.dumps(result, ensure_ascii=False)[:500]}...")
                return {
                    'success': True,
                    'message': 'Debug successful',
                    'response': result,
                    'status_code': response.status_code
                }
        except httpx.HTTPStatusError as e:
            # HTTP error with status code
            error_msg = f'HTTP {e.response.status_code} error: {str(e)}'
            try:
                error_body = e.response.json() if e.response.headers.get('content-type', '').startswith('application/json') else e.response.text
                logger.error(f"[DebugAgentAPI] {error_msg}")
                logger.error(f"[DebugAgentAPI] Error response body: {json.dumps(error_body, ensure_ascii=False) if isinstance(error_body, dict) else error_body}")
            except:
                logger.error(f"[DebugAgentAPI] {error_msg}")
                logger.error(f"[DebugAgentAPI] Error response text: {e.response.text[:500]}")
            
            return {
                'success': False,
                'message': error_msg,
                'error': str(e),
                'status_code': e.response.status_code,
                'response': error_body if 'error_body' in locals() else None
            }
        except httpx.HTTPError as e:
            # Network or other HTTP errors
            logger.error(f"[DebugAgentAPI] HTTP error: {str(e)}")
            return {
                'success': False,
                'message': f'HTTP error: {str(e)}',
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"[DebugAgentAPI] Request failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Request failed: {str(e)}',
                'error': str(e)
            }
    
    async def _debug_model(self, config: Dict[str, Any], test_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Debug model by calling LLM API using AutoGen framework
        
        Args:
            config: Model configuration
            test_data: Test data (should contain 'prompt' or 'messages')
            
        Returns:
            Debug result
        """
        # Check if config has model_config_id (preferred way)
        model_config_id = config.get('model_config_id')
        
        # Prepare messages from test_data
        messages = None
        if 'messages' in test_data:
            messages = test_data['messages']
            if not isinstance(messages, list):
                messages = None
        
        # Prepare prompt text from test_data (for backward compatibility)
        prompt_text = None
        if 'prompt' in test_data:
            prompt_text = test_data['prompt']
        elif messages:
            # Convert messages to a single prompt text (for fallback)
            if len(messages) > 0:
                prompt_parts = []
                for msg in messages:
                    role = msg.get('role', 'user') if isinstance(msg, dict) else 'user'
                    content = msg.get('content', '') if isinstance(msg, dict) else str(msg)
                    if role == 'user':
                        prompt_parts.append(content)
                    elif role == 'assistant':
                        prompt_parts.append(f"Assistant: {content}")
                    elif role == 'system':
                        prompt_parts.append(f"System: {content}")
                prompt_text = '\n\n'.join(prompt_parts) if prompt_parts else str(messages)
        else:
            return {
                'success': False,
                'message': 'Test data must contain "prompt" or "messages"'
            }
            
        if not prompt_text and not messages:
            prompt_text = json.dumps(test_data, ensure_ascii=False)
        
        # Use LLMService if model_config_id is available
        if model_config_id:
            logger.info(f"[DebugModel] Using LLMService with model_config_id={model_config_id}")
            from app.services.llm_service import LLMService
            
            llm_service = LLMService(self.db)
            
            # Get temperature, max_tokens, timeout from config (may override model_config defaults)
            temperature = config.get("temperature")
            max_tokens = config.get("max_tokens")
            timeout = config.get("timeout")
            
            # Convert messages if available, otherwise use prompt_text
            if messages:
                # Use messages directly
                messages_to_send = messages
            else:
                # Use prompt_text as user message
                messages_to_send = [{"role": "user", "content": prompt_text}]
            
            try:
                llm_response = await llm_service.invoke(
                    messages=messages_to_send,
                    model_config_id=model_config_id,
                    system_message="You are a helpful assistant. Respond to user requests directly and concisely.",
                    temperature=float(temperature) if temperature is not None else None,
                    max_tokens=int(max_tokens) if max_tokens is not None else None,
                    timeout=int(timeout) if timeout is not None else None,
                )
                
                if llm_response.error:
                    return {
                        'success': False,
                        'message': f'LLM invocation error: {llm_response.error}',
                        'response': '',
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'model': config.get('model_version', 'unknown'),
                    }
                
                return {
                    'success': True,
                    'message': 'Debug successful',
                    'response': llm_response.content,
                    'input_tokens': llm_response.token_usage.input_tokens,
                    'output_tokens': llm_response.token_usage.output_tokens,
                    'model': llm_response.metadata.get('model', config.get('model_version', 'unknown')),
                }
            except Exception as e:
                logger.error(f"[DebugModel] LLMService invocation failed: {str(e)}", exc_info=True)
                return {
                    'success': False,
                    'message': f'LLM invocation error: {str(e)}',
                    'response': '',
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'model': config.get('model_version', 'unknown'),
                }
        else:
            # Fallback to old AutoGen agent creation (for backward compatibility)
            logger.warning("[DebugModel] model_config_id not found in config, falling back to direct agent creation")
            
            model_version = config.get('model_version')
            encrypted_api_key = config.get('api_key')
            
            if not model_version or not encrypted_api_key:
                return {
                    'success': False,
                    'message': 'Model version and API key are required'
                }
            
            # Decrypt API key for internal use
            api_key = decrypt_api_key(encrypted_api_key)
            
            try:
                # Ensure timeout is an integer (may come as string from JSON)
                timeout_value = config.get('timeout', 120)
                if isinstance(timeout_value, str):
                    try:
                        timeout_value = int(timeout_value)
                    except (ValueError, TypeError):
                        timeout_value = 120
                elif not isinstance(timeout_value, int):
                    timeout_value = int(timeout_value) if timeout_value is not None else 120
                
                # Ensure temperature is a float (may come as string from JSON)
                temperature_value = config.get('temperature')
                if temperature_value is not None:
                    if isinstance(temperature_value, str):
                        try:
                            temperature_value = float(temperature_value)
                        except (ValueError, TypeError):
                            temperature_value = None
                    elif not isinstance(temperature_value, (int, float)):
                        try:
                            temperature_value = float(temperature_value)
                        except (ValueError, TypeError):
                            temperature_value = None
                
                # Ensure max_tokens is an integer (may come as string from JSON)
                max_tokens_value = config.get('max_tokens')
                if max_tokens_value is not None:
                    if isinstance(max_tokens_value, str):
                        try:
                            max_tokens_value = int(max_tokens_value)
                        except (ValueError, TypeError):
                            max_tokens_value = None
                    elif not isinstance(max_tokens_value, int):
                        try:
                            max_tokens_value = int(max_tokens_value)
                        except (ValueError, TypeError):
                            max_tokens_value = None
                
                # Create autogen config from model config (supports qwen and all other model types)
                # Import here to avoid circular import with autogen_helper
                from app.utils.autogen_helper import create_autogen_config_from_model_config, _clear_agent_chat_messages
                
                model_config_dict = {
                    "model_type": config.get('model_type', 'openai'),
                    "model_version": model_version,
                    "api_key": api_key,
                    "api_base": config.get('api_base'),
                    "temperature": temperature_value,
                    "max_tokens": max_tokens_value,
                    "timeout": timeout_value,
                }
                
                autogen_config = create_autogen_config_from_model_config(model_config_dict)
                
                # Create AutoGen agent
                agent = ConversableAgent(
                    name="debug_agent",
                    system_message="You are a helpful assistant. Respond to user requests directly and concisely.",
                    llm_config=autogen_config,
                    human_input_mode="NEVER",
                    max_consecutive_auto_reply=1,
                )
                
                # Clear chat history before generating reply
                # This ensures each debug invocation is independent and doesn't reuse previous results
                _clear_agent_chat_messages(agent)
                
                # Generate reply using AutoGen agent
                # Note: AutoGen's generate_reply is synchronous, but we're in async context
                # We need to run it in a thread pool
                loop = asyncio.get_event_loop()
                
                response = await loop.run_in_executor(
                    None,
                    lambda: agent.generate_reply(
                        messages=[{"role": "user", "content": prompt_text}]
                    )
                )
                
                # Extract content from response
                if isinstance(response, dict):
                    content = response.get("content", "")
                elif hasattr(response, "content"):
                    content = response.content
                else:
                    content = str(response)
                
                # Try to extract token usage from agent's internal state
                input_tokens = 0
                output_tokens = 0
                model_name = model_version
                
                try:
                    # Try various ways to extract token usage from AutoGen agent
                    if hasattr(agent, 'last_cost'):
                        cost_info = agent.last_cost
                        if isinstance(cost_info, dict):
                            input_tokens = cost_info.get("input_tokens", 0) or cost_info.get("prompt_tokens", 0)
                            output_tokens = cost_info.get("output_tokens", 0) or cost_info.get("completion_tokens", 0)
                    
                    if hasattr(agent, 'usage'):
                        usage = agent.usage
                        if isinstance(usage, dict):
                            input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0) or input_tokens
                            output_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0) or output_tokens
                    
                    if hasattr(agent, 'chat_messages'):
                        messages = agent.chat_messages
                        if messages and len(messages) > 0:
                            last_message = messages[-1]
                            if isinstance(last_message, dict) and "usage" in last_message:
                                usage = last_message["usage"]
                                if isinstance(usage, dict):
                                    input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0) or input_tokens
                                    output_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0) or output_tokens
                except Exception as e:
                    logger.warning(f"Failed to extract token usage from AutoGen agent: {str(e)}")
                
                return {
                    'success': True,
                    'message': 'Debug successful',
                    'response': content,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'model': model_name,
                }
            except Exception as e:
                logger.error(f"Failed to debug model (fallback): {str(e)}", exc_info=True)
                return {
                    'success': False,
                    'message': f'Model call failed: {str(e)}',
                    'error': str(e)
                }
    
    def _model_set_to_dict(self, model_set: ModelSet) -> Dict[str, Any]:
        """
        Convert ModelSet model to dictionary
        
        Args:
            model_set: ModelSet model instance
            
        Returns:
            Dictionary representation
        """
        # Mask API key in config for security
        config = model_set.config.copy() if model_set.config else {}
        if model_set.type == 'llm_model' and 'api_key' in config:
            config['api_key'] = mask_api_key(config['api_key'])
        
        return {
            'id': model_set.id,
            'name': model_set.name,
            'description': model_set.description,
            'type': model_set.type,
            'config': config,
            'created_at': model_set.created_at.isoformat() if model_set.created_at else None,
            'updated_at': model_set.updated_at.isoformat() if model_set.updated_at else None,
            'created_by': model_set.created_by,
        }
    
    def validate_model_set(self, model_set_data: Dict[str, Any], exclude_id: Optional[int] = None) -> Dict[str, str]:
        """
        Validate model set data
        
        Args:
            model_set_data: Model set data dictionary
            exclude_id: ID to exclude from uniqueness check (for updates)
            
        Returns:
            Dictionary of validation errors (empty if valid)
        """
        errors = {}
        
        if 'name' in model_set_data and not model_set_data.get('name'):
            errors['name'] = 'Name cannot be empty'
        
        if 'type' in model_set_data:
            valid_types = ['agent_api', 'llm_model']
            if model_set_data.get('type') not in valid_types:
                errors['type'] = f'Type must be one of: {", ".join(valid_types)}'
        
        if 'config' in model_set_data:
            config = model_set_data.get('config')
            if not isinstance(config, dict):
                errors['config'] = 'Config must be a dictionary'
            else:
                # Type-specific validation
                model_set_type = model_set_data.get('type')
                if model_set_type == 'agent_api':
                    if 'api_url' not in config:
                        errors['config.api_url'] = 'API URL is required for agent_api type'
                elif model_set_type == 'llm_model':
                    if 'model_version' not in config:
                        errors['config.model_version'] = 'Model version is required'
                    if 'api_key' not in config:
                        errors['config.api_key'] = 'API key is required'
        
        return errors

