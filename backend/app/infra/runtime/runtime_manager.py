"""
Runtime manager
"""
from typing import Dict, Optional
from app.infra.runtime.runtime import Runtime
from app.infra.runtime.python_runtime import PythonRuntime
from app.infra.runtime.js_runtime import JSRuntime
from app.domain.entity.evaluator_types import LanguageType


class RuntimeManager:
    """运行时管理器"""
    
    def __init__(self):
        self._runtimes: Dict[str, Runtime] = {}
        self._initialize_runtimes()
    
    def _initialize_runtimes(self):
        """初始化运行时"""
        self._runtimes[LanguageType.PYTHON] = PythonRuntime()
        self._runtimes[LanguageType.JS] = JSRuntime()
    
    def get_runtime(self, language_type: LanguageType) -> Runtime:
        """
        获取运行时
        
        Args:
            language_type: 语言类型
            
        Returns:
            运行时实例
            
        Raises:
            ValueError: 如果语言类型不支持
        """
        if language_type not in self._runtimes:
            raise ValueError(f"Unsupported language type: {language_type}")
        return self._runtimes[language_type]
    
    def register_runtime(self, language_type: LanguageType, runtime: Runtime):
        """
        注册运行时
        
        Args:
            language_type: 语言类型
            runtime: 运行时实例
        """
        self._runtimes[language_type] = runtime

