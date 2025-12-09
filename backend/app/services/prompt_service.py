"""
Prompt service
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from typing import List, Optional, Dict, Any, Tuple
from app.models.prompt import Prompt, PromptVersion, PromptExecution
from datetime import datetime
import json


class PromptService:
    def __init__(self, db: Session):
        self.db = db

    # ========== Prompt CRUD ==========
    
    def create_prompt(
        self,
        prompt_key: str,
        display_name: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        draft_detail: Optional[Dict[str, Any]] = None,
    ) -> Prompt:
        """Create a new prompt"""
        # Check if prompt_key already exists
        existing = self.db.query(Prompt).filter(Prompt.prompt_key == prompt_key).first()
        if existing:
            raise ValueError(f"Prompt key '{prompt_key}' already exists")
        
        prompt = Prompt(
            prompt_key=prompt_key,
            display_name=display_name,
            description=description,
            created_by=created_by,
            status="active",
            draft_detail=draft_detail,
            draft_updated_at=datetime.utcnow() if draft_detail else None,
        )
        self.db.add(prompt)
        self.db.commit()
        self.db.refresh(prompt)
        
        return prompt

    def get_prompt(self, prompt_id: int) -> Optional[Prompt]:
        """Get prompt by ID"""
        return self.db.query(Prompt).filter(
            and_(Prompt.id == prompt_id, Prompt.status != "deleted")
        ).first()

    def list_prompts(
        self,
        page_number: int = 1,
        page_size: int = 20,
        key_word: Optional[str] = None,
        order_by: Optional[str] = None,
        asc: bool = False,
        created_bys: Optional[List[str]] = None,
    ) -> Tuple[List[Prompt], int]:
        """List prompts with pagination and filters"""
        query = self.db.query(Prompt).filter(Prompt.status != "deleted")
        
        # Search by key_word
        if key_word:
            search_term = f"%{key_word}%"
            query = query.filter(
                or_(
                    Prompt.prompt_key.ilike(search_term),
                    Prompt.display_name.ilike(search_term),
                )
            )
        
        # Filter by created_by
        if created_bys and len(created_bys) > 0:
            query = query.filter(Prompt.created_by.in_(created_bys))
        
        # Sort
        if order_by == "created_at":
            query = query.order_by(asc(Prompt.created_at) if asc else desc(Prompt.created_at))
        elif order_by == "committed_at":
            query = query.order_by(
                asc(Prompt.latest_committed_at) if asc else desc(Prompt.latest_committed_at)
            )
        else:
            # Default: sort by updated_at desc
            query = query.order_by(desc(Prompt.updated_at))
        
        # Get total count
        total = query.count()
        
        # Pagination
        skip = (page_number - 1) * page_size
        prompts = query.offset(skip).limit(page_size).all()
        
        return prompts, total

    def update_prompt(
        self,
        prompt_id: int,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Prompt:
        """Update prompt basic info"""
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            raise ValueError("Prompt not found")
        
        if display_name is not None:
            prompt.display_name = display_name
        if description is not None:
            prompt.description = description
        
        prompt.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(prompt)
        
        return prompt

    def delete_prompt(self, prompt_id: int) -> None:
        """Soft delete prompt"""
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            raise ValueError("Prompt not found")
        
        prompt.status = "deleted"
        prompt.updated_at = datetime.utcnow()
        self.db.commit()

    def clone_prompt(
        self,
        prompt_id: int,
        cloned_prompt_key: str,
        cloned_display_name: str,
        cloned_description: Optional[str] = None,
        commit_version: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Prompt:
        """Clone a prompt"""
        original = self.get_prompt(prompt_id)
        if not original:
            raise ValueError("Prompt not found")
        
        # Check if cloned_prompt_key already exists
        existing = self.db.query(Prompt).filter(Prompt.prompt_key == cloned_prompt_key).first()
        if existing:
            raise ValueError(f"Prompt key '{cloned_prompt_key}' already exists")
        
        # Determine which content to clone
        content_to_clone = None
        if commit_version:
            # Clone from specific version
            version = self.db.query(PromptVersion).filter(
                and_(
                    PromptVersion.prompt_id == prompt_id,
                    PromptVersion.version == commit_version,
                )
            ).first()
            if version:
                content_to_clone = version.content
        else:
            # Clone from draft or latest version
            if original.draft_detail:
                content_to_clone = original.draft_detail
            elif original.latest_version:
                version = self.db.query(PromptVersion).filter(
                    and_(
                        PromptVersion.prompt_id == prompt_id,
                        PromptVersion.version == original.latest_version,
                    )
                ).first()
                if version:
                    content_to_clone = version.content
        
        # Create cloned prompt
        cloned_prompt = Prompt(
            prompt_key=cloned_prompt_key,
            display_name=cloned_display_name,
            description=cloned_description or original.description,
            created_by=created_by,
            status="active",
            draft_detail=content_to_clone,
            draft_updated_at=datetime.utcnow() if content_to_clone else None,
        )
        self.db.add(cloned_prompt)
        self.db.commit()
        self.db.refresh(cloned_prompt)
        
        return cloned_prompt

    # ========== Draft Management ==========
    
    def save_draft(self, prompt_id: int, detail: Dict[str, Any], base_version: Optional[str] = None) -> Prompt:
        """Save draft detail"""
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            raise ValueError("Prompt not found")
        
        prompt.draft_detail = detail
        prompt.draft_updated_at = datetime.utcnow()
        prompt.updated_at = datetime.utcnow()
        
        # Store base_version in draft_detail metadata if provided
        if base_version:
            if not isinstance(prompt.draft_detail, dict):
                prompt.draft_detail = {}
            # Store base_version as metadata in draft_detail
            if '_metadata' not in prompt.draft_detail:
                prompt.draft_detail['_metadata'] = {}
            prompt.draft_detail['_metadata']['base_version'] = base_version
        
        self.db.commit()
        self.db.refresh(prompt)
        
        return prompt

    # ========== Version Management ==========
    
    def list_versions(self, prompt_id: int) -> List[PromptVersion]:
        """List all versions of a prompt"""
        return self.db.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt_id
        ).order_by(desc(PromptVersion.created_at)).all()

    def submit_version(
        self,
        prompt_id: int,
        version: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> PromptVersion:
        """Submit a new version from draft"""
        prompt = self.get_prompt(prompt_id)
        if not prompt:
            raise ValueError("Prompt not found")
        
        if not prompt.draft_detail:
            raise ValueError("No draft to submit")
        
        # Check if version already exists
        existing = self.db.query(PromptVersion).filter(
            and_(
                PromptVersion.prompt_id == prompt_id,
                PromptVersion.version == version,
            )
        ).first()
        if existing:
            raise ValueError(f"Version '{version}' already exists")
        
        # Create version from draft
        prompt_version = PromptVersion(
            prompt_id=prompt_id,
            version=version,
            description=description,
            content=prompt.draft_detail,
            created_by=created_by,
        )
        self.db.add(prompt_version)
        
        # Update prompt
        prompt.latest_version = version
        prompt.latest_committed_at = datetime.utcnow()
        prompt.updated_at = datetime.utcnow()
        # Keep draft but mark as unmodified (draft_detail stays for future edits)
        
        self.db.commit()
        self.db.refresh(prompt_version)
        
        return prompt_version

    def get_version(self, prompt_id: int, version: str) -> Optional[PromptVersion]:
        """Get specific version"""
        if not self.db:
            return None
        return self.db.query(PromptVersion).filter(
            and_(
                PromptVersion.prompt_id == prompt_id,
                PromptVersion.version == version,
            )
        ).first()

    # ========== Execution Management ==========
    
    def create_execution(
        self,
        prompt_id: int,
        input_data: Optional[Dict[str, Any]] = None,
        output_content: Optional[str] = None,
        error_message: Optional[str] = None,
        success: bool = True,
        usage: Optional[Dict[str, Any]] = None,
        time_consuming_ms: Optional[int] = None,
    ) -> PromptExecution:
        """Create execution record"""
        execution = PromptExecution(
            prompt_id=prompt_id,
            input_data=input_data,
            output_content=output_content,
            error_message=error_message,
            success=success,
            usage=usage,
            time_consuming_ms=time_consuming_ms,
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        
        return execution

    def list_executions(
        self,
        prompt_id: int,
        limit: int = 20,
    ) -> List[PromptExecution]:
        """List execution history"""
        return self.db.query(PromptExecution).filter(
            PromptExecution.prompt_id == prompt_id
        ).order_by(desc(PromptExecution.created_at)).limit(limit).all()

