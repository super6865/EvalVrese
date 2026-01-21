"""
Python runtime implementation
"""
import json
import time
import logging
from typing import Dict, Any, Optional
from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safe_builtins
from app.infra.runtime.runtime import Runtime, ExecutionResult
from app.utils.code_validator import CodeValidator
from app.domain.entity.evaluator_types import LanguageType

logger = logging.getLogger(__name__)


class EvalOutput:
    """评估结果输出类，用于在 RestrictedPython 环境中返回评估结果"""
    def __init__(self, score, reason):
        self.score = score
        self.reason = reason


class PythonRuntime(Runtime):
    """Python 运行时实现"""
    
    def __init__(self):
        import dataclasses
        self.allowed_builtins = {
            **safe_builtins,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'min': min,
            'max': max,
            'sum': sum,
            'abs': abs,
            'round': round,
            'sorted': sorted,
            'enumerate': enumerate,
            'zip': zip,
            'range': range,
            'json': json,
        }
    
    @staticmethod
    def _safe_getitem(obj, key):
        """Safe _getitem_ function to allow dictionary and list access"""
        return obj[key]
    
    async def run_code(
        self,
        code: str,
        language: str,
        timeout_ms: int = 5000,
        ext: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """执行 Python 代码"""
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr
        
        start_time = time.time()
        timeout_seconds = timeout_ms / 1000.0
        
        try:
            # Compile code
            byte_code = compile_restricted(code, '<evaluator>', 'exec')
            
            # Prepare execution environment
            # Inject json and dataclasses modules directly into globals to avoid __import__ restriction
            # Add _getitem_ guard to allow dictionary and list access
            # Inject EvalOutput class to avoid RestrictedPython class definition issues
            import dataclasses
            restricted_globals = {
                '__builtins__': self.allowed_builtins,
                'json': json,  # Inject json module directly
                'dataclasses': dataclasses,  # Inject dataclasses module directly
                'dataclass': dataclasses.dataclass,  # Also provide dataclass decorator directly
                '_getitem_': self._safe_getitem,  # Allow dictionary and list access
                'EvalOutput': EvalOutput,  # Inject EvalOutput class to avoid RestrictedPython class definition issues
            }
            restricted_locals = {}
            
            # Capture stdout and stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            # Execute code
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(byte_code, restricted_globals, restricted_locals)
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                return ExecutionResult(
                    stdout=stdout_capture.getvalue(),
                    stderr=stderr_capture.getvalue(),
                    success=False,
                    error=f"Execution timeout after {timeout_ms}ms",
                )
            
            # Extract result
            ret_val = ""
            if 'evaluation_result' in restricted_locals:
                result = restricted_locals['evaluation_result']
                if isinstance(result, dict):
                    # Validate that the dict can be serialized to JSON
                    try:
                        ret_val = json.dumps(result, ensure_ascii=False)
                        # Verify the serialized JSON can be parsed back
                        json.loads(ret_val)
                    except (TypeError, ValueError, json.JSONDecodeError) as e:
                        logger.warning(
                            f"Failed to serialize evaluation_result dict to JSON: {e}. "
                            f"Result type: {type(result)}, keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}"
                        )
                        # Fallback: try to create a valid dict with string values
                        try:
                            safe_result = {
                                "score": result.get("score") if isinstance(result, dict) else None,
                                "reason": str(result.get("reason", "")) if isinstance(result, dict) else str(result)
                            }
                            ret_val = json.dumps(safe_result, ensure_ascii=False)
                        except Exception:
                            ret_val = json.dumps({"score": None, "reason": str(result)}, ensure_ascii=False)
                elif isinstance(result, str):
                    # If result is already a string, check if it's valid JSON
                    try:
                        json.loads(result)
                        ret_val = result
                    except json.JSONDecodeError:
                        # Not valid JSON, wrap it in a dict
                        ret_val = json.dumps({"score": None, "reason": result}, ensure_ascii=False)
                else:
                    ret_val = str(result)
                    logger.debug(f"evaluation_result is not dict or str, converting to string: {type(result)}")
            elif 'evaluation_result' in restricted_globals:
                result = restricted_globals['evaluation_result']
                if isinstance(result, dict):
                    # Validate that the dict can be serialized to JSON
                    try:
                        ret_val = json.dumps(result, ensure_ascii=False)
                        # Verify the serialized JSON can be parsed back
                        json.loads(ret_val)
                    except (TypeError, ValueError, json.JSONDecodeError) as e:
                        logger.warning(
                            f"Failed to serialize evaluation_result dict to JSON: {e}. "
                            f"Result type: {type(result)}, keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}"
                        )
                        # Fallback: try to create a valid dict with string values
                        try:
                            safe_result = {
                                "score": result.get("score") if isinstance(result, dict) else None,
                                "reason": str(result.get("reason", "")) if isinstance(result, dict) else str(result)
                            }
                            ret_val = json.dumps(safe_result, ensure_ascii=False)
                        except Exception:
                            ret_val = json.dumps({"score": None, "reason": str(result)}, ensure_ascii=False)
                elif isinstance(result, str):
                    # If result is already a string, check if it's valid JSON
                    try:
                        json.loads(result)
                        ret_val = result
                    except json.JSONDecodeError:
                        # Not valid JSON, wrap it in a dict
                        ret_val = json.dumps({"score": None, "reason": result}, ensure_ascii=False)
                else:
                    ret_val = str(result)
                    logger.debug(f"evaluation_result is not dict or str, converting to string: {type(result)}")
            
            # Log ret_val for debugging (truncated to avoid log spam)
            if ret_val:
                preview = ret_val[:200] + ("..." if len(ret_val) > 200 else "")
                logger.debug(f"Python runtime returning ret_val (preview): {preview}")
            
            return ExecutionResult(
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                ret_val=ret_val,
                success=True,
            )
            
        except SyntaxError as e:
            return ExecutionResult(
                stderr=str(e),
                success=False,
                error=f"Syntax error: {str(e)}",
            )
        except Exception as e:
            return ExecutionResult(
                stderr=str(e),
                success=False,
                error=f"Execution error: {str(e)}",
            )
    
    def validate_code(
        self,
        code: str,
        language: str,
    ) -> bool:
        """验证 Python 代码"""
        is_valid, _ = CodeValidator.validate(code, LanguageType.PYTHON)
        return is_valid

