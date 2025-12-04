"""
Code validator for code evaluators
"""
import ast
import re
from typing import Tuple, Optional
from RestrictedPython import compile_restricted
from app.domain.entity.evaluator_types import LanguageType


class CodeValidationError(Exception):
    """Code validation error"""
    pass


class CodeValidator:
    """Code validator for evaluators"""
    
    DANGEROUS_PATTERNS = [
        (r'import\s+os', 'os module'),
        (r'import\s+sys', 'sys module'),
        (r'import\s+subprocess', 'subprocess module'),
        (r'import\s+shutil', 'shutil module'),
        (r'__import__', '__import__ function'),
        (r'eval\s*\(', 'eval function'),
        (r'exec\s*\(', 'exec function'),
        (r'compile\s*\(', 'compile function'),
        (r'open\s*\(', 'open function'),
        (r'file\s*\(', 'file function'),
        (r'input\s*\(', 'input function'),
        (r'raw_input\s*\(', 'raw_input function'),
    ]
    
    @staticmethod
    def validate(
        code: str,
        language_type: LanguageType,
    ) -> Tuple[bool, Optional[str]]:
        has_function, func_error = CodeValidator._check_exec_evaluation_function(code, language_type)
        if not has_function:
            return False, func_error
        
        is_safe, security_error = CodeValidator._check_security(code)
        if not is_safe:
            return False, security_error
        
        is_valid, syntax_error = CodeValidator._check_syntax(code, language_type)
        if not is_valid:
            return False, syntax_error
        
        return True, None
    
    @staticmethod
    def _check_exec_evaluation_function(
        code: str,
        language_type: LanguageType,
    ) -> Tuple[bool, Optional[str]]:
        if language_type == LanguageType.PYTHON:
            if 'def exec_evaluation' not in code and 'exec_evaluation' not in code:
                return False, "exec_evaluation function is not defined"
            
            try:
                tree = ast.parse(code)
                has_function = any(
                    isinstance(node, ast.FunctionDef) and node.name == 'exec_evaluation'
                    for node in ast.walk(tree)
                )
                if not has_function:
                    return False, "exec_evaluation function is not defined"
            except SyntaxError:
                pass
        elif language_type == LanguageType.JS:
            patterns = [
                r'function\s+exec_evaluation',
                r'const\s+exec_evaluation\s*=',
                r'let\s+exec_evaluation\s*=',
                r'var\s+exec_evaluation\s*=',
                r'exec_evaluation\s*=\s*function',
                r'exec_evaluation\s*=\s*\([^)]*\)\s*=>',
            ]
            has_function = any(re.search(pattern, code) for pattern in patterns)
            if not has_function:
                return False, "exec_evaluation function is not defined"
        
        return True, None
    
    @staticmethod
    def _check_security(code: str) -> Tuple[bool, Optional[str]]:
        for pattern, description in CodeValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Dangerous operation detected: {description}"
        return True, None
    
    @staticmethod
    def _check_syntax(
        code: str,
        language_type: LanguageType,
    ) -> Tuple[bool, Optional[str]]:
        if language_type == LanguageType.PYTHON:
            try:
                compile_restricted(code, '<evaluator>', 'exec')
                return True, None
            except SyntaxError as e:
                return False, f"Syntax error: {str(e)}"
            except Exception as e:
                return False, f"Code validation error: {str(e)}"
        elif language_type == LanguageType.JS:
            try:
                if code.count('(') != code.count(')'):
                    return False, "Unmatched parentheses"
                if code.count('[') != code.count(']'):
                    return False, "Unmatched square brackets"
                if code.count('{') != code.count('}'):
                    return False, "Unmatched curly braces"
                return True, None
            except Exception as e:
                return False, f"Code validation error: {str(e)}"
        else:
            return False, f"Unsupported language type: {language_type}"

