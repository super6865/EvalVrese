"""
Code builder for code evaluators
"""
from typing import Dict, Any, Optional
import logging
from app.domain.entity.evaluator_entity import EvaluatorInputData
from app.domain.entity.evaluator_types import LanguageType

logger = logging.getLogger(__name__)


class CodeBuilder:
    """代码构建器"""
    
    @staticmethod
    def build_code(
        input_data: EvaluatorInputData,
        code_content: str,
        language_type: LanguageType,
    ) -> str:
        """
        构建可执行代码
        
        Args:
            input_data: 输入数据
            code_content: 代码内容
            language_type: 语言类型
            
        Returns:
            构建后的代码
        """
        # Build turn data structure (similar to coze-loop)
        # Code evaluators expect a 'turn' object with evaluate_dataset_fields and evaluate_target_output_fields
        turn_dict = {}
        
        # Extract evaluate_dataset_fields
        # IMPORTANT: Include all fields even if content is None or text is None
        # This ensures that expected fields exist in turn_dict, preventing KeyError
        if input_data.evaluate_dataset_fields:
            evaluate_dataset_fields = {}
            for key, content in input_data.evaluate_dataset_fields.items():
                # Always include the field, even if content is None
                if content:
                    # Extract text, use empty string if None to avoid issues
                    text_value = content.text if (hasattr(content, 'text') and content.text is not None) else ""
                    # Extract content_type, handle both enum and string types
                    if hasattr(content, 'content_type') and content.content_type:
                        # ContentType is a str enum, so we can use str() or .value
                        content_type_value = content.content_type.value if hasattr(content.content_type, 'value') else str(content.content_type)
                    else:
                        content_type_value = 'Text'
                    evaluate_dataset_fields[key] = {
                        'content_type': content_type_value,
                        'text': text_value
                    }
                    logger.debug(f"[CodeBuilder] Added evaluate_dataset_fields['{key}']: content_type={content_type_value}, text_length={len(text_value)}")
                else:
                    # Content is None, but still include the field with default values
                    evaluate_dataset_fields[key] = {
                        'content_type': 'Text',
                        'text': ""
                    }
                    logger.warning(f"[CodeBuilder] Content is None for evaluate_dataset_fields['{key}'], using default values")
            if evaluate_dataset_fields:
                turn_dict['evaluate_dataset_fields'] = evaluate_dataset_fields
                logger.debug(f"[CodeBuilder] Built evaluate_dataset_fields with {len(evaluate_dataset_fields)} fields: {list(evaluate_dataset_fields.keys())}")
        
        # Extract evaluate_target_output_fields
        # IMPORTANT: Include all fields even if content is None or text is None
        # This ensures that expected fields exist in turn_dict, preventing KeyError
        if input_data.evaluate_target_output_fields:
            evaluate_target_output_fields = {}
            for key, content in input_data.evaluate_target_output_fields.items():
                # Always include the field, even if content is None
                if content:
                    # Extract text, use empty string if None to avoid issues
                    text_value = content.text if (hasattr(content, 'text') and content.text is not None) else ""
                    # Extract content_type, handle both enum and string types
                    if hasattr(content, 'content_type') and content.content_type:
                        # ContentType is a str enum, so we can use str() or .value
                        content_type_value = content.content_type.value if hasattr(content.content_type, 'value') else str(content.content_type)
                    else:
                        content_type_value = 'Text'
                    evaluate_target_output_fields[key] = {
                        'content_type': content_type_value,
                        'text': text_value
                    }
                    logger.debug(f"[CodeBuilder] Added evaluate_target_output_fields['{key}']: content_type={content_type_value}, text_length={len(text_value)}")
                else:
                    # Content is None, but still include the field with default values
                    evaluate_target_output_fields[key] = {
                        'content_type': 'Text',
                        'text': ""
                    }
                    logger.warning(f"[CodeBuilder] Content is None for evaluate_target_output_fields['{key}'], using default values")
            if evaluate_target_output_fields:
                turn_dict['evaluate_target_output_fields'] = evaluate_target_output_fields
                logger.debug(f"[CodeBuilder] Built evaluate_target_output_fields with {len(evaluate_target_output_fields)} fields: {list(evaluate_target_output_fields.keys())}")
        
        # Extract ext
        if input_data.ext:
            turn_dict['ext'] = input_data.ext
        
        # Build wrapper code based on language
        if language_type == LanguageType.PYTHON:
            return CodeBuilder._build_python_code(code_content, turn_dict)
        elif language_type == LanguageType.JS:
            return CodeBuilder._build_js_code(code_content, turn_dict)
        else:
            raise ValueError(f"Unsupported language type: {language_type}")
    
    @staticmethod
    def _build_python_code(code_content: str, turn_dict: Dict[str, Any]) -> str:
        """构建 Python 代码"""
        # Serialize turn data as JSON string
        import json
        turn_json = json.dumps(turn_dict, ensure_ascii=False)
        
        # Use repr() to escape the JSON string, then remove the outer quotes
        # This ensures all control characters (like \n, \t, etc.) are properly escaped
        # repr() returns a string with quotes, so we remove them with [1:-1]
        escaped_json = repr(turn_json)[1:-1]
        
        # Build wrapper (json module is available in the execution environment)
        # Note: We don't use globals() or locals() as they are restricted in RestrictedPython
        # The runtime will check for evaluation_result in restricted_locals and restricted_globals
        # Note: EvalOutput class is pre-defined in the runtime environment to avoid RestrictedPython
        # class definition issues (__metaclass__ errors)
        wrapper = f"""
# Turn data (json module is available in the execution environment)
# EvalOutput class is pre-defined in the runtime environment
turn = json.loads('''{escaped_json}''')

# User code
{code_content}

# Execute evaluation function
# Directly call exec_evaluation(turn) - if it doesn't exist, NameError will be raised
result = exec_evaluation(turn)

# Convert EvalOutput to dict if needed
# Check if result is an EvalOutput instance using isinstance (RestrictedPython compatible)
try:
    if isinstance(result, EvalOutput):
        # It's an EvalOutput object, convert to dict
        evaluation_result = {{"score": result.score, "reason": result.reason}}
    elif isinstance(result, dict):
        # It's already a dict
        evaluation_result = result
    else:
        # Fallback: try to access score and reason attributes
        try:
            evaluation_result = {{"score": result.score, "reason": result.reason}}
        except AttributeError:
            # If attributes don't exist, use default values
            evaluation_result = {{"score": 0.0, "reason": str(result)}}
except Exception:
    # If anything goes wrong, try to convert to dict directly
    if isinstance(result, dict):
        evaluation_result = result
    else:
        evaluation_result = {{"score": 0.0, "reason": str(result)}}
"""
        return wrapper
    
    @staticmethod
    def _build_js_code(code_content: str, turn_dict: Dict[str, Any]) -> str:
        """构建 JavaScript 代码"""
        import json
        turn_json = json.dumps(turn_dict, ensure_ascii=False)
        
        # Build wrapper
        wrapper = f"""
// Turn data
const turn = {turn_json};

// User code
{code_content}

// Execute evaluation function
if (typeof exec_evaluation === 'function') {{
    const evaluation_result = exec_evaluation(turn);
    if (typeof evaluation_result === 'undefined') {{
        throw new Error("evaluation_result is not set");
    }}
}} else {{
    throw new Error("exec_evaluation function is not defined");
}}
"""
        return wrapper

