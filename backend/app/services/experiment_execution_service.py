"""
Experiment execution service - handles experiment execution logic
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Tuple, Optional, List
from app.models.experiment import Experiment, ExperimentRun, ExperimentResult, ExperimentStatus, CeleryTaskLogLevel
from app.models.dataset import DatasetItem
from app.services.evaluator_service import EvaluatorService
from app.services.dataset_service import DatasetService
from app.services.evaluator_record_service import EvaluatorRecordService
from app.services.celery_log_service import CeleryLogService
from app.services.observability_service import ObservabilityService
from app.infra.tracer import DatabaseTracer
from app.domain.entity.evaluator_entity import EvaluatorInputData, Content
from app.domain.entity.evaluator_types import ContentType
from app.models.evaluator import EvaluatorType
from app.utils.logger_utils import log_celery_task_event
from datetime import datetime
import httpx
import json
import logging

logger = logging.getLogger(__name__)


def _pydantic_to_dict(obj):
    """Convert Pydantic model to dict, compatible with both v1 and v2"""
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    elif hasattr(obj, 'dict'):
        return obj.dict()
    elif isinstance(obj, dict):
        return obj
    else:
        return obj


def _parse_json_string_recursive(text: str, max_depth: int = 5) -> str:
    """Recursively parse JSON strings to extract actual text content"""
    if not text or not isinstance(text, str) or max_depth <= 0:
        return text
    
    try:
        if text.strip().startswith('{') and text.strip().endswith('}'):
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                for field in ["reason", "reasoning"]:
                    if field in parsed:
                        value = parsed[field]
                        if isinstance(value, str):
                            return _parse_json_string_recursive(value, max_depth - 1)
                        return str(value)
                for value in parsed.values():
                    if isinstance(value, str) and value.strip().startswith('{'):
                        return _parse_json_string_recursive(value, max_depth - 1)
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    
    return text


def _extract_actual_output(target_fields: Dict[str, Content], target_error: Optional[str] = None) -> str:
    """Extract actual_output string from target_fields"""
    if not target_fields or "actual_output" not in target_fields:
        return f"[评测对象调用失败] {target_error}" if target_error else ""
    
    content = target_fields["actual_output"]
    if isinstance(content, Content):
        return content.text or ""
    elif isinstance(content, dict):
        return content.get("text", "") or ""
    return str(content) or ""


def _create_experiment_result(
    experiment_id: int,
    run_id: int,
    dataset_item_id: int,
    evaluator_version_id: int,
    score: Optional[float],
    reason: str,
    actual_output: str,
    trace_id: str,
    error_message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> ExperimentResult:
    """Create an ExperimentResult object with common fields"""
    return ExperimentResult(
        experiment_id=experiment_id,
        run_id=run_id,
        dataset_item_id=dataset_item_id,
        evaluator_version_id=evaluator_version_id,
        score=score,
        reason=reason,
        details=details,
        actual_output=actual_output,
        error_message=error_message,
        trace_id=trace_id,
    )


class ExperimentExecutionService:
    """Service for executing experiments"""
    
    def __init__(self, db: Session):
        self.db = db
        self.evaluator_service = EvaluatorService(db)
        self.dataset_service = DatasetService(db)
        self.evaluator_record_service = EvaluatorRecordService(db)
        self.celery_log_service = CeleryLogService(db)
        self.observability_service = ObservabilityService(db)
        self.tracer = DatabaseTracer(db=db)
    
    async def _invoke_evaluation_target(self, config: Dict[str, Any], input_data: Dict[str, Any]) -> str:
        """Invoke evaluation target (API or function)"""
        target_type = config.get("type")
        if target_type == "api":
            api_url = config.get("api_url")
            api_method = config.get("api_method", "POST")
            api_headers = config.get("api_headers", {})
            api_body_template = config.get("api_body_template", {})
            input_mapping = config.get("input_mapping", {})
            
            # Map input_data according to input_mapping
            mapped_data = {}
            if input_mapping:
                for api_param, data_key in input_mapping.items():
                    if data_key in input_data:
                        mapped_data[api_param] = input_data[data_key]
            else:
                mapped_data = input_data
            
            # Build request body from template
            body = {}
            if api_body_template:
                body_str = json.dumps(api_body_template)
                for key, value in mapped_data.items():
                    body_str = body_str.replace(f"{{{key}}}", str(value))
                body = json.loads(body_str)
            else:
                body = mapped_data
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.request(
                    method=api_method,
                    url=api_url,
                    headers=api_headers,
                    json=body,
                )
                response.raise_for_status()
                result = response.json()
                return result.get("output") or result.get("result") or str(result)
        elif target_type == "function":
            # Function-based target (not implemented yet)
            raise NotImplementedError("Function-based evaluation target not implemented")
        else:
            raise ValueError(f"Unknown target type: {target_type}")
    
    async def _call_target(
        self,
        experiment: Experiment,
        item: DatasetItem,
        turn_fields: Dict[str, Content],
        trace_id: str,
        root_span_id: str,
    ) -> Tuple[Dict[str, Content], Optional[Any], Optional[str]]:
        """Call evaluation target and return target output fields"""
        logger.info(f"[CallTarget] Calling target for item {item.id}")
        
        target_span = self.tracer.start_span(
            name="evaluation_target",
            trace_id=trace_id,
            parent_span_id=root_span_id,
            kind="INTERNAL",
            attributes={
                "target_type": experiment.evaluation_target_config.get("type") if experiment.evaluation_target_config else "none",
            }
        )
        target_span.set_input({
            "target_config": experiment.evaluation_target_config,
            "turn_fields": {k: {"text": v.text if hasattr(v, 'text') else str(v)} for k, v in turn_fields.items()} if turn_fields else {},
            "data_content": item.data_content,
        })
        
        try:
            if experiment.evaluation_target_config and experiment.evaluation_target_config.get("type") != "none":
                logger.info(f"[CallTarget] Invoking evaluation target: {experiment.evaluation_target_config.get('type')}")
                
                input_data = {}
                if turn_fields:
                    for field_name, content in turn_fields.items():
                        if content and hasattr(content, 'text') and content.text:
                            input_data[field_name] = content.text
                        elif content:
                            input_data[field_name] = str(content)
                
                if not input_data:
                    if isinstance(item.data_content, dict):
                        input_data = item.data_content.copy()
                    else:
                        input_data = {"data": str(item.data_content)}
                
                actual_output = await self._invoke_evaluation_target(
                    experiment.evaluation_target_config,
                    input_data,
                )
                
                target_span.set_output(actual_output)
            else:
                actual_output = None
                if turn_fields:
                    if "output" in turn_fields:
                        actual_output = turn_fields["output"].text if hasattr(turn_fields["output"], "text") else str(turn_fields["output"])
                    elif "answer" in turn_fields:
                        actual_output = turn_fields["answer"].text if hasattr(turn_fields["answer"], "text") else str(turn_fields["answer"])
                    elif "reference_output" in turn_fields:
                        actual_output = turn_fields["reference_output"].text if hasattr(turn_fields["reference_output"], "text") else str(turn_fields["reference_output"])
                
                if not actual_output:
                    actual_output = item.data_content.get("output") or item.data_content.get("reference_output") or item.data_content.get("answer") or ""
            
            target_fields = {
                "actual_output": Content(
                    content_type=ContentType.TEXT,
                    text=str(actual_output)
                )
            }
            
            target_span.set_output({
                "actual_output": str(actual_output),
                "target_fields": {k: {"text": v.text if hasattr(v, 'text') else str(v)} for k, v in target_fields.items()} if target_fields else {},
            })
            
            return target_fields, target_span, None
        except Exception as e:
            error_message = f"Failed to call evaluation target: {str(e)}"
            logger.error(f"[CallTarget] Error calling target: {error_message}", exc_info=True)
            if target_span:
                target_span.set_error(e)
            
            evaluation_target_config = experiment.evaluation_target_config or {}
            target_type = evaluation_target_config.get('type', 'none')
            
            if target_type != 'none':
                error_output = f"[评测对象调用失败] {error_message}"
                target_fields = {
                    "actual_output": Content(
                        content_type=ContentType.TEXT,
                        text=error_output
                    )
                }
                return target_fields, target_span, error_message
            else:
                return {}, target_span, error_message

