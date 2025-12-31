"""
Experiment service
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
from app.models.experiment import (
    Experiment, ExperimentRun, ExperimentResult, ExperimentStatus,
    ExperimentType, RetryMode, CeleryTaskLog
)
from app.models.dataset import DatasetVersion, DatasetItem
from app.models.evaluator import EvaluatorVersion
from app.models.evaluator_record import EvaluatorRecord, EvaluatorRunStatus
from app.services.evaluator_service import EvaluatorService
from app.services.evaluator_record_service import EvaluatorRecordService
from app.services.dataset_service import DatasetService
from app.services.experiment_aggregate_service import ExperimentAggregateService
from app.services.experiment_result_service import ExperimentResultService
from app.services.observability_service import ObservabilityService
from app.services.celery_log_service import CeleryLogService
from app.infra.tracer import get_tracer, DatabaseTracer
from datetime import datetime
import httpx
import json
import copy
import logging
from app.domain.entity.evaluator_entity import EvaluatorInputData, Content
from app.domain.entity.evaluator_types import ContentType
from app.models.evaluator import EvaluatorType
from app.models.experiment import CeleryTaskLogLevel
from app.utils.logger_utils import log_celery_task_event

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


class ExperimentService:
    def __init__(self, db: Session):
        self.db = db
        self.evaluator_service = EvaluatorService(db)
        self.dataset_service = DatasetService(db)
        self.observability_service = ObservabilityService(db)
        self.evaluator_record_service = EvaluatorRecordService(db)
        self.celery_log_service = CeleryLogService(db)
        self.result_service = ExperimentResultService(db)
        # Use DatabaseTracer that automatically saves spans (like coze-loop)
        self.tracer = DatabaseTracer(db=db)

    # Experiment CRUD
    def create_experiment(
        self,
        name: str,
        dataset_version_id: int,
        evaluation_target_config: Optional[Dict[str, Any]] = None,
        evaluator_version_ids: List[int] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        group_id: Optional[int] = None,
    ) -> Experiment:
        """Create a new experiment"""
        if evaluation_target_config is None:
            evaluation_target_config = {
                "type": "none",  # No evaluation target, use dataset items directly
            }
        
        if evaluator_version_ids is None:
            evaluator_version_ids = []
        
        experiment = Experiment(
            name=name,
            description=description,
            dataset_version_id=dataset_version_id,
            evaluation_target_config=evaluation_target_config,
            evaluator_version_ids=evaluator_version_ids,
            created_by=created_by,
            group_id=group_id,
        )
        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    def get_experiment(self, experiment_id: int) -> Optional[Experiment]:
        """Get experiment by ID"""
        return self.db.query(Experiment).filter(Experiment.id == experiment_id).first()

    def list_experiments(self, skip: int = 0, limit: int = 100, name: Optional[str] = None, group_id: Optional[int] = None) -> Tuple[List[Experiment], int]:
        """List all experiments with pagination"""
        query = self.db.query(Experiment)
        # 如果提供了名称，进行模糊查询（不区分大小写）
        if name:
            query = query.filter(Experiment.name.ilike(f"%{name}%"))
        # 如果提供了 group_id，进行过滤
        if group_id is not None:
            query = query.filter(Experiment.group_id == group_id)
        total = query.count()
        experiments = query.offset(skip).limit(limit).all()
        return experiments, total

    def update_experiment(
        self,
        experiment_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Experiment]:
        """Update experiment"""
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            return None
        
        if name is not None:
            experiment.name = name
        if description is not None:
            experiment.description = description
        experiment.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    def delete_experiment(self, experiment_id: int) -> bool:
        """Delete experiment"""
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            return False
        
        self.db.query(CeleryTaskLog).filter(
            CeleryTaskLog.experiment_id == experiment_id
        ).delete()
        
        self.db.delete(experiment)
        self.db.commit()
        return True

    # Run management
    def create_run(self, experiment_id: int) -> ExperimentRun:
        """Create a new experiment run"""
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        existing_runs = self.db.query(ExperimentRun).filter(
            ExperimentRun.experiment_id == experiment_id
        ).all()
        run_number = len(existing_runs) + 1
        
        run = ExperimentRun(
            experiment_id=experiment_id,
            run_number=run_number,
            status=ExperimentStatus.PENDING.value,
            task_id=None,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: int) -> Optional[ExperimentRun]:
        """Get experiment run by ID"""
        return self.db.query(ExperimentRun).filter(ExperimentRun.id == run_id).first()

    def update_experiment_status(
        self,
        experiment_id: int,
        status: ExperimentStatus,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        """Update experiment status"""
        experiment = self.get_experiment(experiment_id)
        if experiment:
            experiment.status = status.value if isinstance(status, ExperimentStatus) else status
            if progress is not None:
                experiment.progress = progress
            experiment.updated_at = datetime.utcnow()
            self.db.commit()

    def update_run_status(
        self,
        run_id: int,
        status: ExperimentStatus,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        """Update run status"""
        run = self.get_run(run_id)
        if run:
            status_value = status.value if isinstance(status, ExperimentStatus) else status
            run.status = status_value
            if progress is not None:
                run.progress = progress
            if status == ExperimentStatus.RUNNING and not run.started_at:
                run.started_at = datetime.utcnow()
            if status in [ExperimentStatus.COMPLETED, ExperimentStatus.FAILED, ExperimentStatus.STOPPED]:
                run.completed_at = datetime.utcnow()
            if error_message:
                run.error_message = error_message
            run.updated_at = datetime.utcnow()
            self.db.commit()

    # Helper methods for field extraction (aligned with coze-loop logic)
    def _extract_turn_fields_from_data_content(self, data_content: Dict[str, Any]) -> Dict[str, Content]:
        """
        Extract fields from data_content's turns structure, matching coze-loop's logic.
        
        This function mimics coze-loop's behavior:
        - coze-loop: turnFields = gslice.ToMap(turn.FieldDataList, func(t *entity.FieldData) (string, *entity.Content) {
              return t.Name, t.Content
          })
        - If turns is None or empty, returns empty dict (like coze-loop)
        - Uses 'name' as key (consistent with coze-loop)
        
        Args:
            data_content: The dataset item's data_content dict
            
        Returns:
            Dict mapping field names to Content objects (name -> Content)
            
        Raises:
            ValueError: If turns structure is invalid or cannot be parsed
        """
        logger.info(f"[FieldExtraction] ========== Starting field extraction ==========")
        logger.info(f"[FieldExtraction] data_content type: {type(data_content)}")
        if isinstance(data_content, dict):
            logger.info(f"[FieldExtraction] data_content keys: {list(data_content.keys())}")
            logger.info(f"[FieldExtraction] data_content full content: {json.dumps(data_content, ensure_ascii=False, default=str)[:500]}")
        else:
            logger.warning(f"[FieldExtraction] data_content is not a dict: {type(data_content)}")
        
        # Get turns data from data_content
        turns_data = data_content.get("turns")
        logger.info(f"[FieldExtraction] turns_data type: {type(turns_data)}, is_none: {turns_data is None}")
        if turns_data is not None:
            logger.info(f"[FieldExtraction] turns_data value (first 500 chars): {str(turns_data)[:500]}")
        
        # If turns is None, return empty dict (consistent with coze-loop)
        if turns_data is None:
            logger.warning(f"[FieldExtraction] turns_data is None, returning empty dict. This may indicate missing data.")
            return {}
        
        # Parse turns_data into a list
        turns_list = None
        
        if isinstance(turns_data, list):
            turns_list = turns_data
            logger.debug(f"[FieldExtraction] turns_data is already a list, length: {len(turns_list)}")
        elif isinstance(turns_data, str):
            logger.debug(f"[FieldExtraction] turns_data is a string, attempting to parse JSON. Length: {len(turns_data)}")
            try:
                turns_list = json.loads(turns_data)
                logger.debug(f"[FieldExtraction] Successfully parsed turns string, type: {type(turns_list)}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"[FieldExtraction] Failed to parse turns string: {str(e)}")
                raise ValueError(f"Failed to parse turns string: {str(e)}")
        else:
            # Try to convert to string and parse
            logger.debug(f"[FieldExtraction] turns_data is unexpected type {type(turns_data)}, converting to string and parsing")
            try:
                turns_str = json.dumps(turns_data) if not isinstance(turns_data, str) else turns_data
                turns_list = json.loads(turns_str)
                logger.debug(f"[FieldExtraction] Successfully parsed after conversion, type: {type(turns_list)}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"[FieldExtraction] Failed to parse turns data (type: {type(turns_data)}): {str(e)}")
                raise ValueError(f"Failed to parse turns data (type: {type(turns_data)}): {str(e)}")
        
        # If turns_list is empty or not a list, return empty dict (consistent with coze-loop)
        if not isinstance(turns_list, list) or len(turns_list) == 0:
            logger.warning(f"[FieldExtraction] turns_list is empty or not a list (type: {type(turns_list)}, length: {len(turns_list) if isinstance(turns_list, list) else 'N/A'}), returning empty dict")
            return {}
        
        logger.info(f"[FieldExtraction] turns_list is a list with {len(turns_list)} turns")
        
        # Extract fields from first turn's field_data_list (coze-loop uses first turn)
        first_turn = turns_list[0]
        logger.info(f"[FieldExtraction] first_turn type: {type(first_turn)}, is_dict: {isinstance(first_turn, dict)}")
        if isinstance(first_turn, dict):
            logger.info(f"[FieldExtraction] first_turn keys: {list(first_turn.keys())}")
        if not isinstance(first_turn, dict):
            logger.error(f"[FieldExtraction] First turn is not a dict, got type: {type(first_turn)}, value: {str(first_turn)[:200]}")
            raise ValueError(f"First turn is not a dict, got type: {type(first_turn)}")
        
        field_data_list = first_turn.get("field_data_list")
        logger.info(f"[FieldExtraction] field_data_list type: {type(field_data_list)}, is_list: {isinstance(field_data_list, list) if field_data_list else False}")
        if field_data_list and isinstance(field_data_list, list):
            logger.info(f"[FieldExtraction] field_data_list length: {len(field_data_list)}")
            logger.info(f"[FieldExtraction] field_data_list content: {json.dumps(field_data_list, ensure_ascii=False, default=str)[:500]}")
        if not isinstance(field_data_list, list):
            # If field_data_list is missing or not a list, return empty dict (consistent with coze-loop)
            logger.warning(f"[FieldExtraction] field_data_list is missing or not a list (type: {type(field_data_list)}), returning empty dict")
            return {}
        
        # Build map: name -> Content (consistent with coze-loop)
        turn_fields = {}
        extracted_count = 0
        for field_data in field_data_list:
            if not isinstance(field_data, dict):
                logger.debug(f"[FieldExtraction] Skipping non-dict field_data: {type(field_data)}")
                continue
            
            # Use 'name' as key (consistent with coze-loop), fallback to 'key' if name is missing
            field_name = field_data.get("name") or field_data.get("key")
            if not field_name:
                logger.debug(f"[FieldExtraction] Skipping field_data with no name/key")
                continue
            
            field_content = field_data.get("content")
            if not field_content:
                logger.debug(f"[FieldExtraction] Skipping field_data '{field_name}' with no content")
                continue
            
            # Extract text from content (coze-loop uses Content.Text)
            text_value = None
            if isinstance(field_content, dict):
                text_value = field_content.get("text")
                if text_value is None:
                    text_value = str(field_content)
            elif isinstance(field_content, str):
                text_value = field_content
            else:
                text_value = str(field_content)
            
            if text_value is not None:
                turn_fields[field_name] = Content(
                    content_type=ContentType.TEXT,
                    text=text_value
                )
                extracted_count += 1
                logger.debug(f"[FieldExtraction] Extracted field '{field_name}' with text length: {len(str(text_value))}")
        
        logger.info(f"[FieldExtraction] Successfully extracted {extracted_count} fields from {len(field_data_list)} field_data items. Field names: {list(turn_fields.keys())}")
        if turn_fields:
            logger.info(f"[FieldExtraction] Extracted fields details:")
            for field_name, content in turn_fields.items():
                text_preview = (content.text or "")[:100] if hasattr(content, 'text') else str(content)[:100]
                logger.info(f"[FieldExtraction]   - {field_name}: {text_preview}...")
        else:
            logger.warning(f"[FieldExtraction] WARNING: No fields extracted! This may cause evaluation to fail.")
        
        # Final check: Ensure turns is NEVER in turn_fields
        if "turns" in turn_fields:
            logger.error(f"[FieldExtraction] CRITICAL: turns field found in turn_fields! This should never happen. Fields: {list(turn_fields.keys())}")
            raise RuntimeError(f"CRITICAL: turns field found in turn_fields. This indicates a bug in field extraction.")
        
        logger.info(f"[FieldExtraction] ========== Field extraction completed ==========")
        return turn_fields

    # Helper methods aligned with coze-loop's buildFieldsFromSource
    def _build_fields_from_source(
        self,
        source_fields: Dict[str, Content],
    ) -> Dict[str, Content]:
        """
        Build fields from source (simplified version without FieldConf).
        
        In coze-loop, this method uses FieldConf to map fields, but EvalVerse
        doesn't have FieldConf configuration, so we simply return all source_fields.
        
        This matches coze-loop's behavior where all fields from turnFields are used.
        
        Args:
            source_fields: Source fields map (name -> Content)
            
        Returns:
            Mapped fields (same as source_fields in simplified version)
        """
        # Simplified version: return all source fields
        # In coze-loop, this would filter/map based on FieldConf
        return source_fields.copy() if source_fields else {}

    # Helper methods aligned with coze-loop's buildEvaluatorInputData
    def _build_evaluator_input_data(
        self,
        evaluator_type: EvaluatorType,
        turn_fields: Dict[str, Content],
        target_fields: Dict[str, Content],
    ) -> EvaluatorInputData:
        """
        Build evaluator input data based on evaluator type, matching coze-loop's logic.
        
        In coze-loop:
        - Code evaluator: Separates evaluateDatasetFields and evaluateTargetOutputFields
        - Prompt evaluator: Merges all fields into InputFields
        
        Args:
            evaluator_type: Type of evaluator (PROMPT or CODE)
            turn_fields: Fields from dataset item's turn (name -> Content)
            target_fields: Fields from target output (name -> Content)
            
        Returns:
            EvaluatorInputData with appropriate fields set
        """
        logger.info(f"[BuildInputData] ========== Building input data ==========")
        logger.info(f"[BuildInputData] evaluator_type: {evaluator_type}")
        logger.info(f"[BuildInputData] turn_fields keys: {list(turn_fields.keys())}, count: {len(turn_fields)}")
        if turn_fields:
            for key, content in turn_fields.items():
                text_preview = (content.text or "")[:100] if hasattr(content, 'text') else str(content)[:100]
                logger.info(f"[BuildInputData]   turn_fields['{key}']: {text_preview}...")
        logger.info(f"[BuildInputData] target_fields keys: {list(target_fields.keys())}, count: {len(target_fields)}")
        if target_fields:
            for key, content in target_fields.items():
                text_preview = (content.text or "")[:100] if hasattr(content, 'text') else str(content)[:100]
                logger.info(f"[BuildInputData]   target_fields['{key}']: {text_preview}...")
        
        # Validate: Ensure turns is not in turn_fields or target_fields
        if "turns" in turn_fields:
            logger.error(f"[BuildInputData] CRITICAL: turns found in turn_fields! Keys: {list(turn_fields.keys())}")
            raise RuntimeError(f"CRITICAL: turns field found in turn_fields. This should never happen.")
        if "turns" in target_fields:
            logger.error(f"[BuildInputData] CRITICAL: turns found in target_fields! Keys: {list(target_fields.keys())}")
            raise RuntimeError(f"CRITICAL: turns field found in target_fields. This should never happen.")
        
        if evaluator_type == EvaluatorType.CODE:
            # Code evaluator: Separate fields
            evaluate_dataset_fields = self._build_fields_from_source(turn_fields)
            evaluate_target_output_fields = self._build_fields_from_source(target_fields)
            
            logger.info(f"[BuildInputData] Code evaluator - evaluate_dataset_fields keys: {list(evaluate_dataset_fields.keys())}, count: {len(evaluate_dataset_fields)}")
            if evaluate_dataset_fields:
                for key, content in evaluate_dataset_fields.items():
                    text_preview = (content.text or "")[:100] if hasattr(content, 'text') else str(content)[:100]
                    logger.info(f"[BuildInputData]   evaluate_dataset_fields['{key}']: {text_preview}...")
            logger.info(f"[BuildInputData] Code evaluator - evaluate_target_output_fields keys: {list(evaluate_target_output_fields.keys())}, count: {len(evaluate_target_output_fields)}")
            if evaluate_target_output_fields:
                for key, content in evaluate_target_output_fields.items():
                    text_preview = (content.text or "")[:100] if hasattr(content, 'text') else str(content)[:100]
                    logger.info(f"[BuildInputData]   evaluate_target_output_fields['{key}']: {text_preview}...")
            
            # Warn if fields are empty
            if not evaluate_dataset_fields and not evaluate_target_output_fields:
                logger.error(f"[BuildInputData] Code evaluator: Both evaluate_dataset_fields and evaluate_target_output_fields are empty!")
            elif not evaluate_dataset_fields:
                logger.warning(f"[BuildInputData] Code evaluator: evaluate_dataset_fields is empty!")
            elif not evaluate_target_output_fields:
                logger.warning(f"[BuildInputData] Code evaluator: evaluate_target_output_fields is empty!")
            
            input_data = EvaluatorInputData(
                history_messages=None,
                input_fields={},
                evaluate_dataset_fields=evaluate_dataset_fields,
                evaluate_target_output_fields=evaluate_target_output_fields,
            )
        else:
            # Prompt evaluator: Merge all fields into InputFields
            input_fields = {}
            
            # Check if we have evaluation target output (actual_output from target_fields)
            has_evaluation_target_output = False
            target_fields_data = self._build_fields_from_source(target_fields)
            if "actual_output" in target_fields_data and target_fields_data["actual_output"]:
                has_evaluation_target_output = True
                # Map actual_output to output field
                # This ensures that when there's an evaluation target, "output" field
                # uses the actual output from the target, not from the dataset
                input_fields["output"] = target_fields_data["actual_output"]
                logger.info(f"[BuildInputData] Has evaluation target output: mapped target_fields['actual_output'] to input_fields['output']")
            
            # Add target fields (including actual_output)
            for key, content in target_fields_data.items():
                input_fields[key] = content
            
            # Add dataset fields, but completely skip "output" if we have evaluation target output
            # This ensures that when there's an evaluation target, we use the target's output
            # and completely ignore the dataset's output field
            eval_set_fields_data = self._build_fields_from_source(turn_fields)
            for key, content in eval_set_fields_data.items():
                # If we have evaluation target output, completely skip "output" field from dataset
                if key == "output" and has_evaluation_target_output:
                    logger.info(f"[BuildInputData] Skipping turn_fields['output'] because evaluation target output is available (actual_output -> output)")
                    continue
                # Only add if not already in input_fields (target_fields take priority)
                if key not in input_fields:
                    input_fields[key] = content
            
            logger.info(f"[BuildInputData] Prompt evaluator - input_fields keys: {list(input_fields.keys())}, count: {len(input_fields)}")
            if input_fields:
                for key, content in input_fields.items():
                    text_preview = (content.text or "")[:100] if hasattr(content, 'text') else str(content)[:100]
                    logger.info(f"[BuildInputData]   input_fields['{key}']: {text_preview}...")
            
            # Warn if input_fields is empty
            if not input_fields:
                logger.error(f"[BuildInputData] Prompt evaluator: input_fields is empty!")
            
            input_data = EvaluatorInputData(
                history_messages=None,
                input_fields=input_fields,
                evaluate_dataset_fields=None,
                evaluate_target_output_fields=None,
            )
        
        # Final validation: Ensure turns is not in any field
        if input_data.evaluate_dataset_fields and "turns" in input_data.evaluate_dataset_fields:
            logger.error(f"[BuildInputData] CRITICAL: turns found in evaluate_dataset_fields!")
            raise RuntimeError(f"CRITICAL: turns field found in evaluate_dataset_fields.")
        if input_data.evaluate_target_output_fields and "turns" in input_data.evaluate_target_output_fields:
            logger.error(f"[BuildInputData] CRITICAL: turns found in evaluate_target_output_fields!")
            raise RuntimeError(f"CRITICAL: turns field found in evaluate_target_output_fields.")
        if input_data.input_fields and "turns" in input_data.input_fields:
            logger.error(f"[BuildInputData] CRITICAL: turns found in input_fields!")
            raise RuntimeError(f"CRITICAL: turns field found in input_fields.")
        
        logger.info(f"[BuildInputData] Successfully built input_data for {evaluator_type} evaluator")
        # Log final input_data structure
        if hasattr(input_data, 'dict'):
            input_data_dict = input_data.dict()
            logger.info(f"[BuildInputData] Final input_data structure: {json.dumps(input_data_dict, ensure_ascii=False, default=str)[:1000]}")
        logger.info(f"[BuildInputData] ========== Input data building completed ==========")
        return input_data

    # Helper method aligned with coze-loop's callTarget
    async def _call_target(
        self,
        experiment,
        item,
        turn_fields: Dict[str, Content],
        trace_id: str,
        root_span_id: str,
    ) -> Tuple[Dict[str, Content], Optional[Any], Optional[str]]:
        """
        Call evaluation target and return target output fields.
        
        This matches coze-loop's callTarget method, which:
        1. Builds turnFields from turn.FieldDataList
        2. Calls evalTargetService.ExecuteTarget
        3. Returns targetResult.OutputFields
        
        Args:
            experiment: Experiment object
            item: Dataset item
            turn_fields: Fields from dataset item's turn (name -> Content)
            trace_id: Trace ID for observability
            root_span_id: Root span ID
            
        Returns:
            Tuple of (target output fields (name -> Content), target_span if created, error_message if any)
        """
        logger.info(f"[CallTarget] ========== Calling target for item ==========")
        logger.info(f"[CallTarget] evaluation_target_config: {experiment.evaluation_target_config}")
        
        # Create span for evaluation target (always create for better observability)
        logger.info(f"[CallTarget] 🔵 Creating target span: trace_id={trace_id}, root_span_id={root_span_id}")
        target_span = self.tracer.start_span(
            name="evaluation_target",
            trace_id=trace_id,
            parent_span_id=root_span_id,
            kind="INTERNAL",
            attributes={
                "target_type": experiment.evaluation_target_config.get("type") if experiment.evaluation_target_config else "none",
            }
        )
        logger.info(f"[CallTarget] ✅ Target span created: span_id={target_span.span_id}, name={target_span.name}")
        # Set detailed input information
        target_span.set_input({
            "target_config": experiment.evaluation_target_config,
            "turn_fields": {k: {"text": v.text if hasattr(v, 'text') else str(v), "content_type": v.content_type.value if hasattr(v, 'content_type') else None} for k, v in turn_fields.items()} if turn_fields else {},
            "data_content": item.data_content,
        })
        
        try:
            # Get actual output from evaluation target
            if experiment.evaluation_target_config and experiment.evaluation_target_config.get("type") != "none":
                logger.info(f"[CallTarget] Invoking evaluation target: {experiment.evaluation_target_config.get('type')}")
                
                # Build input_data from turn_fields and data_content
                # ONLY use 'name' as keys in input_data (not 'key')
                # This simplifies the logic and avoids confusion between key and name
                input_data = {}
                
                # First, extract from turn_fields (uses 'name' as key)
                if turn_fields:
                    # Extract text values from turn_fields
                    for field_name, content in turn_fields.items():
                        if content and hasattr(content, 'text') and content.text:
                            input_data[field_name] = content.text
                        elif content:
                            input_data[field_name] = str(content)
                    logger.info(f"[CallTarget] Extracted {len(input_data)} fields from turn_fields: {list(input_data.keys())}")
                
                # Extract from data_content, but ONLY add by 'name' (not 'key')
                # We'll build key-to-name mapping separately for conversion purposes
                if isinstance(item.data_content, dict):
                    turns_data = item.data_content.get("turns")
                    if isinstance(turns_data, list) and len(turns_data) > 0:
                        first_turn = turns_data[0]
                        field_data_list = first_turn.get("field_data_list", [])
                        if isinstance(field_data_list, list):
                            logger.info(f"[CallTarget] Extracting fields from data_content.turns[0].field_data_list ({len(field_data_list)} fields)")
                            fields_added_by_name = 0
                            for field_data in field_data_list:
                                if isinstance(field_data, dict):
                                    field_key = field_data.get("key")
                                    field_name = field_data.get("name")
                                    field_content = field_data.get("content", {})
                                    
                                    # Extract text value
                                    text_value = None
                                    if isinstance(field_content, dict):
                                        text_value = field_content.get("text")
                                    elif isinstance(field_content, str):
                                        text_value = field_content
                                    
                                    if text_value is not None:
                                        text_str = str(text_value)
                                        # ONLY add by 'name' (if not already added from turn_fields)
                                        if field_name and field_name not in input_data:
                                            input_data[field_name] = text_str
                                            fields_added_by_name += 1
                                            logger.debug(f"[CallTarget] Added field by name '{field_name}'")
                            
                            logger.info(f"[CallTarget] Extracted {len(input_data)} field entries from data_content (using name only). Added {fields_added_by_name} fields by name.")
                    else:
                        logger.warning(f"[CallTarget] data_content.turns is not a list or is empty")
                else:
                    logger.warning(f"[CallTarget] item.data_content is not a dict: {type(item.data_content)}")
                
                # If still no fields, fallback to copying entire data_content
                if not input_data:
                    logger.warning(f"[CallTarget] ⚠️ No fields extracted from turn_fields or data_content.turns, falling back to data_content copy")
                    if isinstance(item.data_content, dict):
                        input_data = item.data_content.copy()
                    else:
                        input_data = {"data": str(item.data_content)}
                
                # Build key-to-name mapping for user_input_mapping conversion
                # This helps _invoke_prompt convert field 'key' (e.g., "输入") to 'name' (e.g., "input")
                key_to_name_mapping = {}
                if isinstance(item.data_content, dict):
                    turns_data = item.data_content.get("turns")
                    if isinstance(turns_data, list) and len(turns_data) > 0:
                        first_turn = turns_data[0]
                        field_data_list = first_turn.get("field_data_list", [])
                        if isinstance(field_data_list, list):
                            for field_data in field_data_list:
                                if isinstance(field_data, dict):
                                    field_key = field_data.get("key")
                                    field_name = field_data.get("name")
                                    if field_key and field_name:
                                        key_to_name_mapping[field_key] = field_name
                
                # Add key-to-name mapping to input_data as metadata (prefixed with _ to avoid conflicts)
                if key_to_name_mapping:
                    input_data["_key_to_name_mapping"] = key_to_name_mapping
                    logger.debug(f"[CallTarget] Added key-to-name mapping: {key_to_name_mapping}")
                
                logger.info(f"[CallTarget] Built input_data with keys: {list(input_data.keys())}")
                # Log detailed information about input_data values
                for key, value in input_data.items():
                    if key != "_key_to_name_mapping":  # Skip metadata
                        value_type = type(value).__name__
                        value_preview = str(value)[:100] if value else "None"
                        logger.debug(f"[CallTarget] input_data['{key}']: type={value_type}, value={value_preview}...")
                logger.debug(f"[CallTarget] input_data content (first 500 chars): {json.dumps(input_data, ensure_ascii=False, default=str)[:500]}")
                
                actual_output = await self._invoke_evaluation_target(
                    experiment.evaluation_target_config,
                    input_data,
                )
                
                logger.info(f"[CallTarget] Target returned output type: {type(actual_output)}, value (first 200 chars): {str(actual_output)[:200]}")
                
                # Validate that actual_output is not empty
                if not actual_output or (isinstance(actual_output, str) and not actual_output.strip()):
                    logger.warning(f"[CallTarget] Target returned empty output! This may indicate a problem with the evaluation target call.")
                
                target_span.set_output(actual_output)
            else:
                # No evaluation target, use dataset item's output field from turn_fields
                logger.info(f"[CallTarget] No evaluation target, using dataset item output field from turn_fields")
                # Try to get output from turn_fields (prefer 'output', then 'answer', then 'reference_output')
                actual_output = None
                if turn_fields:
                    if "output" in turn_fields:
                        actual_output = turn_fields["output"].text if hasattr(turn_fields["output"], "text") else str(turn_fields["output"])
                    elif "answer" in turn_fields:
                        actual_output = turn_fields["answer"].text if hasattr(turn_fields["answer"], "text") else str(turn_fields["answer"])
                    elif "reference_output" in turn_fields:
                        actual_output = turn_fields["reference_output"].text if hasattr(turn_fields["reference_output"], "text") else str(turn_fields["reference_output"])
                
                # Fallback to data_content if not found in turn_fields
                if not actual_output:
                    actual_output = item.data_content.get("output") or item.data_content.get("reference_output") or item.data_content.get("answer")
                
                # Last resort: use first field from turn_fields or empty string
                if not actual_output:
                    if turn_fields:
                        first_field = next(iter(turn_fields.values()))
                        actual_output = first_field.text if hasattr(first_field, "text") else str(first_field)
                    else:
                        actual_output = ""
                
                logger.info(f"[CallTarget] Using output from turn_fields, type: {type(actual_output)}, value (first 200 chars): {str(actual_output)[:200]}")
            
            # Convert actual_output to target_fields format (name -> Content)
            target_fields = {
                "actual_output": Content(
                    content_type=ContentType.TEXT,
                    text=str(actual_output)
                )
            }
            logger.info(f"[CallTarget] Target fields created: {list(target_fields.keys())}")
            
            # Set detailed output information
            target_span.set_output({
                "actual_output": str(actual_output),
                "target_fields": {k: {"text": v.text if hasattr(v, 'text') else str(v), "content_type": v.content_type.value if hasattr(v, 'content_type') else None} for k, v in target_fields.items()} if target_fields else {},
            })
            
            logger.info(f"[CallTarget] ========== Target call completed ==========")
            
            return target_fields, target_span, None
        except Exception as e:
            error_message = f"Failed to call evaluation target: {str(e)}"
            logger.error(f"[CallTarget] Error calling target: {error_message}", exc_info=True)
            if target_span:
                target_span.set_error(e)
            
            # If evaluation target is configured, return error message in target_fields
            # instead of empty dict, so caller knows not to use dataset output
            evaluation_target_config = experiment.evaluation_target_config or {}
            target_type = evaluation_target_config.get('type', 'none')
            
            if target_type != 'none':
                # Return error message in target_fields so evaluators can use it
                error_output = f"[评测对象调用失败] {error_message}"
                target_fields = {
                    "actual_output": Content(
                        content_type=ContentType.TEXT,
                        text=error_output
                    )
                }
                logger.warning(f"[CallTarget] Evaluation target failed, returning error message in target_fields: {error_output}")
                return target_fields, target_span, error_message
            else:
                # No evaluation target configured, return empty dict (will use dataset output)
                return {}, target_span, error_message

    # Helper method aligned with coze-loop's callEvaluators
    async def _call_evaluators(
        self,
        experiment,
        item,
        turn_fields: Dict[str, Content],
        target_fields: Dict[str, Content],
        target_error: Optional[str],
        trace_id: str,
        root_span_id: str,
        run_id: int,
        experiment_id: int,
    ) -> Dict[int, Any]:
        """
        Call all evaluators for the item, matching coze-loop's callEvaluators method.
        
        This matches coze-loop's callEvaluators method, which:
        1. Gets turnFields (already built)
        2. Gets targetFields (from targetResult)
        3. For each evaluator:
           - buildEvaluatorInputData(evaluatorType, ec, turnFields, targetFields)
           - Run evaluator
        
        Args:
            experiment: Experiment object
            item: Dataset item
            turn_fields: Fields from dataset item's turn (name -> Content)
            target_fields: Fields from target output (name -> Content)
            target_error: Error message if evaluation target call failed
            trace_id: Trace ID for observability
            root_span_id: Root span ID
            run_id: Experiment run ID
            experiment_id: Experiment ID
            
        Returns:
            Dict mapping evaluator_version_id to evaluator result
        """
        evaluator_results = {}
        logger.info(f"[CallEvaluators] ========== Starting evaluators call ==========")
        logger.info(f"[CallEvaluators] Evaluator version IDs: {experiment.evaluator_version_ids}")
        logger.info(f"[CallEvaluators] turn_fields keys: {list(turn_fields.keys())}, count: {len(turn_fields)}")
        logger.info(f"[CallEvaluators] target_fields keys: {list(target_fields.keys())}, count: {len(target_fields)}")
        logger.info(f"[CallEvaluators] target_error: {target_error}")
        logger.info(f"[CallEvaluators] Starting to process {len(experiment.evaluator_version_ids)} evaluators")
        
        # Get task_id from run if available
        run = self.get_run(run_id)
        task_id = run.task_id if run and run.task_id else "unknown"
        
        # Early return: If evaluation target failed and experiment has evaluation target configured,
        # skip evaluator calls and directly create failure results
        evaluation_target_config = experiment.evaluation_target_config or {}
        target_type = evaluation_target_config.get('type', 'none')
        
        if target_error and target_type != 'none':
            logger.warning(f"[CallEvaluators] Evaluation target call failed (target_error: {target_error}), and experiment has evaluation target configured (type: {target_type}). Skipping evaluator calls and creating failure results.")
            self.celery_log_service.create_log(
                experiment_id, run_id, task_id, CeleryTaskLogLevel.WARNING,
                f"评测对象调用失败，跳过评估器调用: {target_error}",
                "target_failed_skip_evaluators"
            )
            
            actual_output_str = _extract_actual_output(target_fields, target_error)
            
            # Create failure results for all evaluators
            for evaluator_version_id in experiment.evaluator_version_ids:
                logger.info(f"[CallEvaluators] Creating failure result for evaluator {evaluator_version_id} due to target failure")
                
                result = _create_experiment_result(
                    experiment_id=experiment_id,
                    run_id=run_id,
                    dataset_item_id=item.id,
                    evaluator_version_id=evaluator_version_id,
                    score=None,
                    reason=f"评测对象调用失败，跳过评估: {target_error}",
                    actual_output=actual_output_str,
                    trace_id=trace_id,
                    error_message=f"评测对象调用失败: {target_error}",
                )
                self.db.add(result)
                
                evaluator_results[evaluator_version_id] = {
                    "score": None,
                    "reason": f"评测对象调用失败，跳过评估: {target_error}",
                    "error_message": f"评测对象调用失败: {target_error}",
                }
            
            # Commit all failure results
            self.db.commit()
            logger.info(f"[CallEvaluators] Created {len(evaluator_results)} failure results due to target failure")
            return evaluator_results
        
        # Run all evaluators
        for evaluator_version_id in experiment.evaluator_version_ids:
            logger.info(f"[CallEvaluators] Processing evaluator {evaluator_version_id}")
            
            # Log evaluator start
            self.celery_log_service.create_log(
                experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO,
                f"处理评估器 {evaluator_version_id}",
                "evaluator_start"
            )
            # Create span for evaluator execution
            logger.info(f"[CallEvaluators] 🔵 Creating evaluator span: evaluator_version_id={evaluator_version_id}, trace_id={trace_id}, root_span_id={root_span_id}")
            evaluator_span = self.tracer.start_span(
                name=f"evaluator_{evaluator_version_id}",
                trace_id=trace_id,
                parent_span_id=root_span_id,
                kind="INTERNAL",
                attributes={
                    "evaluator_version_id": evaluator_version_id,
                }
            )
            logger.info(f"[CallEvaluators] ✅ Evaluator span created: span_id={evaluator_span.span_id}, name={evaluator_span.name}")
            
            try:
                logger.debug(f"[CallEvaluators] Processing evaluator {evaluator_version_id} for item {item.id}")
                
                # Get evaluator type
                evaluator_version = self.evaluator_service.get_version(evaluator_version_id)
                if not evaluator_version:
                    logger.error(f"[CallEvaluators] Evaluator version {evaluator_version_id} not found")
                    raise ValueError(f"Evaluator version {evaluator_version_id} not found")
                
                evaluator = evaluator_version.evaluator
                if not evaluator:
                    logger.error(f"[CallEvaluators] Evaluator for version {evaluator_version_id} not found")
                    raise ValueError(f"Evaluator for version {evaluator_version_id} not found")
                
                evaluator_type = EvaluatorType(evaluator.evaluator_type)
                logger.debug(f"[CallEvaluators] Evaluator type: {evaluator_type}")
                
                # Validate input: Check if turn_fields and target_fields are empty
                if not turn_fields and not target_fields:
                    logger.error(f"[CallEvaluators] Both turn_fields and target_fields are empty for item {item.id}, evaluator {evaluator_version_id}")
                    raise ValueError(f"Cannot evaluate item {item.id}: both turn_fields and target_fields are empty")
                
                # Build EvaluatorInputData based on evaluator type (matching coze-loop)
                input_data = self._build_evaluator_input_data(
                    evaluator_type=evaluator_type,
                    turn_fields=turn_fields,
                    target_fields=target_fields,
                )
                
                # Record evaluator input data
                input_data_dict = _pydantic_to_dict(input_data)
                evaluator_name = evaluator.name if evaluator else f"评估器 {evaluator_version_id}"
                evaluator_type_display = "代码评估器" if evaluator_type == EvaluatorType.CODE else "提示词评估器"
                self.celery_log_service.create_log(
                    experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO,
                    f"构建评估器输入数据 ({evaluator_name}, {evaluator_type_display})",
                    "evaluator_input_built",
                    input_data={
                        "evaluator_version_id": evaluator_version_id,
                        "evaluator_type": evaluator_type.value,
                        "evaluator_name": evaluator.name if evaluator else None,
                        "turn_fields": {k: {"text": v.text if hasattr(v, 'text') else str(v)} for k, v in turn_fields.items()} if turn_fields else {},
                        "target_fields": {k: {"text": v.text if hasattr(v, 'text') else str(v)} for k, v in target_fields.items()} if target_fields else {},
                        "input_data": input_data_dict,
                    }
                )
                
                # Validate input_data based on evaluator type
                final_code = None
                if evaluator_type == EvaluatorType.CODE:
                    if not input_data.evaluate_dataset_fields and not input_data.evaluate_target_output_fields:
                        logger.error(f"[CallEvaluators] Code evaluator {evaluator_version_id}: Both evaluate_dataset_fields and evaluate_target_output_fields are empty!")
                        raise ValueError(f"Code evaluator {evaluator_version_id} requires at least one of evaluate_dataset_fields or evaluate_target_output_fields")
                    
                    # Build final code (with variables replaced) for logging
                    code_content = evaluator_version.code_content or {}
                    code = code_content.get("code_content", "")
                    language_type_str = code_content.get("language_type", "Python")
                    from app.domain.entity.evaluator_types import LanguageType
                    language_type = LanguageType(language_type_str)
                    
                    # Build code using the same method as evaluator_service
                    final_code = self.evaluator_service.code_builder.build_code(input_data, code, language_type)
                    
                    # Log final code
                    self.celery_log_service.create_log(
                        experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO,
                        f"评估器完整代码 ({evaluator_name})",
                        "evaluator_final_code",
                        input_data={
                            "evaluator_version_id": evaluator_version_id,
                            "evaluator_name": evaluator.name if evaluator else None,
                            "language_type": language_type_str,
                            "original_code": code,
                            "final_code": final_code,
                        }
                    )
                else:
                    if not input_data.input_fields:
                        logger.error(f"[CallEvaluators] Prompt evaluator {evaluator_version_id}: input_fields is empty!")
                        raise ValueError(f"Prompt evaluator {evaluator_version_id} requires input_fields")
                
                # Strict validation: Ensure turns is NEVER in evaluate_dataset_fields
                if input_data.evaluate_dataset_fields and "turns" in input_data.evaluate_dataset_fields:
                    logger.error(f"[CallEvaluators] CRITICAL: turns field found in evaluate_dataset_fields for item {item.id}, evaluator {evaluator_version_id}")
                    raise RuntimeError(
                        f"CRITICAL: turns field found in evaluate_dataset_fields for item {item.id}. "
                        f"This indicates a bug in field extraction. "
                        f"Fields: {list(input_data.evaluate_dataset_fields.keys())}"
                    )
                            
                # Final validation before passing to evaluator: Ensure turns is NEVER in any field
                # This is a critical check - if turns is found, it means there's a bug
                assert "turns" not in (input_data.evaluate_dataset_fields or {}), (
                    f"CRITICAL: turns field found in evaluate_dataset_fields for item {item.id}, evaluator {evaluator_version_id}"
                )
                assert "turns" not in (input_data.evaluate_target_output_fields or {}), (
                    f"CRITICAL: turns field found in evaluate_target_output_fields for item {item.id}, evaluator {evaluator_version_id}"
                )
                assert "turns" not in (input_data.input_fields or {}), (
                    f"CRITICAL: turns field found in input_fields for item {item.id}, evaluator {evaluator_version_id}"
                )
                
                logger.info(f"[CallEvaluators] Input data validated for evaluator {evaluator_version_id}, item {item.id}")
                
                # Record prompt information for LLM evaluators
                final_messages = None
                if evaluator_type == EvaluatorType.PROMPT:
                    prompt_content = evaluator_version.prompt_content or {}
                    message_list = prompt_content.get("message_list", [])
                    model_config = prompt_content.get("model_config", {})
                    parse_type = prompt_content.get("parse_type", "text")
                    prompt_suffix = prompt_content.get("prompt_suffix", "")
                    
                    # Build final messages (with variables replaced) for logging
                    from app.services.prompt_evaluator_service import PromptEvaluatorService
                    prompt_service = PromptEvaluatorService(self.db)
                    final_messages = prompt_service._build_messages(message_list, input_data, prompt_suffix)
                    
                    # Convert messages to dict format for logging
                    final_messages_dict = [
                        {
                            "role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role),
                            "content": msg.content.text if hasattr(msg.content, 'text') else str(msg.content)
                        }
                        for msg in final_messages
                    ]
                    
                    # Update evaluator_input_built log with final messages
                    # We need to update the previous log entry, but since we can't modify it,
                    # we'll add a new log entry with the final prompt
                    self.celery_log_service.create_log(
                        experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO,
                        f"评估器完整Prompt ({evaluator_name})",
                        "evaluator_final_prompt",
                        input_data={
                            "evaluator_version_id": evaluator_version_id,
                            "evaluator_name": evaluator.name if evaluator else None,
                            "message_list_template": message_list,
                            "prompt_suffix": prompt_suffix,
                            "final_messages": final_messages_dict,
                        }
                    )
                    
                    # Record prompt information to span attributes
                    evaluator_span.set_attribute("llm.prompt.message_list", message_list)
                    evaluator_span.set_attribute("llm.prompt.model_config", {
                        "provider": model_config.get("provider"),
                        "model": model_config.get("model") or model_config.get("model_version"),
                        "temperature": model_config.get("temperature"),
                        "max_tokens": model_config.get("max_tokens"),
                        "model_config_id": model_config.get("model_config_id"),
                    })
                    evaluator_span.set_attribute("llm.prompt.parse_type", parse_type)
                    if prompt_suffix:
                        evaluator_span.set_attribute("llm.prompt.prompt_suffix", prompt_suffix)
                
                # Set detailed span input
                input_data_dict = _pydantic_to_dict(input_data)
                evaluator_span.set_input({
                    "evaluator_version_id": evaluator_version_id,
                    "evaluator_type": evaluator_type.value,
                    "evaluator_name": evaluator.name if evaluator else None,
                    "input_data": input_data_dict,
                    "turn_fields_keys": list(turn_fields.keys()) if turn_fields else [],
                    "target_fields_keys": list(target_fields.keys()) if target_fields else [],
                })
                # Add event for input data preparation
                evaluator_span.add_event("input_data_prepared", attributes={
                    "evaluator_type": evaluator_type.value,
                    "has_dataset_fields": bool(input_data.evaluate_dataset_fields),
                    "has_target_fields": bool(input_data.evaluate_target_output_fields),
                    "has_input_fields": bool(input_data.input_fields),
                })
                
                # Run evaluator
                logger.debug(f"[CallEvaluators] Running evaluator {evaluator_version_id} for item {item.id}")
                eval_result = await self.evaluator_service.run_evaluator(
                    version_id=evaluator_version_id,
                    input_data=input_data,
                    experiment_id=experiment_id,
                    experiment_run_id=run_id,
                    dataset_item_id=item.id,
                )
                logger.debug(f"[CallEvaluators] Evaluator {evaluator_version_id} execution completed for item {item.id}")
                
                # Create evaluator record
                try:
                    status = EvaluatorRunStatus.SUCCESS if eval_result.evaluator_result else EvaluatorRunStatus.FAIL
                    input_data_dict = _pydantic_to_dict(input_data)
                    output_data_dict = _pydantic_to_dict(eval_result)
                    
                    # Log evaluator_usage before saving
                    evaluator_usage = output_data_dict.get("evaluator_usage")
                    logger.info(f"[CallEvaluators] Creating evaluator record for evaluator {evaluator_version_id}, item {item.id}")
                    logger.info(f"[CallEvaluators] evaluator_usage: {evaluator_usage}")
                    if evaluator_usage:
                        logger.info(f"[CallEvaluators] input_tokens: {evaluator_usage.get('input_tokens')}, output_tokens: {evaluator_usage.get('output_tokens')}")
                    
                    self.evaluator_record_service.create_record(
                        evaluator_version_id=evaluator_version_id,
                        input_data=input_data_dict,
                        output_data=output_data_dict,
                        status=status,
                        experiment_id=experiment_id,
                        experiment_run_id=run_id,
                        dataset_item_id=item.id,
                        trace_id=trace_id,
                    )
                    logger.info(f"[CallEvaluators] ✅ Evaluator record created successfully for evaluator {evaluator_version_id}, item {item.id}")
                except Exception as e:
                    logger.error(f"[CallEvaluators] ❌ Failed to create evaluator record for evaluator {evaluator_version_id}, item {item.id}: {str(e)}", exc_info=True)
                
                # Extract result from EvaluatorOutputData
                score = None
                reason = None
                error_message = None
                
                # Add debug info
                debug_info = {
                    "evaluator_version_id": evaluator_version_id,
                    "eval_result_type": str(type(eval_result)),
                    "has_evaluator_result": eval_result.evaluator_result is not None,
                    "has_evaluator_run_error": eval_result.evaluator_run_error is not None,
                }
                if hasattr(eval_result, 'dict'):
                    debug_info["eval_result"] = eval_result.dict()
                else:
                    debug_info["eval_result"] = str(eval_result)
                
                logger.info(f"[CallEvaluators] Evaluator {evaluator_version_id} result debug info:")
                logger.info(f"[CallEvaluators]   - has_evaluator_result: {debug_info.get('has_evaluator_result')}")
                logger.info(f"[CallEvaluators]   - has_evaluator_run_error: {debug_info.get('has_evaluator_run_error')}")
                if hasattr(eval_result, 'dict'):
                    result_dict = eval_result.dict()
                    logger.info(f"[CallEvaluators]   - Full result: {json.dumps(result_dict, ensure_ascii=False, default=str)[:1000]}")
                
                # Initialize variables
                score = None
                reason = None
                error_message = None
                
                # Check for evaluator run error first
                if eval_result.evaluator_run_error:
                    error_message = f"Evaluator execution error: {eval_result.evaluator_run_error.message}"
                    logger.error(f"[CallEvaluators] Evaluator {evaluator_version_id} execution error: {error_message}")
                    reason = error_message
                elif eval_result.evaluator_result:
                    score = eval_result.evaluator_result.score
                    reason = eval_result.evaluator_result.reasoning
                    
                    # Recursively parse reason if it's a JSON string to avoid double encoding
                    if reason and isinstance(reason, str):
                        reason = _parse_json_string_recursive(reason)
                    
                    logger.info(f"[CallEvaluators] Evaluator {evaluator_version_id} result:")
                    logger.info(f"[CallEvaluators]   - score: {score} (type: {type(score)})")
                    logger.info(f"[CallEvaluators]   - reason: {reason[:200] if reason else 'None'}...")
                    logger.info(f"[CallEvaluators]   - has_reason: {reason is not None}")
                    
                    # Check if score is None
                    if score is None:
                        error_message = "Failed to parse score from evaluator output"
                        logger.error(f"[CallEvaluators] Evaluator {evaluator_version_id} returned score=None!")
                        logger.error(f"[CallEvaluators] Reason from evaluator: {reason}")
                        logger.error(f"[CallEvaluators] Full debug info: {json.dumps(debug_info, default=str, indent=2)}")
                        # Append debug info to reason
                        debug_str = json.dumps(debug_info, default=str, indent=2)
                        if reason:
                            reason = f"Error: {error_message}\n\nRaw Output: {reason}\n\nDebug Info: {debug_str}"
                        else:
                            reason = f"Error: {error_message}\n\nDebug Info: {debug_str}"
                    else:
                        logger.info(f"[CallEvaluators] ✅ Evaluator {evaluator_version_id} successfully returned score: {score}")
                        
                        # Log evaluator result with detailed output
                        eval_result_dict = _pydantic_to_dict(eval_result)
                        # Clean up evaluator_result to avoid double encoding
                        evaluator_result_clean = eval_result_dict.get("evaluator_result")
                        if evaluator_result_clean and isinstance(evaluator_result_clean, dict):
                            # Recursively parse reasoning if it's a JSON string
                            if "reasoning" in evaluator_result_clean and isinstance(evaluator_result_clean["reasoning"], str):
                                evaluator_result_clean["reasoning"] = _parse_json_string_recursive(evaluator_result_clean["reasoning"])
                            # Also check reason field
                            if "reason" in evaluator_result_clean and isinstance(evaluator_result_clean["reason"], str):
                                evaluator_result_clean["reason"] = _parse_json_string_recursive(evaluator_result_clean["reason"])
                        
                        self.celery_log_service.create_log(
                            experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO,
                            f"评估器返回分数: {score}",
                            "evaluator_result",
                            output_data={
                                "score": score,
                                "reason": reason,
                                "evaluator_result": evaluator_result_clean,
                                "evaluator_usage": eval_result_dict.get("evaluator_usage"),
                                "time_consuming_ms": eval_result_dict.get("time_consuming_ms"),
                            }
                        )
                else:
                    # No result object at all
                    error_message = "Evaluator returned no result object"
                    logger.error(f"[CallEvaluators] ❌ Evaluator {evaluator_version_id} returned no result object!")
                    logger.error(f"[CallEvaluators] Full debug info: {json.dumps(debug_info, default=str, indent=2)}")
                    logger.error(f"[CallEvaluators] eval_result type: {type(eval_result)}")
                    logger.error(f"[CallEvaluators] eval_result attributes: {dir(eval_result)}")
                    debug_str = json.dumps(debug_info, default=str, indent=2)
                    reason = f"Error: {error_message}\n\nDebug Info: {debug_str}"
                
                # Record LLM response information for prompt evaluators
                if evaluator_type == EvaluatorType.PROMPT and eval_result:
                    eval_result_dict = _pydantic_to_dict(eval_result)
                    
                    # Record response content
                    if eval_result.evaluator_result:
                        evaluator_span.set_attribute("llm.response.score", eval_result.evaluator_result.score)
                        evaluator_span.set_attribute("llm.response.reasoning", eval_result.evaluator_result.reasoning)
                    
                    # Record token usage
                    evaluator_usage = eval_result_dict.get("evaluator_usage", {})
                    if evaluator_usage:
                        evaluator_span.set_attribute("llm.usage.input_tokens", evaluator_usage.get("input_tokens", 0))
                        evaluator_span.set_attribute("llm.usage.output_tokens", evaluator_usage.get("output_tokens", 0))
                    
                    # Record time consuming
                    if eval_result.time_consuming_ms:
                        evaluator_span.set_attribute("llm.time_consuming_ms", eval_result.time_consuming_ms)
                    
                    # Record error if any
                    if eval_result.evaluator_run_error:
                        evaluator_span.set_attribute("llm.error.code", eval_result.evaluator_run_error.code)
                        evaluator_span.set_attribute("llm.error.message", eval_result.evaluator_run_error.message)
                
                # Set detailed span output
                eval_result_dict = _pydantic_to_dict(eval_result)
                evaluator_span.set_output({
                    "score": score,
                    "reason": reason,
                    "error": error_message,
                    "result": eval_result_dict,
                    "has_error": error_message is not None,
                    "evaluator_version_id": evaluator_version_id,
                })
                # Add event for evaluation completion
                evaluator_span.add_event("evaluation_completed", attributes={
                    "score": score,
                    "has_error": error_message is not None,
                })
                
                actual_output_str = _extract_actual_output(target_fields, target_error)
                if target_error and not actual_output_str:
                    logger.warning(f"[CallEvaluators] Target call failed for item {item.id}, saving error to actual_output: {target_error}")
                
                result = _create_experiment_result(
                    experiment_id=experiment_id,
                    run_id=run_id,
                    dataset_item_id=item.id,
                    evaluator_version_id=evaluator_version_id,
                    score=score,
                    reason=reason,
                    actual_output=actual_output_str,
                    trace_id=trace_id,
                    error_message=error_message,
                    details=eval_result.dict() if hasattr(eval_result, 'dict') else None,
                )
                self.db.add(result)
                self.db.commit()
                
                evaluator_results[evaluator_version_id] = {
                    "score": score,
                    "reason": reason,
                    "error_message": error_message,
                }
                logger.info(f"[CallEvaluators] ✅ Evaluator {evaluator_version_id} result saved - score: {score}, has_error: {error_message is not None}")
                logger.info(f"[CallEvaluators] ========== Evaluator {evaluator_version_id} processing completed ==========")
                
                # Log evaluator completion with detailed output
                eval_result_dict = _pydantic_to_dict(eval_result) if hasattr(eval_result, 'dict') else {}
                # Clean up evaluator_result to avoid double encoding
                evaluator_result_clean = eval_result_dict.get("evaluator_result")
                if evaluator_result_clean and isinstance(evaluator_result_clean, dict):
                    # Recursively parse reasoning if it's a JSON string
                    if "reasoning" in evaluator_result_clean and isinstance(evaluator_result_clean["reasoning"], str):
                        evaluator_result_clean["reasoning"] = _parse_json_string_recursive(evaluator_result_clean["reasoning"])
                    # Also check reason field
                    if "reason" in evaluator_result_clean and isinstance(evaluator_result_clean["reason"], str):
                        evaluator_result_clean["reason"] = _parse_json_string_recursive(evaluator_result_clean["reason"])
                
                self.celery_log_service.create_log(
                    experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO,
                    f"评估器处理完成，分数: {score}" + (f"，错误: {error_message}" if error_message else ""),
                    "evaluator_saved",
                    output_data={
                        "evaluator_version_id": evaluator_version_id,
                        "score": score,
                        "reason": reason,
                        "error_message": error_message,
                        "evaluator_result": evaluator_result_clean,
                        "evaluator_usage": eval_result_dict.get("evaluator_usage"),
                        "time_consuming_ms": eval_result_dict.get("time_consuming_ms"),
                        "evaluator_run_error": eval_result_dict.get("evaluator_run_error"),
                    }
                )
                
            except Exception as e:
                if evaluator_span:
                    evaluator_span.set_error(e)
                
                logger.error(f"[CallEvaluators] Error executing evaluator {evaluator_version_id} for item {item.id}: {str(e)}", exc_info=True)
                
                # Log evaluator error
                self.celery_log_service.create_log(
                    experiment_id, run_id, task_id, CeleryTaskLogLevel.ERROR,
                    f"评估器执行失败: {str(e)}",
                    "evaluator_error"
                )
                
                actual_output_str = _extract_actual_output(target_fields, target_error)
                if target_error and not actual_output_str:
                    logger.warning(f"[CallEvaluators] Target call failed for item {item.id}, saving error to actual_output: {target_error}")
                
                result = _create_experiment_result(
                    experiment_id=experiment_id,
                    run_id=run_id,
                    dataset_item_id=item.id,
                    evaluator_version_id=evaluator_version_id,
                    score=None,
                    reason=str(e),
                    actual_output=actual_output_str,
                    trace_id=trace_id,
                    error_message=str(e),
                )
                self.db.add(result)
                self.db.commit()
                
                evaluator_results[evaluator_version_id] = {
                    "score": None,
                    "reason": str(e),
                    "error_message": str(e),
                }
            finally:
                # Finish span immediately (auto-saved by DatabaseTracer)
                # This follows coze-loop's pattern: each span is saved when finished
                if evaluator_span:
                    logger.info(f"[CallEvaluators] 🔄 About to finish evaluator span: span_id={evaluator_span.span_id}, evaluator_version_id={evaluator_version_id}, trace_id={trace_id}, parent_span_id={root_span_id}, has_db={self.db is not None}")
                    self.tracer.finish_span(evaluator_span, db=self.db)
                    logger.info(f"[CallEvaluators] ✅ Evaluator span finish_span() called: span_id={evaluator_span.span_id}, evaluator_version_id={evaluator_version_id}")
                    
                    # Verify evaluator span was saved
                    from app.services.observability_service import ObservabilityService
                    obs_service = ObservabilityService(self.db)
                    saved_evaluator_span = obs_service.get_span(evaluator_span.span_id)
                    if saved_evaluator_span:
                        logger.info(f"[CallEvaluators] ✅ VERIFIED: Evaluator span {evaluator_span.span_id} (evaluator_version_id={evaluator_version_id}) found in database")
                    else:
                        logger.error(f"[CallEvaluators] ❌ CRITICAL: Evaluator span {evaluator_span.span_id} (evaluator_version_id={evaluator_version_id}) NOT found in database after save!")
                else:
                    logger.error(f"[CallEvaluators] ❌ CRITICAL: evaluator_span is None for evaluator_version_id={evaluator_version_id}!")
        
        logger.info(f"[CallEvaluators] Completed processing {len(evaluator_results)} evaluators")
        return evaluator_results

    # Execution
    async def execute_experiment(self, experiment_id: int, run_id: int):
        """Execute an experiment"""
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        run = self.get_run(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        # Check if experiment or run is already stopped before starting
        if experiment.status == ExperimentStatus.STOPPED:
            logger.info(f"[ExecuteExperiment] Experiment {experiment_id} is already stopped, aborting execution")
            return
        
        if run.status == ExperimentStatus.STOPPED:
            logger.info(f"[ExecuteExperiment] Run {run_id} is already stopped, aborting execution")
            return
        
        task_id = run.task_id or "unknown"
        
        # Update status to running and reset progress to 0
        # This ensures progress bar starts from 0 on each new execution
        self.update_run_status(run_id, ExperimentStatus.RUNNING, progress=0)
        self.update_experiment_status(experiment_id, ExperimentStatus.RUNNING, progress=0)
        
        try:
            # Get dataset version and items
            dataset_version = self.dataset_service.get_version(experiment.dataset_version_id)
            if not dataset_version:
                raise ValueError(f"Dataset version {experiment.dataset_version_id} not found")
            
            # Get dataset_id from dataset_version
            dataset_id = dataset_version.dataset_id
            items, total_count = self.dataset_service.list_items(dataset_id=dataset_id, version_id=experiment.dataset_version_id, skip=0, limit=10000)
            total_items = total_count
            
            log_celery_task_event(
                self.celery_log_service, experiment_id, run_id, task_id,
                CeleryTaskLogLevel.INFO, f"加载数据集，共 {total_items} 条数据", "dataset_loaded"
            )
            
            if total_items == 0:
                self.update_run_status(run_id, ExperimentStatus.COMPLETED, progress=100)
                self.update_experiment_status(experiment_id, ExperimentStatus.COMPLETED, progress=100)
                return
            
            # Check if experiment was stopped after loading dataset
            experiment = self.get_experiment(experiment_id)
            run = self.get_run(run_id)
            if experiment.status == ExperimentStatus.STOPPED or (run and run.status == ExperimentStatus.STOPPED):
                logger.info(f"[ExecuteExperiment] Experiment {experiment_id} or run {run_id} was stopped after loading dataset, aborting execution")
                self.update_run_status(run_id, ExperimentStatus.STOPPED)
                self.update_experiment_status(experiment_id, ExperimentStatus.STOPPED)
                return
            
            # Log first item content as example
            if items and len(items) > 0:
                first_item = items[0]
                log_celery_task_event(
                    self.celery_log_service, experiment_id, run_id, task_id,
                    CeleryTaskLogLevel.INFO, f"数据项示例 (ID: {first_item.id})", "dataset_item_example",
                    input_data={
                        "item_id": first_item.id,
                        "data_content": first_item.data_content,
                    },
                    output_data={
                        "item_id": first_item.id,
                        "data_content_keys": list(first_item.data_content.keys()) if isinstance(first_item.data_content, dict) else None,
                    }
                )
            
            # Process each item
            for idx, item in enumerate(items):
                # Check if experiment or run was stopped
                experiment = self.get_experiment(experiment_id)
                run = self.get_run(run_id)
                if experiment.status == ExperimentStatus.STOPPED or (run and run.status == ExperimentStatus.STOPPED):
                    logger.info(f"[ExecuteExperiment] Experiment {experiment_id} or run {run_id} was stopped during execution, stopping at item {idx + 1}/{total_items}")
                    self.update_run_status(run_id, ExperimentStatus.STOPPED)
                    self.update_experiment_status(experiment_id, ExperimentStatus.STOPPED)
                    break
                
                # Log processing item
                self.celery_log_service.create_log(
                    experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO,
                    f"处理数据项 {item.id} ({idx + 1}/{total_items})",
                    "process_item"
                )
                
                trace_span = self.tracer.start_span(
                    name=f"experiment_item_{item.id}",
                    parent_span_id=None,  # Explicitly set to None for root span
                    kind="INTERNAL",
                    attributes={
                        "experiment_id": experiment_id,
                        "run_id": run_id,
                        "dataset_item_id": item.id,
                    }
                )
                trace_id = trace_span.get_trace_id()
                root_span_id = trace_span.get_span_id()
                
                try:
                    # Extract turnFields from dataset item (matching coze-loop's logic)
                    # In coze-loop: turnFields = gslice.ToMap(turn.FieldDataList, func(t *entity.FieldData) (string, *entity.Content) {
                    #     return t.Name, t.Content
                    # })
                    logger.info(f"[ExecuteExperiment] Processing item {item.id}, data_content keys: {list(item.data_content.keys()) if isinstance(item.data_content, dict) else 'not a dict'}")
                    
                    try:
                        turn_fields = self._extract_turn_fields_from_data_content(item.data_content)
                    except ValueError as e:
                        error_msg = f"Failed to extract fields from dataset item {item.id}: {str(e)}"
                        logger.error(f"[ExecuteExperiment] {error_msg}")
                        raise ValueError(error_msg)
                    
                    # Validate turn_fields
                    if not turn_fields:
                        logger.warning(f"[ExecuteExperiment] turn_fields is empty for item {item.id}. This may cause evaluation to fail.")
                        self.celery_log_service.create_log(
                            experiment_id, run_id, task_id, CeleryTaskLogLevel.WARNING,
                            f"数据项 {item.id} 字段提取结果为空",
                            "field_extraction_warning"
                        )
                    else:
                        logger.info(f"[ExecuteExperiment] Successfully extracted {len(turn_fields)} fields from item {item.id}: {list(turn_fields.keys())}")
                        
                        # Record field extraction with input/output
                        turn_fields_data = {
                            k: {
                                "text": v.text if hasattr(v, 'text') else str(v),
                                "format": v.format if hasattr(v, 'format') else None,
                                "content_type": v.content_type.value if hasattr(v, 'content_type') and hasattr(v.content_type, 'value') else None,
                            } for k, v in turn_fields.items()
                        }
                        
                        self.celery_log_service.create_log(
                            experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO,
                            f"字段提取完成，提取到 {len(turn_fields)} 个字段: {', '.join(list(turn_fields.keys()))}",
                            "field_extraction_completed",
                            input_data={"dataset_item_id": item.id, "raw_data_content": item.data_content},
                            output_data={"extracted_fields": turn_fields_data, "field_names": list(turn_fields.keys())}
                        )
                    
                    # Strict validation: Ensure turns is NEVER in turn_fields
                    if "turns" in turn_fields:
                        logger.error(f"[ExecuteExperiment] CRITICAL: turns field found in turn_fields for item {item.id}. Fields: {list(turn_fields.keys())}")
                        raise RuntimeError(
                            f"CRITICAL: turns field found in turn_fields for item {item.id}. "
                            f"This indicates a bug in _extract_turn_fields_from_data_content. "
                            f"Fields: {list(turn_fields.keys())}"
                        )
                    
                    # Add more context to root span
                    trace_span.set_input({
                        "experiment_id": experiment_id,
                        "run_id": run_id,
                        "dataset_item_id": item.id,
                        "turn_fields_keys": list(turn_fields.keys()) if turn_fields else [],
                        "data_content_keys": list(item.data_content.keys()) if isinstance(item.data_content, dict) else [],
                    })
                    trace_span.add_event("field_extraction_completed", attributes={
                        "extracted_fields_count": len(turn_fields) if turn_fields else 0,
                        "field_names": list(turn_fields.keys()) if turn_fields else [],
                    })
                    
                    # IMPORTANT: Save root span first to create trace
                    # This ensures trace exists before child spans are saved
                    logger.info(f"[ExecuteExperiment] Saving root span first to create trace {trace_id}")
                    self.tracer.finish_span(trace_span, db=self.db)
                    logger.info(f"[ExecuteExperiment] Root span saved, trace {trace_id} created")
                    
                    # CallTarget: Get target output fields (matching coze-loop's CallTarget)
                    logger.debug(f"[ExecuteExperiment] Calling target for item {item.id}")
                    
                    # Get target type for logging
                    target_config = experiment.evaluation_target_config or {}
                    target_type = target_config.get("type", "none")
                    target_type_display = {
                        "api": "API",
                        "function": "Function",
                        "none": "无（使用数据集输出）"
                    }.get(target_type, target_type.upper())
                    
                    self.celery_log_service.create_log(
                        experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO,
                        f"调用评测对象 ({target_type_display})",
                        "call_target",
                        input_data={
                            "target_type": target_type,
                            "target_config": target_config,
                        }
                    )
                    
                    target_fields, target_span, target_error = await self._call_target(
                        experiment=experiment,
                        item=item,
                        turn_fields=turn_fields,
                        trace_id=trace_id,
                        root_span_id=root_span_id,
                    )
                    logger.info(f"[ExecuteExperiment] Target fields for item {item.id}: {list(target_fields.keys())}")
                    
                    # Log target error if any
                    if target_error:
                        logger.error(f"[ExecuteExperiment] Evaluation target call failed for item {item.id}: {target_error}")
                        self.celery_log_service.create_log(
                            experiment_id, run_id, task_id, CeleryTaskLogLevel.ERROR,
                            f"评测对象调用失败: {target_error}",
                            "target_error",
                            input_data={
                                "dataset_item_id": item.id,
                                "target_type": target_type,
                                "target_config": target_config,
                                "turn_fields": {k: {"text": v.text if hasattr(v, 'text') else str(v)} for k, v in turn_fields.items()} if turn_fields else {},
                            },
                            output_data={"error": target_error}
                        )
                    
                    # Record target call with input/output
                    target_fields_data = {
                        k: {
                            "text": v.text if hasattr(v, 'text') else str(v),
                            "format": v.format if hasattr(v, 'format') else None,
                            "content_type": v.content_type.value if hasattr(v, 'content_type') and hasattr(v.content_type, 'value') else None,
                        } for k, v in target_fields.items()
                    }
                    
                    # Prepare turn_fields data for logging
                    turn_fields_for_log = {
                        k: {
                            "text": v.text if hasattr(v, 'text') else str(v),
                            "format": v.format if hasattr(v, 'format') else None,
                            "content_type": v.content_type.value if hasattr(v, 'content_type') and hasattr(v.content_type, 'value') else None,
                        } for k, v in turn_fields.items()
                    }
                    
                    log_level = CeleryTaskLogLevel.ERROR if target_error else CeleryTaskLogLevel.INFO
                    if target_error:
                        log_message = f"评测对象调用失败: {target_error}"
                    else:
                        log_message = f"评测对象调用完成 ({target_type_display})，获取到 {len(target_fields)} 个字段: {', '.join(list(target_fields.keys()))}"
                    
                    self.celery_log_service.create_log(
                        experiment_id, run_id, task_id, log_level,
                        log_message,
                        "target_completed",
                        input_data={
                            "dataset_item_id": item.id,
                            "target_type": target_type,
                            "target_config": target_config,
                            "turn_fields": turn_fields_for_log,
                        },
                        output_data={"target_fields": target_fields_data, "error": target_error} if target_error else {"target_fields": target_fields_data}
                    )
                    
                    # Finish target span immediately (auto-saved by DatabaseTracer)
                    if target_span:
                        logger.info(f"[ExecuteExperiment] 🔄 About to finish target span: span_id={target_span.span_id}, trace_id={trace_id}, parent_span_id={root_span_id}, has_db={self.db is not None}")
                        self.tracer.finish_span(target_span, db=self.db)
                        logger.info(f"[ExecuteExperiment] ✅ Target span finish_span() called: span_id={target_span.span_id}")
                        
                        # Verify target span was saved
                        from app.services.observability_service import ObservabilityService
                        obs_service = ObservabilityService(self.db)
                        saved_target_span = obs_service.get_span(target_span.span_id)
                        if saved_target_span:
                            logger.info(f"[ExecuteExperiment] ✅ VERIFIED: Target span {target_span.span_id} found in database")
                        else:
                            logger.error(f"[ExecuteExperiment] ❌ CRITICAL: Target span {target_span.span_id} NOT found in database after save!")
                    else:
                        logger.warning(f"[ExecuteExperiment] ⚠️ target_span is None! Cannot finish target span.")
                    
                    # Validate target_fields
                    if not target_fields:
                        logger.warning(f"[ExecuteExperiment] target_fields is empty for item {item.id}. This may cause evaluation to fail.")
                    
                    # Note: trace_span was already finished at line 991, so we can't add events to it
                    # This is OK - events were already added before finishing
                    
                    # CallEvaluators: Call all evaluators (matching coze-loop's CallEvaluators)
                    logger.debug(f"[ExecuteExperiment] Calling evaluators for item {item.id}")
                    self.celery_log_service.create_log(
                        experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO,
                        f"调用评估器",
                        "call_evaluator"
                    )
                    
                    evaluator_results = await self._call_evaluators(
                        experiment=experiment,
                        item=item,
                        turn_fields=turn_fields,
                        target_fields=target_fields,
                        target_error=target_error,
                        trace_id=trace_id,
                        root_span_id=root_span_id,
                        run_id=run_id,
                        experiment_id=experiment_id,
                    )
                    logger.info(f"[ExecuteExperiment] Completed evaluation for item {item.id}, results: {list(evaluator_results.keys())}")
                    
                    self.celery_log_service.create_log(
                        experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO,
                        f"评估完成，共 {len(evaluator_results)} 个结果",
                        "evaluator_completed"
                    )
                    
                    # Verify all spans were saved to database
                    from app.services.observability_service import ObservabilityService
                    obs_service = ObservabilityService(self.db)
                    all_spans = obs_service.list_spans(trace_id)
                    logger.info(f"[ExecuteExperiment] 🔍 VERIFICATION: Found {len(all_spans)} spans in database for trace {trace_id}")
                    for span in all_spans:
                        logger.info(f"[ExecuteExperiment]   - Span: span_id={span.span_id}, name={span.name}, parent_span_id={span.parent_span_id}")
                    
                    # Verify we have all expected spans
                    expected_span_count = 1 + 1 + len(experiment.evaluator_version_ids)  # root + target + evaluators
                    if len(all_spans) < expected_span_count:
                        logger.error(f"[ExecuteExperiment] ❌ CRITICAL: Expected {expected_span_count} spans but found {len(all_spans)}! Missing spans!")
                    else:
                        logger.info(f"[ExecuteExperiment] ✅ All {expected_span_count} expected spans found in database")
                    
                    # Set root span output
                    trace_span.set_output({
                        "evaluator_results": {
                            str(k): {
                                "score": v.get("score"),
                                "has_error": v.get("error_message") is not None,
                            } for k, v in evaluator_results.items()
                        },
                        "total_evaluators": len(evaluator_results),
                    })
                            
                except Exception as e:
                    # Set root span error
                    trace_span.set_error(e)
                    # If root span hasn't been saved yet, save it now
                    if not trace_span._is_finished:
                        logger.info(f"[ExecuteExperiment] Saving root span after error for trace {trace_id}")
                        self.tracer.finish_span(trace_span, db=self.db)
                finally:
                    # Root span should already be saved, but ensure it's finished
                    if not trace_span._is_finished:
                        logger.warning(f"[ExecuteExperiment] Root span not finished, finishing now for trace {trace_id}")
                        self.tracer.finish_span(trace_span, db=self.db)
                    
                    self.db.commit()
                    
                    # Update progress
                    progress = int((idx + 1) * 100 / total_items)
                    self.update_run_status(run_id, ExperimentStatus.RUNNING, progress=progress)
                    self.update_experiment_status(experiment_id, ExperimentStatus.RUNNING, progress=progress)
            
            # Mark as completed
            self.celery_log_service.create_log(
                experiment_id, run_id, task_id, CeleryTaskLogLevel.INFO,
                f"所有 {total_items} 条数据项处理完成",
                "all_items_completed"
            )
            
            self.update_run_status(run_id, ExperimentStatus.COMPLETED, progress=100)
            self.update_experiment_status(experiment_id, ExperimentStatus.COMPLETED, progress=100)
            
        except Exception as e:
            error_msg = f"实验执行失败: {str(e)}"
            self.celery_log_service.create_log(
                experiment_id, run_id, task_id, CeleryTaskLogLevel.ERROR,
                error_msg,
                "execution_failed"
            )
            self.update_run_status(run_id, ExperimentStatus.FAILED, error_message=str(e))
            self.update_experiment_status(experiment_id, ExperimentStatus.FAILED)
            raise

    async def _invoke_evaluation_target(self, config: Dict[str, Any], input_data: Dict[str, Any]) -> str:
        """Invoke evaluation target using AutoGen framework for unified handling"""
        logger.info(f"[InvokeTarget] ========== Invoking evaluation target ==========")
        logger.info(f"[InvokeTarget] Target type: {config.get('type')}")
        logger.info(f"[InvokeTarget] Input data keys: {list(input_data.keys()) if isinstance(input_data, dict) else 'not a dict'}")
        logger.debug(f"[InvokeTarget] Input data content (first 500 chars): {json.dumps(input_data, ensure_ascii=False, default=str)[:500]}")
        
        try:
            # Use AutoGenTargetInvoker for unified target invocation
            from app.utils.autogen_helper import AutoGenTargetInvoker
            
            invoker = AutoGenTargetInvoker(config, db=self.db)
            output = await invoker.invoke(input_data)
            
            if not output or (isinstance(output, str) and not output.strip()):
                logger.warning(f"[InvokeTarget] Target returned empty output! This may indicate a problem.")
            else:
                logger.info(f"[InvokeTarget] Target returned output (first 200 chars): {output[:200]}...")
            
            logger.info(f"[InvokeTarget] ========== Target invocation completed successfully ==========")
            return output
            
        except Exception as e:
            error_msg = f"Failed to invoke evaluation target: {str(e)}"
            logger.error(f"[InvokeTarget] {error_msg}", exc_info=True)
            raise ValueError(error_msg)

    # Results
    def get_results(self, experiment_id: int, run_id: Optional[int] = None) -> List[ExperimentResult]:
        """Get experiment results"""
        return self.result_service.get_results(experiment_id, run_id)
    
    # Extended methods
    def check_experiment_name(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """Check if experiment name is available"""
        query = self.db.query(Experiment).filter(Experiment.name == name)
        if exclude_id:
            query = query.filter(Experiment.id != exclude_id)
        existing = query.first()
        return existing is None
    
    def clone_experiment(self, experiment_id: int, new_name: Optional[str] = None) -> Experiment:
        """Clone an experiment"""
        original = self.get_experiment(experiment_id)
        if not original:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Generate new name if not provided
        if not new_name:
            base_name = original.name
            counter = 1
            new_name = f"{base_name}_copy_{counter}"
            while not self.check_experiment_name(new_name):
                counter += 1
                new_name = f"{base_name}_copy_{counter}"
        
        # Create new experiment
        new_experiment = Experiment(
            name=new_name,
            description=original.description,
            dataset_version_id=original.dataset_version_id,
            evaluation_target_config=copy.deepcopy(original.evaluation_target_config),
            evaluator_version_ids=copy.deepcopy(original.evaluator_version_ids),
            item_concur_num=original.item_concur_num,
            expt_type=original.expt_type,
            max_alive_time=original.max_alive_time,
            created_by=original.created_by,
        )
        self.db.add(new_experiment)
        self.db.commit()
        self.db.refresh(new_experiment)
        return new_experiment
    
    def retry_experiment(
        self,
        experiment_id: int,
        retry_mode: RetryMode = RetryMode.RETRY_ALL,
        item_ids: Optional[List[int]] = None
    ) -> ExperimentRun:
        """Retry an experiment with specified mode"""
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Create a new run
        run = self.create_run(experiment_id)
        
        # If retry mode is RETRY_FAILURE, we need to identify failed items
        # For now, we'll just create a new run and let it execute all items
        # In a more sophisticated implementation, we could filter items based on retry_mode
        
        return run
    
    def batch_delete_experiments(self, experiment_ids: List[int]) -> int:
        """Batch delete experiments"""
        deleted_count = 0
        for experiment_id in experiment_ids:
            if self.delete_experiment(experiment_id):
                deleted_count += 1
        return deleted_count
    
    def calculate_aggregate_results(
        self,
        experiment_id: int,
        run_id: Optional[int] = None,
        save: bool = True
    ) -> List[Dict[str, Any]]:
        """Calculate and optionally save aggregate results"""
        return self.result_service.calculate_aggregate_results(experiment_id, run_id, save)
    
    def get_experiment_statistics(
        self,
        experiment_id: int,
        run_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get experiment statistics"""
        return self.result_service.get_experiment_statistics(experiment_id, run_id)
        
        # Calculate statistics
        total_count = len(results)
        success_count = len([r for r in results if r.score is not None and r.error_message is None])
        
        # Failure count: explicitly has error message OR score is None (invalid result)
        failure_count = len([r for r in results if r.error_message is not None or (r.score is None and r.error_message is None)])
        
        # Pending count: total - success - failure
        # This ensures pending is 0 if all items are accounted for (either success or failure)
        pending_count = max(0, total_count - success_count - failure_count)
        
        # If experiment is completed, pending should be 0
        if experiment.status in [ExperimentStatus.COMPLETED, ExperimentStatus.FAILED, ExperimentStatus.STOPPED]:
            pending_count = 0
        
        # Get aggregate results
        aggregate_results = self.calculate_aggregate_results(experiment_id, run_id, save=False)
        
        # Calculate token usage from evaluator_records
        evaluator_records_query = self.db.query(EvaluatorRecord).filter(
            EvaluatorRecord.experiment_id == experiment_id
        )
        if run_id:
            evaluator_records_query = evaluator_records_query.filter(
                EvaluatorRecord.experiment_run_id == run_id
            )
        evaluator_records = evaluator_records_query.all()
        
        logger.info(f"[GetStatistics] Found {len(evaluator_records)} evaluator records for experiment {experiment_id}, run_id={run_id}")
        
        total_input_tokens = 0
        total_output_tokens = 0
        
        for record in evaluator_records:
            output_data = record.output_data or {}
            logger.debug(f"[GetStatistics] Record {record.id}: output_data keys={list(output_data.keys()) if isinstance(output_data, dict) else 'not a dict'}")
            
            evaluator_usage = output_data.get("evaluator_usage", {})
            logger.debug(f"[GetStatistics] Record {record.id}: evaluator_usage type={type(evaluator_usage)}, value={evaluator_usage}")
            
            if isinstance(evaluator_usage, dict):
                input_tokens = evaluator_usage.get("input_tokens", 0)
                output_tokens = evaluator_usage.get("output_tokens", 0)
                logger.info(f"[GetStatistics] Record {record.id}: input_tokens={input_tokens} (type={type(input_tokens)}), output_tokens={output_tokens} (type={type(output_tokens)})")
                
                if isinstance(input_tokens, (int, float)) and input_tokens:
                    total_input_tokens += int(input_tokens)
                if isinstance(output_tokens, (int, float)) and output_tokens:
                    total_output_tokens += int(output_tokens)
            else:
                logger.warning(f"[GetStatistics] Record {record.id}: evaluator_usage is not a dict, type={type(evaluator_usage)}, value={evaluator_usage}")
                logger.warning(f"[GetStatistics] Record {record.id}: Full output_data={json.dumps(output_data, default=str, ensure_ascii=False)[:500]}")
        
        logger.info(f"[GetStatistics] Total tokens: input={total_input_tokens}, output={total_output_tokens}")
        
        token_usage = {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens
        }
        
        return {
            "experiment_id": experiment_id,
            "total_count": total_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "pending_count": pending_count,
            "evaluator_aggregate_results": aggregate_results,
            "token_usage": token_usage
        }

