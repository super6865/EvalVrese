"""
JavaScript runtime implementation
"""
import json
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional
from app.infra.runtime.runtime import Runtime, ExecutionResult
from app.utils.code_validator import CodeValidator
from app.domain.entity.evaluator_types import LanguageType


class JSRuntime(Runtime):
    """JavaScript 运行时实现（使用 Node.js）"""
    
    def __init__(self, node_path: str = "node"):
        """
        初始化 JavaScript 运行时
        
        Args:
            node_path: Node.js 可执行文件路径
        """
        self.node_path = node_path
    
    async def run_code(
        self,
        code: str,
        language: str,
        timeout_ms: int = 5000,
        ext: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """执行 JavaScript 代码"""
        # Wrap code to capture result
        wrapped_code = f"""
{code}

// Capture result
if (typeof evaluation_result !== 'undefined') {{
    if (typeof evaluation_result === 'object') {{
        console.log(JSON.stringify(evaluation_result));
    }} else {{
        console.log(String(evaluation_result));
    }}
}} else {{
    console.error("evaluation_result is not defined");
    process.exit(1);
}}
"""
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(wrapped_code)
            temp_file = f.name
        
        try:
            # Execute with Node.js
            timeout_seconds = timeout_ms / 1000.0
            process = subprocess.run(
                [self.node_path, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            
            stdout = process.stdout
            stderr = process.stderr
            ret_val = stdout.strip() if stdout else ""
            
            # Try to parse JSON result
            if ret_val:
                try:
                    json.loads(ret_val)
                except json.JSONDecodeError:
                    pass  # Not JSON, keep as string
            
            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                ret_val=ret_val,
                success=process.returncode == 0,
                error=stderr if process.returncode != 0 else None,
            )
            
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error=f"Execution timeout after {timeout_ms}ms",
            )
        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                error="Node.js is not installed or not in PATH",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}",
            )
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def validate_code(
        self,
        code: str,
        language: str,
    ) -> bool:
        """验证 JavaScript 代码"""
        is_valid, _ = CodeValidator.validate(code, LanguageType.JS)
        return is_valid

