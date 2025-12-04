"""
Runtime abstract interface
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel


class ExecutionResult(BaseModel):
    """执行结果"""
    stdout: str = ""
    stderr: str = ""
    ret_val: str = ""
    success: bool = True
    error: Optional[str] = None


class Runtime(ABC):
    """运行时抽象接口"""
    
    @abstractmethod
    async def run_code(
        self,
        code: str,
        language: str,
        timeout_ms: int = 5000,
        ext: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        执行代码
        
        Args:
            code: 代码内容
            language: 语言类型
            timeout_ms: 超时时间（毫秒）
            ext: 扩展参数
            
        Returns:
            执行结果
        """
        pass
    
    @abstractmethod
    def validate_code(
        self,
        code: str,
        language: str,
    ) -> bool:
        """
        验证代码
        
        Args:
            code: 代码内容
            language: 语言类型
            
        Returns:
            是否有效
        """
        pass

