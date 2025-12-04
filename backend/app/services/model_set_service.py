"""
Model set service
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.model_set import ModelSet
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
            model_set = ModelSet(
                name=model_set_data['name'],
                description=model_set_data.get('description'),
                type=model_set_data['type'],
                config=model_set_data['config'],
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
                model_set.config = model_set_data['config']
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
        
        if not api_url:
            return {
                'success': False,
                'message': 'API URL is required'
            }
        
        # Map test data to API body using input_mapping
        api_body = {}
        if input_mapping:
            for api_key, test_key in input_mapping.items():
                if test_key in test_data:
                    api_body[api_key] = test_data[test_key]
        else:
            # If no mapping, use test_data directly
            api_body = test_data
        
        # Replace placeholders in body template
        if api_body_template:
            for key, value in api_body_template.items():
                if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
                    # Replace placeholder with mapped value
                    placeholder = value[1:-1]
                    if placeholder in api_body:
                        api_body[key] = api_body[placeholder]
                elif key not in api_body:
                    api_body[key] = value
        
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
                    return {
                        'success': False,
                        'message': f'Unsupported HTTP method: {api_method}'
                    }
                
                response.raise_for_status()
                result = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                
                return {
                    'success': True,
                    'message': 'Debug successful',
                    'response': result,
                    'status_code': response.status_code
                }
        except httpx.HTTPError as e:
            return {
                'success': False,
                'message': f'HTTP error: {str(e)}',
                'error': str(e)
            }
        except Exception as e:
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
        model_version = config.get('model_version')
        api_key = config.get('api_key')
        
        if not model_version or not api_key:
            return {
                'success': False,
                'message': 'Model version and API key are required'
            }
        
        # Prepare prompt text from test_data
        prompt_text = None
        if 'prompt' in test_data:
            prompt_text = test_data['prompt']
        elif 'messages' in test_data:
            # Convert messages to a single prompt text
            messages = test_data['messages']
            if isinstance(messages, list) and len(messages) > 0:
                # Use the last user message, or concatenate all messages
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
                prompt_text = str(messages)
        else:
            return {
                'success': False,
                'message': 'Test data must contain "prompt" or "messages"'
            }
            
        if not prompt_text:
            prompt_text = json.dumps(test_data, ensure_ascii=False)
        
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
            from app.utils.autogen_helper import create_autogen_config_from_model_config
            
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
                # Try various ways to extract token usage (similar to AutoGenEvaluator)
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
            logger.error(f"Failed to debug model: {str(e)}", exc_info=True)
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
        return {
            'id': model_set.id,
            'name': model_set.name,
            'description': model_set.description,
            'type': model_set.type,
            'config': model_set.config,
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

