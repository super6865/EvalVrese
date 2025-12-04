"""
Evaluator service
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
from app.models.evaluator import (
    Evaluator,
    EvaluatorVersion,
    EvaluatorType,
    EvaluatorVersionStatus,
    EvaluatorBoxType,
)
from app.domain.entity.evaluator_entity import (
    EvaluatorInputData,
    EvaluatorOutputData,
    EvaluatorResult,
)
from app.models.evaluator_record import EvaluatorRunStatus
from app.domain.entity.evaluator_types import LanguageType, ParseType
from app.services.prompt_evaluator_service import PromptEvaluatorService
from app.utils.code_builder import CodeBuilder
from app.utils.code_validator import CodeValidator
from app.utils.schema_validator import SchemaValidator
from app.infra.runtime.runtime_manager import RuntimeManager
from datetime import datetime
import json
import uuid


class EvaluatorService:
    def __init__(self, db: Session):
        self.db = db
        self.prompt_service = PromptEvaluatorService(db=db)
        self.runtime_manager = RuntimeManager()
        self.code_builder = CodeBuilder()
        self.code_validator = CodeValidator()
        self.schema_validator = SchemaValidator()

    # Evaluator CRUD
    def create_evaluator(
        self,
        name: str,
        evaluator_type: EvaluatorType,
        description: Optional[str] = None,
        builtin: bool = False,
        box_type: Optional[EvaluatorBoxType] = None,
        evaluator_info: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> Evaluator:
        """Create a new evaluator"""
        evaluator = Evaluator(
            name=name,
            description=description,
            evaluator_type=evaluator_type,
            builtin=builtin,
            box_type=box_type,
            evaluator_info=evaluator_info,
            tags=tags,
            created_by=created_by,
        )
        self.db.add(evaluator)
        self.db.commit()
        self.db.refresh(evaluator)
        return evaluator

    def create_evaluator_with_version(
        self,
        name: str,
        evaluator_type: EvaluatorType,
        description: Optional[str] = None,
        builtin: bool = False,
        box_type: Optional[EvaluatorBoxType] = None,
        evaluator_info: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, Any]] = None,
        current_version: Optional[Any] = None,  # CurrentVersionCreate from API
        created_by: Optional[str] = None,
    ) -> Evaluator:
        """Create evaluator and version(s) in one transaction (coze-loop style)"""
        from app.api.v1.evaluator import CurrentVersionCreate
        
        # Generate version number if not provided
        version_number = current_version.version if current_version and current_version.version else "v1.0"
        
        # Extract content based on evaluator type
        prompt_content = None
        code_content = None
        
        if current_version and current_version.evaluator_content:
            if evaluator_type == EvaluatorType.PROMPT:
                prompt_evaluator = current_version.evaluator_content.prompt_evaluator
                if not prompt_evaluator:
                    raise ValueError("prompt_evaluator is required for PROMPT evaluator")
                # Convert to dict if it's a Pydantic model
                if hasattr(prompt_evaluator, 'dict'):
                    prompt_content = prompt_evaluator.dict(exclude_none=True)
                elif isinstance(prompt_evaluator, dict):
                    prompt_content = prompt_evaluator
                else:
                    prompt_content = dict(prompt_evaluator)
            elif evaluator_type == EvaluatorType.CODE:
                code_evaluator = current_version.evaluator_content.code_evaluator
                if not code_evaluator:
                    raise ValueError("code_evaluator is required for CODE evaluator")
                # Convert to dict if it's a Pydantic model
                if hasattr(code_evaluator, 'dict'):
                    code_content = code_evaluator.dict(exclude_none=True)
                elif isinstance(code_evaluator, dict):
                    code_content = code_evaluator
                else:
                    code_content = dict(code_evaluator)
        
        # Create evaluator
        evaluator = Evaluator(
            name=name,
            description=description,
            evaluator_type=evaluator_type,
            builtin=builtin,
            box_type=box_type,
            evaluator_info=evaluator_info,
            tags=tags,
            created_by=created_by,
            latest_version=version_number,
        )
        self.db.add(evaluator)
        self.db.flush()  # Get evaluator ID without committing
        
        # Create first version (submitted version)
        submitted_version = EvaluatorVersion(
            evaluator_id=evaluator.id,
            version=version_number,
            description=current_version.description if current_version else None,
            status=EvaluatorVersionStatus.SUBMITTED.value,  # Use enum value instead of enum object
            prompt_content=prompt_content,
            code_content=code_content,
            input_schemas=current_version.input_schemas if current_version else None,
            output_schemas=current_version.output_schemas if current_version else None,
            created_by=created_by,
        )
        self.db.add(submitted_version)
        self.db.flush()
        
        # Commit transaction
        self.db.commit()
        self.db.refresh(evaluator)
        return evaluator

    def get_evaluator(self, evaluator_id: int) -> Optional[Evaluator]:
        return self.db.query(Evaluator).filter(Evaluator.id == evaluator_id).first()

    def list_evaluators(self, skip: int = 0, limit: int = 100, name: Optional[str] = None) -> Tuple[List[Evaluator], int]:
        query = self.db.query(Evaluator)
        # 如果提供了名称，进行模糊查询（不区分大小写）
        if name:
            query = query.filter(Evaluator.name.ilike(f"%{name}%"))
        total = query.count()
        evaluators = query.offset(skip).limit(limit).all()
        return evaluators, total

    def update_evaluator(
        self,
        evaluator_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Evaluator]:
        evaluator = self.get_evaluator(evaluator_id)
        if not evaluator:
            return None
        
        if name is not None:
            evaluator.name = name
        if description is not None:
            evaluator.description = description
        evaluator.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(evaluator)
        return evaluator

    def delete_evaluator(self, evaluator_id: int) -> bool:
        evaluator = self.get_evaluator(evaluator_id)
        if not evaluator:
            return False
        
        self.db.delete(evaluator)
        self.db.commit()
        return True

    # Version management
    def create_version(
        self,
        evaluator_id: int,
        version: str,
        content: Optional[Dict[str, Any]] = None,
        prompt_content: Optional[Dict[str, Any]] = None,
        code_content: Optional[Dict[str, Any]] = None,
        input_schemas: Optional[List[Dict[str, Any]]] = None,
        output_schemas: Optional[List[Dict[str, Any]]] = None,
        description: Optional[str] = None,
        status: EvaluatorVersionStatus = EvaluatorVersionStatus.DRAFT,
        created_by: Optional[str] = None,
    ) -> EvaluatorVersion:
        """Create a new evaluator version"""
        evaluator = self.get_evaluator(evaluator_id)
        if not evaluator:
            raise ValueError(f"Evaluator {evaluator_id} not found")
        
        # Determine content based on type
        if evaluator.evaluator_type == EvaluatorType.PROMPT:
            if not prompt_content:
                raise ValueError("prompt_content is required for PROMPT evaluator")
        elif evaluator.evaluator_type == EvaluatorType.CODE:
            if not code_content:
                raise ValueError("code_content is required for CODE evaluator")
        
        evaluator_version = EvaluatorVersion(
            evaluator_id=evaluator_id,
            version=version,
            description=description,
            status=status,
            content=content,  # Legacy field
            prompt_content=prompt_content,
            code_content=code_content,
            input_schemas=input_schemas,
            output_schemas=output_schemas,
            created_by=created_by,
        )
        self.db.add(evaluator_version)
        self.db.commit()
        
        # Update evaluator's latest version
        if evaluator:
            evaluator.latest_version = version
            self.db.commit()
        
        self.db.refresh(evaluator_version)
        return evaluator_version
    
    def submit_version(
        self,
        version_id: int,
        description: Optional[str] = None,
    ) -> Optional[EvaluatorVersion]:
        """提交评估器版本"""
        version = self.get_version(version_id)
        if not version:
            return None
        
        # Validate version before submission
        self._validate_version(version)
        
        version.status = EvaluatorVersionStatus.SUBMITTED.value  # Use enum value instead of enum object
        if description:
            version.description = description
        version.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(version)
        return version
    
    def _validate_version(self, version: EvaluatorVersion):
        """验证评估器版本"""
        evaluator = self.get_evaluator(version.evaluator_id)
        if not evaluator:
            raise ValueError("Evaluator not found")
        
        if evaluator.evaluator_type == EvaluatorType.CODE:
            # Validate code
            code_content = version.code_content or {}
            code = code_content.get("code_content", "")
            language = code_content.get("language_type", "Python")
            
            is_valid, error = self.code_validator.validate(code, LanguageType(language))
            if not is_valid:
                raise ValueError(f"Code validation failed: {error}")
        
        # Validate schemas if provided
        if version.input_schemas:
            # Basic schema validation
            pass

    def get_version(self, version_id: int) -> Optional[EvaluatorVersion]:
        """Get evaluator version by ID"""
        return self.db.query(EvaluatorVersion).filter(EvaluatorVersion.id == version_id).first()

    def list_versions(self, evaluator_id: int) -> List[EvaluatorVersion]:
        """List all versions of an evaluator"""
        return self.db.query(EvaluatorVersion).filter(
            EvaluatorVersion.evaluator_id == evaluator_id
        ).all()

    # Evaluation execution
    async def run_evaluator(
        self,
        version_id: int,
        input_data: EvaluatorInputData,
        experiment_id: Optional[int] = None,
        experiment_run_id: Optional[int] = None,
        dataset_item_id: Optional[int] = None,
        turn_id: Optional[int] = None,
        disable_tracing: bool = False,
    ) -> EvaluatorOutputData:
        """
        Run an evaluator on given inputs
        
        Args:
            version_id: Evaluator version ID
            input_data: Input data
            experiment_id: Experiment ID (optional)
            experiment_run_id: Experiment run ID (optional)
            dataset_item_id: Dataset item ID (optional)
            turn_id: Turn ID (optional)
            disable_tracing: Disable tracing
            
        Returns:
            Evaluation output data
        """
        version = self.get_version(version_id)
        if not version:
            raise ValueError(f"Evaluator version {version_id} not found")
        
        evaluator = self.get_evaluator(version.evaluator_id)
        if not evaluator:
            raise ValueError("Evaluator not found")
        
        # Validate input data
        if version.input_schemas:
            input_dict = input_data.dict() if hasattr(input_data, 'dict') else input_data
            is_valid, error = self.schema_validator.validate_evaluator_input(
                input_dict.get("input_fields", {}),
                version.input_schemas,
            )
            if not is_valid:
                from app.domain.entity.evaluator_entity import EvaluatorRunError
                return EvaluatorOutputData(
                    evaluator_run_error=EvaluatorRunError(
                        code=400,
                        message=f"Input validation failed: {error}",
                    )
                )
        
        # Generate trace ID
        trace_id = None if disable_tracing else str(uuid.uuid4())
        
        # Execute based on evaluator type
        if evaluator.evaluator_type == EvaluatorType.PROMPT:
            output_data = await self._run_prompt_evaluator(version, input_data)
        elif evaluator.evaluator_type == EvaluatorType.CODE:
            output_data = await self._run_code_evaluator(version, input_data)
        else:
            raise ValueError(f"Unknown evaluator type: {evaluator.evaluator_type}")
        
        return output_data
    
    async def _run_prompt_evaluator(
        self,
        version: EvaluatorVersion,
        input_data: EvaluatorInputData,
    ) -> EvaluatorOutputData:
        """运行 Prompt 评估器"""
        prompt_content = version.prompt_content or {}
        message_list = prompt_content.get("message_list", [])
        model_config = prompt_content.get("model_config", {})
        parse_type = ParseType(prompt_content.get("parse_type", "text"))
        prompt_suffix = prompt_content.get("prompt_suffix", "")
        tools = prompt_content.get("tools", [])
        
        return await self.prompt_service.run(
            message_list=message_list,
            model_config=model_config,
            input_data=input_data,
            parse_type=parse_type,
            prompt_suffix=prompt_suffix,
            tools=tools,
        )
    
    async def _run_code_evaluator(
        self,
        version: EvaluatorVersion,
        input_data: EvaluatorInputData,
    ) -> EvaluatorOutputData:
        """运行 Code 评估器"""
        code_content = version.code_content or {}
        code = code_content.get("code_content", "")
        language_type = LanguageType(code_content.get("language_type", "Python"))
        
        # Build code
        built_code = self.code_builder.build_code(input_data, code, language_type)
        
        # Get runtime
        runtime = self.runtime_manager.get_runtime(language_type)
        
        # Execute code
        result = await runtime.run_code(
            code=built_code,
            language=str(language_type),
            timeout_ms=5000,
        )
        
        # Parse result
        if not result.success:
            from app.domain.entity.evaluator_entity import EvaluatorRunError
            return EvaluatorOutputData(
                evaluator_run_error=EvaluatorRunError(
                    code=500,
                    message=result.error or result.stderr,
                ),
                stdout=result.stdout,
            )
        
        # Parse evaluation result
        try:
            import json
            eval_result = json.loads(result.ret_val) if result.ret_val else {}
        except:
            eval_result = {"score": None, "reason": result.ret_val}
        
        evaluator_result = EvaluatorResult(
            score=eval_result.get("score"),
            reasoning=eval_result.get("reason", ""),
        )
        
        return EvaluatorOutputData(
            evaluator_result=evaluator_result,
            stdout=result.stdout,
        )
    
    async def debug_evaluator(
        self,
        version_id: int,
        input_data: EvaluatorInputData,
    ) -> EvaluatorOutputData:
        """调试评估器"""
        return await self.run_evaluator(version_id, input_data, disable_tracing=True)

    async def batch_debug_evaluator(
        self,
        evaluator_type: str,
        evaluator_content: Dict[str, Any],
        input_data_list: List[EvaluatorInputData],
    ) -> List[EvaluatorOutputData]:
        """
        批量调试评估器，无需创建版本
        
        Args:
            evaluator_type: 评估器类型 ('prompt' or 'code')
            evaluator_content: 评估器内容 { code_evaluator: {...} } or { prompt_evaluator: {...} }
            input_data_list: 输入数据列表
            
        Returns:
            评估结果列表
        """
        results = []
        
        for input_data in input_data_list:
            try:
                if evaluator_type == 'code':
                    result = await self._run_code_evaluator_direct(
                        evaluator_content.get("code_evaluator", {}),
                        input_data,
                    )
                elif evaluator_type == 'prompt':
                    result = await self._run_prompt_evaluator_direct(
                        evaluator_content.get("prompt_evaluator", {}),
                        input_data,
                    )
                else:
                    from app.domain.entity.evaluator_entity import EvaluatorRunError
                    result = EvaluatorOutputData(
                        evaluator_run_error=EvaluatorRunError(
                            code=400,
                            message=f"Unknown evaluator type: {evaluator_type}",
                        )
                    )
                results.append(result)
            except Exception as e:
                # 单个失败不影响其他任务
                from app.domain.entity.evaluator_entity import EvaluatorRunError
                results.append(
                    EvaluatorOutputData(
                        evaluator_run_error=EvaluatorRunError(
                            code=500,
                            message=str(e),
                        )
                    )
                )
        
        return results
    
    async def _run_code_evaluator_direct(
        self,
        code_evaluator_content: Dict[str, Any],
        input_data: EvaluatorInputData,
    ) -> EvaluatorOutputData:
        """直接运行代码评估器，无需版本对象"""
        code = code_evaluator_content.get("code_content", "")
        language_type = LanguageType(code_evaluator_content.get("language_type", "Python"))
        
        # Build code
        built_code = self.code_builder.build_code(input_data, code, language_type)
        
        # Get runtime
        runtime = self.runtime_manager.get_runtime(language_type)
        
        # Execute code
        result = await runtime.run_code(
            code=built_code,
            language=str(language_type),
            timeout_ms=5000,
        )
        
        # Parse result
        if not result.success:
            from app.domain.entity.evaluator_entity import EvaluatorRunError
            return EvaluatorOutputData(
                evaluator_run_error=EvaluatorRunError(
                    code=500,
                    message=result.error or result.stderr,
                ),
                stdout=result.stdout,
            )
        
        # Parse evaluation result
        try:
            import json
            eval_result = json.loads(result.ret_val) if result.ret_val else {}
        except:
            eval_result = {"score": None, "reason": result.ret_val}
        
        evaluator_result = EvaluatorResult(
            score=eval_result.get("score"),
            reasoning=eval_result.get("reason", ""),
        )
        
        return EvaluatorOutputData(
            evaluator_result=evaluator_result,
            stdout=result.stdout,
        )
    
    async def _run_prompt_evaluator_direct(
        self,
        prompt_evaluator_content: Dict[str, Any],
        input_data: EvaluatorInputData,
    ) -> EvaluatorOutputData:
        """直接运行Prompt评估器，无需版本对象"""
        message_list = prompt_evaluator_content.get("message_list", [])
        model_config = prompt_evaluator_content.get("model_config", {})
        parse_type = ParseType(prompt_evaluator_content.get("parse_type", "text"))
        prompt_suffix = prompt_evaluator_content.get("prompt_suffix", "")
        tools = prompt_evaluator_content.get("tools", [])
        
        return await self.prompt_service.run(
            message_list=message_list,
            model_config=model_config,
            input_data=input_data,
            parse_type=parse_type,
            prompt_suffix=prompt_suffix,
            tools=tools,
        )

