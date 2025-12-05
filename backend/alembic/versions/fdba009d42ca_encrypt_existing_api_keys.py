"""encrypt_existing_api_keys

Revision ID: fdba009d42ca
Revises: 29a455994d5e
Create Date: 2025-12-05 11:42:31.000000

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'fdba009d42ca'
down_revision: Union[str, None] = '29a455994d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Encrypt existing plain text API keys in model_configs and model_sets tables.
    This migration encrypts API keys that are not already encrypted.
    """
    bind = op.get_bind()
    
    # Import encryption utilities
    from app.utils.crypto import encrypt_api_key
    
    # Encrypt API keys in model_configs table
    # Check if table exists and has data
    result = bind.execute(text("""
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'model_configs'
    """))
    
    if result.scalar() > 0:
        # Get all model_configs with potentially unencrypted API keys
        # Fernet encrypted strings start with 'gAAAAAB'
        configs = bind.execute(text("""
            SELECT id, api_key 
            FROM model_configs 
            WHERE api_key IS NOT NULL 
            AND api_key != ''
            AND api_key NOT LIKE 'gAAAAAB%'
        """))
        
        updated_count = 0
        for row in configs:
            config_id, api_key = row
            try:
                encrypted_key = encrypt_api_key(api_key)
                bind.execute(
                    text("UPDATE model_configs SET api_key = :encrypted WHERE id = :id"),
                    {"encrypted": encrypted_key, "id": config_id}
                )
                updated_count += 1
            except Exception as e:
                # Log error but continue with other records
                print(f"Failed to encrypt API key for model_config id {config_id}: {str(e)}")
        
        if updated_count > 0:
            print(f"Encrypted {updated_count} API keys in model_configs table")
    
    # Encrypt API keys in model_sets table (stored in JSON config)
    result = bind.execute(text("""
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE() 
        AND table_name = 'model_sets'
    """))
    
    if result.scalar() > 0:
        # Get all model_sets with llm_model type that might have unencrypted API keys
        model_sets = bind.execute(text("""
            SELECT id, config, type 
            FROM model_sets 
            WHERE type = 'llm_model' 
            AND config IS NOT NULL
        """))
        
        updated_count = 0
        for row in model_sets:
            model_set_id, config_json, model_type = row
            try:
                if config_json:
                    # Parse JSON config
                    if isinstance(config_json, str):
                        config = json.loads(config_json)
                    else:
                        config = config_json
                    
                    # Check if api_key exists and is not encrypted
                    if 'api_key' in config and config['api_key']:
                        api_key = config['api_key']
                        # Check if already encrypted
                        if not api_key.startswith('gAAAAAB'):
                            # Encrypt the API key
                            encrypted_key = encrypt_api_key(api_key)
                            config['api_key'] = encrypted_key
                            
                            # Update the record
                            updated_config = json.dumps(config, ensure_ascii=False)
                            bind.execute(
                                text("UPDATE model_sets SET config = :config WHERE id = :id"),
                                {"config": updated_config, "id": model_set_id}
                            )
                            updated_count += 1
            except Exception as e:
                # Log error but continue with other records
                print(f"Failed to encrypt API key for model_set id {model_set_id}: {str(e)}")
        
        if updated_count > 0:
            print(f"Encrypted {updated_count} API keys in model_sets table")


def downgrade() -> None:
    """
    Note: Decryption is not implemented in downgrade as it would require
    the original plain text keys which we don't have.
    This migration is one-way for security reasons.
    """
    # Decryption is intentionally not implemented for security reasons
    # Once encrypted, API keys should remain encrypted
    pass

