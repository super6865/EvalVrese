"""
Model configuration service
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.model_config import ModelConfig
from app.utils.crypto import encrypt_api_key, decrypt_api_key, mask_api_key
import logging

logger = logging.getLogger(__name__)


class ModelConfigService:
    """Service for managing model configurations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_configs(self, include_sensitive: bool = False, skip: int = 0, limit: int = 100, name: Optional[str] = None) -> tuple[List[Dict[str, Any]], int]:
        """
        Get all model configurations with pagination and search
        
        Args:
            include_sensitive: Whether to include sensitive fields like api_key
            skip: Number of records to skip
            limit: Maximum number of records to return
            name: Optional search term for config_name (partial match)
            
        Returns:
            Tuple of (list of model configurations, total count)
        """
        # Build query with optional name filter
        query = self.db.query(ModelConfig)
        if name:
            query = query.filter(ModelConfig.config_name.ilike(f'%{name}%'))
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        configs = query.order_by(ModelConfig.id.asc()).offset(skip).limit(limit).all()
        
        result = []
        for config in configs:
            config_dict = {
                'id': config.id,
                'config_name': config.config_name,
                'model_type': config.model_type,
                'model_version': config.model_version,
                'api_base': config.api_base,
                'temperature': config.temperature,
                'max_tokens': config.max_tokens,
                'timeout': config.timeout,
                'is_enabled': config.is_enabled,
                'created_at': config.created_at.isoformat() if config.created_at else None,
                'updated_at': config.updated_at.isoformat() if config.updated_at else None,
                'created_by': config.created_by,
            }
            
            if include_sensitive:
                # Return masked API key instead of plain text for security
                config_dict['api_key'] = mask_api_key(config.api_key)
            
            result.append(config_dict)
        
        return result, total
    
    def get_config_by_id(self, config_id: int, include_sensitive: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get model configuration by ID
        
        Args:
            config_id: Configuration ID
            include_sensitive: Whether to include sensitive fields like api_key
            
        Returns:
            Model configuration dictionary or None
        """
        config = self.db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        
        if not config:
            return None
        
        config_dict = {
            'id': config.id,
            'config_name': config.config_name,
            'model_type': config.model_type,
            'model_version': config.model_version,
            'api_base': config.api_base,
            'temperature': config.temperature,
            'max_tokens': config.max_tokens,
            'timeout': config.timeout,
            'is_enabled': config.is_enabled,
            'created_at': config.created_at.isoformat() if config.created_at else None,
            'updated_at': config.updated_at.isoformat() if config.updated_at else None,
            'created_by': config.created_by,
        }
        
        if include_sensitive:
            # Return masked API key instead of plain text for security
            config_dict['api_key'] = mask_api_key(config.api_key)
        
        return config_dict
    
    def create_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new model configuration
        
        Args:
            config_data: Configuration data dictionary
            
        Returns:
            Result dictionary with success status and message
        """
        # Validate required fields
        validation_errors = self.validate_config(config_data)
        if validation_errors:
            return {
                'success': False,
                'message': 'Configuration validation failed',
                'errors': validation_errors
            }
        
        # Check if config_name already exists
        existing = self.db.query(ModelConfig).filter(
            ModelConfig.config_name == config_data['config_name']
        ).first()
        
        if existing:
            return {
                'success': False,
                'message': f'Configuration name "{config_data["config_name"]}" already exists'
            }
        
        try:
            # Encrypt API key before storing
            encrypted_api_key = encrypt_api_key(config_data['api_key'])
            
            config = ModelConfig(
                config_name=config_data['config_name'],
                model_type=config_data['model_type'],
                model_version=config_data['model_version'],
                api_key=encrypted_api_key,
                api_base=config_data.get('api_base'),
                temperature=config_data.get('temperature'),
                max_tokens=config_data.get('max_tokens'),
                timeout=config_data.get('timeout', 60),  # Default to 60 seconds
                is_enabled=config_data.get('is_enabled', False),
                created_by=config_data.get('created_by'),
            )
            
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            
            logger.info(f"Model configuration created: {config.config_name}")
            return {
                'success': True,
                'message': 'Configuration created successfully',
                'data': self.get_config_by_id(config.id, include_sensitive=True)
            }
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create model configuration: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to create configuration: {str(e)}'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create model configuration: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to create configuration: {str(e)}'
            }
    
    def update_config(self, config_id: int, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing model configuration
        
        Args:
            config_id: Configuration ID
            config_data: Configuration data dictionary
            
        Returns:
            Result dictionary with success status and message
        """
        config = self.db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        
        if not config:
            return {
                'success': False,
                'message': 'Configuration not found'
            }
        
        # Validate required fields
        validation_errors = self.validate_config(config_data, exclude_id=config_id)
        if validation_errors:
            return {
                'success': False,
                'message': 'Configuration validation failed',
                'errors': validation_errors
            }
        
        # Check if config_name already exists (excluding current config)
        if 'config_name' in config_data:
            existing = self.db.query(ModelConfig).filter(
                ModelConfig.config_name == config_data['config_name'],
                ModelConfig.id != config_id
            ).first()
            
            if existing:
                return {
                    'success': False,
                    'message': f'Configuration name "{config_data["config_name"]}" already exists'
                }
        
        try:
            # Update fields
            if 'config_name' in config_data:
                config.config_name = config_data['config_name']
            if 'model_type' in config_data:
                config.model_type = config_data['model_type']
            if 'model_version' in config_data:
                config.model_version = config_data['model_version']
            if 'api_key' in config_data and config_data['api_key']:
                # Encrypt API key before storing
                config.api_key = encrypt_api_key(config_data['api_key'])
            if 'api_base' in config_data:
                config.api_base = config_data.get('api_base')
            if 'temperature' in config_data:
                config.temperature = config_data.get('temperature')
            if 'max_tokens' in config_data:
                config.max_tokens = config_data.get('max_tokens')
            if 'timeout' in config_data:
                config.timeout = config_data.get('timeout', 60)
            if 'created_by' in config_data:
                config.created_by = config_data.get('created_by')
            
            self.db.commit()
            self.db.refresh(config)
            
            logger.info(f"Model configuration updated: {config.config_name}")
            return {
                'success': True,
                'message': 'Configuration updated successfully',
                'data': self.get_config_by_id(config.id, include_sensitive=True)
            }
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to update model configuration: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to update configuration: {str(e)}'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update model configuration: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to update configuration: {str(e)}'
            }
    
    def delete_config(self, config_id: int) -> Dict[str, Any]:
        """
        Delete a model configuration
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Result dictionary with success status and message
        """
        config = self.db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        
        if not config:
            return {
                'success': False,
                'message': 'Configuration not found'
            }
        
        try:
            config_name = config.config_name
            self.db.delete(config)
            self.db.commit()
            
            logger.info(f"Model configuration deleted: {config_name}")
            return {
                'success': True,
                'message': f'Configuration "{config_name}" deleted successfully'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete model configuration: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to delete configuration: {str(e)}'
            }
    
    def toggle_enabled(self, config_id: int, enabled: bool) -> Dict[str, Any]:
        """
        Toggle the enabled status of a model configuration
        
        Args:
            config_id: Configuration ID
            enabled: Whether to enable the configuration
            
        Returns:
            Result dictionary with success status and message
        """
        config = self.db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        
        if not config:
            return {
                'success': False,
                'message': 'Configuration not found'
            }
        
        try:
            if enabled:
                # Check if there are other enabled configs (optional: allow multiple enabled)
                # For now, we allow multiple enabled configs
                pass
            
            config.is_enabled = enabled
            self.db.commit()
            self.db.refresh(config)
            
            status_text = 'enabled' if enabled else 'disabled'
            logger.info(f"Model configuration {status_text}: {config.config_name}")
            return {
                'success': True,
                'message': f'Configuration "{config.config_name}" has been {status_text}'
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to toggle model configuration status: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to toggle status: {str(e)}'
            }
    
    def get_autogen_config(self, config_id: int) -> Optional[Dict[str, Any]]:
        """
        Get autogen-compatible configuration format
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Autogen configuration dictionary or None
        """
        config = self.db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        
        if not config:
            return None
        
        # Decrypt API key for internal use
        decrypted_api_key = decrypt_api_key(config.api_key)
        
        # Build autogen config based on model type
        autogen_config = {
            "model": config.model_version,
            "api_key": decrypted_api_key,
            "base_url": config.api_base,
        }
        
        # Add optional parameters
        if config.temperature is not None:
            autogen_config["temperature"] = config.temperature
        if config.max_tokens is not None:
            autogen_config["max_tokens"] = config.max_tokens
        
        # Note: timeout is handled by create_autogen_config_from_model_config
        # which wraps this in the proper format with config_list and timeout
        
        return autogen_config
    
    def validate_config(self, config_data: Dict[str, Any], exclude_id: Optional[int] = None) -> Dict[str, str]:
        """
        Validate configuration data
        
        Args:
            config_data: Configuration data dictionary
            exclude_id: ID to exclude from uniqueness check (for updates)
            
        Returns:
            Dictionary of validation errors (empty if valid)
        """
        errors = {}
        
        if 'config_name' in config_data and not config_data.get('config_name'):
            errors['config_name'] = 'Configuration name cannot be empty'
        
        if 'model_type' in config_data and not config_data.get('model_type'):
            errors['model_type'] = 'Model type cannot be empty'
        
        if 'model_version' in config_data and not config_data.get('model_version'):
            errors['model_version'] = 'Model version cannot be empty'
        
        if 'api_key' in config_data and not config_data.get('api_key'):
            errors['api_key'] = 'API key cannot be empty'
        
        # Validate temperature if provided
        if 'temperature' in config_data and config_data.get('temperature') is not None:
            try:
                temp = float(config_data['temperature'])
                if temp < 0 or temp > 2:
                    errors['temperature'] = 'Temperature must be between 0 and 2'
            except (ValueError, TypeError):
                errors['temperature'] = 'Temperature must be a valid number'
        
        # Validate max_tokens if provided
        if 'max_tokens' in config_data and config_data.get('max_tokens') is not None:
            try:
                tokens = int(config_data['max_tokens'])
                if tokens < 1:
                    errors['max_tokens'] = 'Max tokens must be greater than 0'
            except (ValueError, TypeError):
                errors['max_tokens'] = 'Max tokens must be a valid integer'
        
        # Validate timeout if provided
        if 'timeout' in config_data and config_data.get('timeout') is not None:
            try:
                timeout = int(config_data['timeout'])
                if timeout < 1:
                    errors['timeout'] = 'Timeout must be greater than 0'
                if timeout > 600:  # Max 10 minutes
                    errors['timeout'] = 'Timeout must be less than or equal to 600 seconds'
            except (ValueError, TypeError):
                errors['timeout'] = 'Timeout must be a valid integer'
        
        return errors

