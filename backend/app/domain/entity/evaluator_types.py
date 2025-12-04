"""
Evaluator type definitions
"""
from enum import Enum
from typing import Literal


class EvaluatorType(str, Enum):
    """评估器类型"""
    PROMPT = "prompt"  # Prompt 评估器
    CODE = "code"  # Code 评估器


class EvaluatorBoxType(str, Enum):
    """评估器黑白盒类型"""
    WHITE = "white"  # 白盒
    BLACK = "black"  # 黑盒


class ContentType(str, Enum):
    """内容类型"""
    TEXT = "Text"
    IMAGE = "Image"
    AUDIO = "Audio"
    MULTIPART = "MultiPart"
    MULTIPART_VARIABLE = "multi_part_variable"


class EvaluatorRunStatus(str, Enum):
    """评估器运行状态"""
    UNKNOWN = "unknown"
    SUCCESS = "success"
    FAIL = "fail"


class ParseType(str, Enum):
    """解析类型（用于 Prompt 评估器）"""
    JSON = "json"
    TEXT = "text"


class LanguageType(str, Enum):
    """编程语言类型"""
    PYTHON = "Python"
    JS = "JS"


class Role(str, Enum):
    """消息角色"""
    UNDEFINED = "undefined"
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# Type aliases for convenience
EvaluatorTypeLiteral = Literal["prompt", "code"]
ContentTypeLiteral = Literal["Text", "Image", "Audio", "MultiPart", "multi_part_variable"]
LanguageTypeLiteral = Literal["Python", "JS"]

