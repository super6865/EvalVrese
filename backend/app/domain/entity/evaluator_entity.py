"""
Evaluator entity definitions
"""
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from app.domain.entity.evaluator_types import (
    ContentType,
    Role,
    EvaluatorRunStatus,
)


class Image(BaseModel):
    """图片信息"""
    name: Optional[str] = None
    url: Optional[str] = None
    uri: Optional[str] = None
    thumb_url: Optional[str] = None
    storage_provider: Optional[str] = None


class Audio(BaseModel):
    """音频信息"""
    format: Optional[str] = None
    url: Optional[str] = None
    base64: Optional[str] = None
    duration: Optional[float] = None


class Content(BaseModel):
    """内容结构"""
    content_type: Optional[ContentType] = None
    format: Optional[str] = None  # FieldDisplayFormat
    text: Optional[str] = None
    image: Optional[Image] = None
    audio: Optional[Audio] = None
    multi_part: Optional[List["Content"]] = None

    def get_text(self) -> str:
        """获取文本内容"""
        return self.text or ""

    def get_content_type(self) -> ContentType:
        """获取内容类型"""
        return self.content_type or ContentType.TEXT


class Message(BaseModel):
    """消息结构（用于 Prompt 评估器）"""
    role: Role = Role.USER
    content: Optional[Content] = None
    ext: Optional[Dict[str, str]] = None


class ArgsSchema(BaseModel):
    """参数 Schema 定义"""
    key: Optional[str] = None
    support_content_types: List[ContentType] = Field(default_factory=list)
    json_schema: Optional[str] = None  # JSON Schema 字符串
    default_value: Optional[Content] = None


class Correction(BaseModel):
    """评估结果修正"""
    score: Optional[float] = None
    explain: Optional[str] = None
    updated_by: Optional[str] = None


class EvaluatorResult(BaseModel):
    """评估结果"""
    score: Optional[float] = Field(None, ge=0.0, le=1.0)
    correction: Optional[Correction] = None
    reasoning: Optional[str] = None


class EvaluatorUsage(BaseModel):
    """评估器使用统计（Token 使用）"""
    input_tokens: int = 0
    output_tokens: int = 0


class EvaluatorRunError(BaseModel):
    """评估器运行错误"""
    code: Optional[int] = None
    message: Optional[str] = None


class EvaluatorOutputData(BaseModel):
    """评估器输出数据"""
    evaluator_result: Optional[EvaluatorResult] = None
    evaluator_usage: Optional[EvaluatorUsage] = None
    evaluator_run_error: Optional[EvaluatorRunError] = None
    time_consuming_ms: Optional[int] = None
    stdout: Optional[str] = None


class EvaluatorInputData(BaseModel):
    """评估器输入数据"""
    history_messages: Optional[List[Message]] = None
    input_fields: Optional[Dict[str, Content]] = None
    evaluate_dataset_fields: Optional[Dict[str, Content]] = None
    evaluate_target_output_fields: Optional[Dict[str, Content]] = None
    ext: Optional[Dict[str, str]] = None

    def get_input_field(self, key: str) -> Optional[Content]:
        """获取输入字段"""
        if self.input_fields:
            return self.input_fields.get(key)
        return None

    def get_dataset_field(self, key: str) -> Optional[Content]:
        """获取数据集字段"""
        if self.evaluate_dataset_fields:
            return self.evaluate_dataset_fields.get(key)
        return None

    def get_target_output_field(self, key: str) -> Optional[Content]:
        """获取目标输出字段"""
        if self.evaluate_target_output_fields:
            return self.evaluate_target_output_fields.get(key)
        return None


# Update forward references
Content.model_rebuild()
Message.model_rebuild()

