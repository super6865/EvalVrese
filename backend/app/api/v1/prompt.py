"""
Prompt API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.core.database import get_db
from app.services.prompt_service import PromptService
from app.services.model_config_service import ModelConfigService
from app.services.prompt_evaluator_service import PromptEvaluatorService
from app.domain.entity.evaluator_entity import EvaluatorInputData, Content, ContentType
from app.utils.api_decorators import handle_api_errors, handle_not_found
import time

router = APIRouter()


# ========== Request/Response Models ==========

class PromptBasicResponse(BaseModel):
    id: int
    prompt_key: str
    display_name: str
    description: Optional[str] = None
    latest_version: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    latest_committed_at: Optional[datetime] = None
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PromptDraftResponse(BaseModel):
    draft_info: Dict[str, Any]
    detail: Optional[Dict[str, Any]] = None


class PromptCommitResponse(BaseModel):
    commit_info: Dict[str, Any]
    detail: Optional[Dict[str, Any]] = None


class PromptResponse(BaseModel):
    id: int
    prompt_key: str
    prompt_basic: PromptBasicResponse
    prompt_draft: Optional[PromptDraftResponse] = None
    prompt_commit: Optional[PromptCommitResponse] = None
    user: Optional[Dict[str, Any]] = None


class PromptCreate(BaseModel):
    prompt_key: str
    prompt_name: str
    prompt_description: Optional[str] = None
    draft_detail: Optional[Dict[str, Any]] = None


class PromptUpdate(BaseModel):
    prompt_name: Optional[str] = None
    prompt_description: Optional[str] = None


class PromptClone(BaseModel):
    prompt_id: int
    cloned_prompt_key: str
    cloned_prompt_name: str
    cloned_prompt_description: Optional[str] = None
    commit_version: Optional[str] = None


class DraftSave(BaseModel):
    detail: Dict[str, Any]
    base_version: Optional[str] = None


class VersionSubmit(BaseModel):
    version: str
    description: Optional[str] = None


class PromptVersionResponse(BaseModel):
    id: int
    prompt_id: int
    version: str
    description: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DebugRequest(BaseModel):
    messages: Optional[List[Dict[str, Any]]] = None
    variables: Optional[Dict[str, Any]] = None
    model_config: Optional[Dict[str, Any]] = None
    
    # Pydantic v2 uses 'model_config' as a reserved name for model configuration
    # We need to use Field with alias to avoid conflict, or access via model_dump()
    class Config:
        # Allow extra fields and preserve field names
        extra = "allow"


class DebugResponse(BaseModel):
    content: Optional[str] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    time_consuming_ms: Optional[int] = None


class ExecutionHistoryResponse(BaseModel):
    id: int
    timestamp: str
    input: Optional[str] = None
    output: Optional[str] = None
    success: bool


# ========== Helper Functions ==========

def _build_prompt_response(prompt: Any, db: Session, include_user: bool = True) -> Dict[str, Any]:
    """Build prompt response from database model"""
    prompt_basic = {
        "id": prompt.id,
        "prompt_key": prompt.prompt_key,
        "display_name": prompt.display_name,
        "description": prompt.description,
        "latest_version": prompt.latest_version,
        "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
        "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None,
        "latest_committed_at": prompt.latest_committed_at.isoformat() if prompt.latest_committed_at else None,
        "created_by": prompt.created_by,
    }
    
    prompt_draft = None
    if prompt.draft_detail:
        is_modified = prompt.draft_updated_at and (
            not prompt.latest_committed_at or 
            prompt.draft_updated_at > prompt.latest_committed_at
        )
        
        # Extract base_version from draft_detail metadata if exists
        base_version = prompt.latest_version  # Default to latest_version
        if isinstance(prompt.draft_detail, dict) and '_metadata' in prompt.draft_detail:
            metadata = prompt.draft_detail.get('_metadata', {})
            if 'base_version' in metadata:
                base_version = metadata['base_version']
        
        # Create draft_detail without metadata for response
        draft_detail = prompt.draft_detail
        if isinstance(draft_detail, dict) and '_metadata' in draft_detail:
            draft_detail = {k: v for k, v in draft_detail.items() if k != '_metadata'}
        
        prompt_draft = {
            "draft_info": {
                "is_modified": is_modified,
                "updated_at": prompt.draft_updated_at.isoformat() if prompt.draft_updated_at else None,
                "base_version": base_version,
            },
            "detail": draft_detail,
        }
    
    prompt_commit = None
    if prompt.latest_version and prompt.latest_committed_at:
        # Get version content
        service = PromptService(db)
        version = service.get_version(prompt.id, prompt.latest_version)
        if version:
            prompt_commit = {
                "commit_info": {
                    "version": version.version,
                    "committed_at": version.created_at.isoformat() if version.created_at else None,
                },
                "detail": version.content,
            }
    
    user = None
    if include_user and prompt.created_by:
        # TODO: Get user info from user service if available
        user = {
            "user_id": prompt.created_by,
            "nick_name": prompt.created_by,
            "avatar_url": "",
        }
    
    return {
        "id": prompt.id,
        "prompt_key": prompt.prompt_key,
        "prompt_basic": prompt_basic,
        "prompt_draft": prompt_draft,
        "prompt_commit": prompt_commit,
        "user": user,
    }


# ========== API Endpoints ==========

@router.get("", response_model=Dict[str, Any])
@handle_api_errors
async def list_prompts(
    page_number: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    key_word: Optional[str] = Query(None),
    order_by: Optional[str] = Query(None),
    asc: bool = Query(False),
    created_bys: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
):
    """List prompts with pagination and filters"""
    service = PromptService(db)
    prompts, total = service.list_prompts(
        page_number=page_number,
        page_size=page_size,
        key_word=key_word,
        order_by=order_by,
        asc=asc,
        created_bys=created_bys,
    )
    
    # Build response
    prompt_list = []
    for prompt in prompts:
        prompt_list.append(_build_prompt_response(prompt, db, include_user=True))
    
    # Get unique users
    users = []
    user_ids = set()
    for prompt in prompts:
        if prompt.created_by and prompt.created_by not in user_ids:
            user_ids.add(prompt.created_by)
            users.append({
                "user_id": prompt.created_by,
                "nick_name": prompt.created_by,
                "avatar_url": "",
            })
    
    return {
        "success": True,
        "data": {
            "prompts": prompt_list,
            "total": total,
            "users": users,
        },
        "message": "Get prompts successfully",
    }


@router.get("/{prompt_id}", response_model=Dict[str, Any])
@handle_api_errors
@handle_not_found("Prompt not found")
async def get_prompt(
    prompt_id: int,
    db: Session = Depends(get_db),
):
    """Get prompt by ID"""
    service = PromptService(db)
    prompt = service.get_prompt(prompt_id)
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    return {
        "success": True,
        "data": _build_prompt_response(prompt, db, include_user=True),
        "message": "Get prompt successfully",
    }


@router.post("", response_model=Dict[str, Any])
@handle_api_errors
async def create_prompt(
    data: PromptCreate,
    created_by: str = Query("system"),  # TODO: Get from auth context
    db: Session = Depends(get_db),
):
    """Create a new prompt"""
    service = PromptService(db)
    
    try:
        prompt = service.create_prompt(
            prompt_key=data.prompt_key,
            display_name=data.prompt_name,
            description=data.prompt_description,
            created_by=created_by,
            draft_detail=data.draft_detail,
        )
        
        return {
            "success": True,
            "data": {"prompt_id": prompt.id},
            "message": "Create prompt successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{prompt_id}", response_model=Dict[str, Any])
@handle_api_errors
@handle_not_found("Prompt not found")
async def update_prompt(
    prompt_id: int,
    data: PromptUpdate,
    db: Session = Depends(get_db),
):
    """Update prompt basic info"""
    service = PromptService(db)
    
    try:
        prompt = service.update_prompt(
            prompt_id=prompt_id,
            display_name=data.prompt_name,
            description=data.prompt_description,
        )
        
        return {
            "success": True,
            "data": {},
            "message": "Update prompt successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{prompt_id}", response_model=Dict[str, Any])
@handle_api_errors
@handle_not_found("Prompt not found")
async def delete_prompt(
    prompt_id: int,
    db: Session = Depends(get_db),
):
    """Delete prompt"""
    service = PromptService(db)
    
    try:
        service.delete_prompt(prompt_id)
        
        return {
            "success": True,
            "data": {},
            "message": "Delete prompt successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/clone", response_model=Dict[str, Any])
@handle_api_errors
async def clone_prompt(
    data: PromptClone,
    created_by: str = Query("system"),  # TODO: Get from auth context
    db: Session = Depends(get_db),
):
    """Clone a prompt"""
    service = PromptService(db)
    
    try:
        cloned_prompt = service.clone_prompt(
            prompt_id=data.prompt_id,
            cloned_prompt_key=data.cloned_prompt_key,
            cloned_display_name=data.cloned_prompt_name,
            cloned_description=data.cloned_prompt_description,
            commit_version=data.commit_version,
            created_by=created_by,
        )
        
        return {
            "success": True,
            "data": {"cloned_prompt_id": cloned_prompt.id},
            "message": "Clone prompt successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{prompt_id}/versions", response_model=Dict[str, Any])
@handle_api_errors
@handle_not_found("Prompt not found")
async def list_versions(
    prompt_id: int,
    db: Session = Depends(get_db),
):
    """List prompt versions"""
    service = PromptService(db)
    
    # Check if prompt exists
    prompt = service.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    versions = service.list_versions(prompt_id)
    
    version_list = []
    for version in versions:
        version_list.append({
            "id": version.id,
            "prompt_id": version.prompt_id,
            "version": version.version,
            "description": version.description,
            "content": version.content,
            "created_at": version.created_at.isoformat() if version.created_at else None,
            "updated_at": version.updated_at.isoformat() if version.updated_at else None,
            "created_by": version.created_by,
        })
    
    return {
        "success": True,
        "data": version_list,
        "message": "Get versions successfully",
    }


@router.get("/{prompt_id}/versions/{version}", response_model=Dict[str, Any])
@handle_api_errors
@handle_not_found("Prompt not found")
async def get_version(
    prompt_id: int,
    version: str,
    db: Session = Depends(get_db),
):
    """Get specific version details"""
    service = PromptService(db)
    
    # Check if prompt exists
    prompt = service.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Get version
    version_obj = service.get_version(prompt_id, version)
    if not version_obj:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return {
        "success": True,
        "data": {
            "id": version_obj.id,
            "prompt_id": version_obj.prompt_id,
            "version": version_obj.version,
            "description": version_obj.description,
            "content": version_obj.content,
            "created_at": version_obj.created_at.isoformat() if version_obj.created_at else None,
            "updated_at": version_obj.updated_at.isoformat() if version_obj.updated_at else None,
            "created_by": version_obj.created_by,
        },
        "message": "Get version successfully",
    }


@router.put("/{prompt_id}/draft", response_model=Dict[str, Any])
@handle_api_errors
@handle_not_found("Prompt not found")
async def save_draft(
    prompt_id: int,
    data: DraftSave,
    db: Session = Depends(get_db),
):
    """Save draft"""
    service = PromptService(db)
    
    try:
        service.save_draft(prompt_id, data.detail, data.base_version)
        
        return {
            "success": True,
            "data": {},
            "message": "Save draft successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{prompt_id}/versions", response_model=Dict[str, Any])
@handle_api_errors
@handle_not_found("Prompt not found")
async def submit_version(
    prompt_id: int,
    data: VersionSubmit,
    created_by: str = Query("system"),  # TODO: Get from auth context
    db: Session = Depends(get_db),
):
    """Submit a new version"""
    service = PromptService(db)
    
    try:
        service.submit_version(
            prompt_id=prompt_id,
            version=data.version,
            description=data.description,
            created_by=created_by,
        )
        
        return {
            "success": True,
            "data": {},
            "message": "Submit version successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{prompt_id}/debug", response_model=Dict[str, Any])
@handle_api_errors
@handle_not_found("Prompt not found")
async def debug_prompt(
    prompt_id: int,
    data: DebugRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Debug/Execute prompt"""
    # Get raw request body for model_config (Pydantic v2 uses 'model_config' as reserved field)
    try:
        body = await request.json()
    except Exception as e:
        print(f"[ERROR] Failed to get raw request body: {e}")
        raise HTTPException(status_code=400, detail="Invalid request body")
    
    service = PromptService(db)
    evaluator_service = PromptEvaluatorService(db)
    model_config_service = ModelConfigService(db)
    
    # Check if prompt exists
    prompt = service.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Get model config from raw request body since Pydantic's 'model_config' is reserved
    # Pydantic v2 uses 'model_config' as a reserved field name for model configuration
    # So we need to get it from the raw request body instead
    model_config = body.get('model_config', {}) if isinstance(body, dict) else {}
    model_config_id = model_config.get("model_config_id") if isinstance(model_config, dict) else None
    
    if not model_config_id:
        raise HTTPException(
            status_code=400, 
            detail=f"model_config_id is required. Received model_config: {model_config}"
        )
    
    # Load model config from database
    model_config_dict = model_config_service.get_config_by_id(
        model_config_id,
        include_sensitive=True,
    )
    
    if not model_config_dict:
        raise HTTPException(status_code=404, detail="Model configuration not found")
    
    # Decrypt API key for internal use (get_config_by_id returns masked key)
    # We need to get the actual config from database and decrypt it
    from app.models.model_config import ModelConfig
    from app.utils.crypto import decrypt_api_key
    db_config = db.query(ModelConfig).filter(ModelConfig.id == model_config_id).first()
    if db_config and db_config.api_key:
        model_config_dict['api_key'] = decrypt_api_key(db_config.api_key)
    
    # Prepare messages
    messages = data.messages or []
    if not messages:
        # Use draft or latest version messages
        if prompt.draft_detail and prompt.draft_detail.get("messages"):
            messages = prompt.draft_detail["messages"]
        elif prompt.latest_version:
            version = service.get_version(prompt_id, prompt.latest_version)
            if version and version.content and version.content.get("messages"):
                messages = version.content["messages"]
    
    # Prepare variables
    variables = data.variables or {}
    
    # Build input data
    input_fields = {}
    for key, value in variables.items():
        if isinstance(value, dict) and value.get("content_type"):
            # Already a Content object
            input_fields[key] = Content(
                content_type=ContentType(value["content_type"]),
                text=value.get("text"),
            )
        else:
            # Convert to Content
            input_fields[key] = Content(
                content_type=ContentType.TEXT,
                text=str(value),
            )
    
    # Directly call LLM model for debugging (not using evaluator)
    # Build autogen config
    from app.utils.autogen_helper import create_autogen_config_from_model_config
    from autogen import ConversableAgent
    import asyncio
    
    # Prepare autogen config dict
    autogen_config_dict = {
        "model_type": model_config_dict.get("model_type", "openai"),
        "model_version": model_config_dict.get("model_version"),
        "api_key": model_config_dict.get("api_key"),
        "api_base": model_config_dict.get("api_base"),
        "temperature": model_config.get("temperature", model_config_dict.get("temperature", 0.7)),
        "max_tokens": model_config.get("max_tokens", model_config_dict.get("max_tokens", 2000)),
        "timeout": model_config_dict.get("timeout", 120),
    }
    
    autogen_config = create_autogen_config_from_model_config(autogen_config_dict)
    
    # Build messages for AutoGen (convert to AutoGen format)
    autogen_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, dict):
            content_text = content.get("text", "") if isinstance(content, dict) else str(content)
        else:
            content_text = str(content)
        
        # Replace variables in content (support {{variable}} format)
        if variables:
            for key, value in variables.items():
                # Support both {{variable}} and {variable} formats
                placeholder_double = "{{" + key + "}}"
                placeholder_single = "{" + key + "}"
                if isinstance(value, dict) and value.get("content_type"):
                    value_text = value.get("text", str(value))
                else:
                    value_text = str(value)
                # Replace double braces first, then single braces
                content_text = content_text.replace(placeholder_double, value_text)
                content_text = content_text.replace(placeholder_single, value_text)
        
        autogen_messages.append({"role": role, "content": content_text})
    
    # Execute
    start_time = time.time()
    try:
        # Create AutoGen agent
        agent = ConversableAgent(
            name="debug_agent",
            system_message="You are a helpful assistant. Respond to user requests directly and concisely.",
            llm_config=autogen_config,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )
        
        # Generate reply using AutoGen agent
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: agent.generate_reply(messages=autogen_messages)
        )
        
        # Extract content from response
        if isinstance(response, dict):
            response_content = response.get("content", "")
        elif hasattr(response, "content"):
            response_content = response.content
        else:
            response_content = str(response)
        
        # Try to extract token usage from agent's internal state
        input_tokens = 0
        output_tokens = 0
        try:
            if hasattr(agent, "client") and hasattr(agent.client, "cost"):
                cost_info = agent.client.cost
                if isinstance(cost_info, dict):
                    input_tokens = cost_info.get("prompt_tokens", 0) or cost_info.get("input_tokens", 0) or 0
                    output_tokens = cost_info.get("completion_tokens", 0) or cost_info.get("output_tokens", 0) or 0
        except Exception:
            pass
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Save execution record
        service.create_execution(
            prompt_id=prompt_id,
            input_data={
                "messages": messages,
                "variables": variables,
            },
            output_content=response_content,
            success=True,
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
            time_consuming_ms=execution_time_ms,
        )
        
        # Return direct model response (not evaluation result)
        return {
            "success": True,
            "data": {
                "content": response_content,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
                "time_consuming_ms": execution_time_ms,
            },
            "message": "Debug execution successfully",
        }
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Save error execution record
        service.create_execution(
            prompt_id=prompt_id,
            input_data={
                "messages": messages,
                "variables": variables,
            },
            error_message=str(e),
            success=False,
            time_consuming_ms=execution_time_ms,
        )
        
        return {
            "success": False,
            "data": {
                "error": str(e),
                "time_consuming_ms": execution_time_ms,
            },
            "message": "Debug execution failed",
        }


@router.get("/{prompt_id}/executions", response_model=Dict[str, Any])
@handle_api_errors
@handle_not_found("Prompt not found")
async def list_executions(
    prompt_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List execution history"""
    service = PromptService(db)
    
    # Check if prompt exists
    prompt = service.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    executions = service.list_executions(prompt_id, limit=limit)
    
    execution_list = []
    for execution in executions:
        # Extract input/output from execution
        input_text = None
        if execution.input_data:
            # Try to extract meaningful input text
            if isinstance(execution.input_data, dict):
                messages = execution.input_data.get("messages", [])
                if messages:
                    # Get last user message
                    for msg in reversed(messages):
                        if msg.get("role") == "user":
                            content = msg.get("content", "")
                            if isinstance(content, dict):
                                input_text = content.get("text", "")
                            else:
                                input_text = str(content)
                            break
        
        execution_list.append({
            "id": f"exec_{execution.id}",
            "timestamp": execution.created_at.isoformat() if execution.created_at else None,
            "input": input_text,
            "output": execution.output_content or execution.error_message,
            "success": execution.success,
        })
    
    return {
        "success": True,
        "data": execution_list,
        "message": "Get execution history successfully",
    }


@router.get("/{prompt_id}/variables", response_model=Dict[str, Any])
@handle_api_errors
@handle_not_found("Prompt not found")
async def get_prompt_variables(
    prompt_id: int,
    version: Optional[str] = Query(None, description="Version string, or 'draft' for draft, or None for draft"),
    db: Session = Depends(get_db),
):
    """Get variables from prompt messages"""
    service = PromptService(db)
    
    # Check if prompt exists
    prompt = service.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    try:
        variables = service.extract_variables_from_prompt(prompt_id, version)
        return {
            "success": True,
            "data": {"variables": variables},
            "message": "Get variables successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

