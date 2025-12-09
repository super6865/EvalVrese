"""
Prompt evaluator service
"""
import json
import re
import time
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.domain.entity.evaluator_entity import (
    EvaluatorInputData,
    EvaluatorOutputData,
    EvaluatorResult,
    EvaluatorUsage,
    EvaluatorRunError,
    Message,
    Content,
)
from app.domain.entity.evaluator_types import ParseType, Role, ContentType
from app.services.model_config_service import ModelConfigService
from app.utils.autogen_helper import AutoGenEvaluator, create_autogen_config_from_model_config

logger = logging.getLogger(__name__)


class PromptEvaluatorService:
    """Prompt 评估器服务"""
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
    
    def _log_prompt_info(
        self,
        message_list: List[Dict[str, Any]],
        messages: List[Message],
        input_data: EvaluatorInputData,
        model_config: Dict[str, Any],
        prompt_suffix: Optional[str] = None,
    ):
        """
        打印评估器prompt日志信息
        
        Args:
            message_list: 原始消息列表模板
            messages: 构建后的消息列表
            input_data: 输入数据
            model_config: 模型配置
            prompt_suffix: 提示后缀
        """
        logger.info("=" * 80)
        logger.info("[EvaluatorPrompt] ========== Prompt Information ==========")
        
        # Log model configuration
        logger.info("[EvaluatorPrompt] Model Configuration:")
        logger.info(f"[EvaluatorPrompt]   - Provider: {model_config.get('provider', 'N/A')}")
        logger.info(f"[EvaluatorPrompt]   - Model: {model_config.get('model') or model_config.get('model_version', 'N/A')}")
        logger.info(f"[EvaluatorPrompt]   - Model Config ID: {model_config.get('model_config_id', 'N/A')}")
        logger.info(f"[EvaluatorPrompt]   - Temperature: {model_config.get('temperature', 'N/A')}")
        logger.info(f"[EvaluatorPrompt]   - Max Tokens: {model_config.get('max_tokens', 'N/A')}")
        
        # Log dataset fields
        logger.info("[EvaluatorPrompt] Dataset Fields (Input Data):")
        if input_data.input_fields:
            logger.info(f"[EvaluatorPrompt]   - Input Fields ({len(input_data.input_fields)} fields):")
            for key, content in input_data.input_fields.items():
                text_preview = (content.text or "")[:200] if hasattr(content, 'text') and content.text else "N/A"
                logger.info(f"[EvaluatorPrompt]     * {key}: {text_preview}...")
        else:
            logger.info("[EvaluatorPrompt]   - Input Fields: None")
        
        if input_data.evaluate_dataset_fields:
            logger.info(f"[EvaluatorPrompt]   - Evaluate Dataset Fields ({len(input_data.evaluate_dataset_fields)} fields):")
            for key, content in input_data.evaluate_dataset_fields.items():
                text_preview = (content.text or "")[:200] if hasattr(content, 'text') and content.text else "N/A"
                logger.info(f"[EvaluatorPrompt]     * {key}: {text_preview}...")
        else:
            logger.info("[EvaluatorPrompt]   - Evaluate Dataset Fields: None")
        
        if input_data.evaluate_target_output_fields:
            logger.info(f"[EvaluatorPrompt]   - Evaluate Target Output Fields ({len(input_data.evaluate_target_output_fields)} fields):")
            for key, content in input_data.evaluate_target_output_fields.items():
                text_preview = (content.text or "")[:200] if hasattr(content, 'text') and content.text else "N/A"
                logger.info(f"[EvaluatorPrompt]     * {key}: {text_preview}...")
        else:
            logger.info("[EvaluatorPrompt]   - Evaluate Target Output Fields: None")
        
        # Log prompt suffix
        if prompt_suffix:
            logger.info(f"[EvaluatorPrompt] Prompt Suffix: {prompt_suffix[:200]}...")
        else:
            logger.info("[EvaluatorPrompt] Prompt Suffix: None")
        
        # Log original message list template
        logger.info("[EvaluatorPrompt] Original Message List Template:")
        for idx, msg_template in enumerate(message_list):
            role = msg_template.get("role", "user")
            content = msg_template.get("content", {})
            if isinstance(content, dict):
                text = content.get("text", "")
            else:
                text = str(content)
            logger.info(f"[EvaluatorPrompt]   [{idx}] Role: {role}")
            logger.info(f"[EvaluatorPrompt]       Content: {text[:300]}...")
        
        # Log built messages (final prompt)
        logger.info("[EvaluatorPrompt] Built Messages (Final Prompt):")
        for idx, msg in enumerate(messages):
            role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
            content_text = ""
            if msg.content:
                if hasattr(msg.content, 'text') and msg.content.text:
                    content_text = msg.content.text
                else:
                    content_text = str(msg.content)
            logger.info(f"[EvaluatorPrompt]   [{idx}] Role: {role}")
            logger.info(f"[EvaluatorPrompt]       Content: {content_text[:500]}...")
            if len(content_text) > 500:
                logger.info(f"[EvaluatorPrompt]       ... (truncated, total length: {len(content_text)} chars)")
        
        logger.info("[EvaluatorPrompt] ========== End Prompt Information ==========")
        logger.info("=" * 80)
    
    def _build_messages(
        self,
        message_list: List[Dict[str, Any]],
        input_data: EvaluatorInputData,
        prompt_suffix: Optional[str] = None,
    ) -> List[Message]:
        """
        构建消息列表
        
        Args:
            message_list: 消息列表模板
            input_data: 输入数据
            prompt_suffix: 提示后缀
            
        Returns:
            构建后的消息列表
        """
        messages = []
        
        # Process message list template
        for msg_template in message_list:
            role = Role(msg_template.get("role", "user"))
            content_template = msg_template.get("content", {})
            
            # Handle content
            if isinstance(content_template, str):
                content_text = content_template
            elif isinstance(content_template, dict):
                content_text = content_template.get("text", "")
            else:
                content_text = str(content_template)
            
            # Replace variables in content
            # Simple variable replacement: {variable_name}
            if input_data.input_fields:
                for key, value in input_data.input_fields.items():
                    placeholder = f"{{{key}}}"
                    if value and value.text:
                        content_text = content_text.replace(placeholder, value.text)
            
            # Add prompt suffix if exists
            if prompt_suffix and role == Role.USER:
                content_text += "\n" + prompt_suffix
            
            content = Content(content_type=ContentType.TEXT, text=content_text)
            message = Message(role=role, content=content)
            messages.append(message)
        
        # Add history messages if needed
        if input_data.history_messages:
            messages.extend(input_data.history_messages)
        
        return messages
    
    def _parse_response(
        self,
        response_text: str,
        parse_type: ParseType = ParseType.TEXT,
    ) -> Dict[str, Any]:
        """
        解析响应
        
        Args:
            response_text: 响应文本
            parse_type: 解析类型
            
        Returns:
            解析后的结果
        """
        if parse_type == ParseType.JSON:
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON block
            json_blocks = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            for block in json_blocks:
                try:
                    return json.loads(block)
                except json.JSONDecodeError:
                    continue
        
        # Fallback: try to extract score from text
        score_match = re.search(r'score["\s:]*([0-9.]+)', response_text, re.IGNORECASE)
        if score_match:
            try:
                score = float(score_match.group(1))
                return {
                    "score": max(0.0, min(1.0, score)),
                    "reason": response_text,  # Use full response text (no truncation)
                }
            except ValueError:
                pass
        
        return {
            "score": None,
            "reason": response_text,
        }
    
    async def run(
        self,
        message_list: List[Dict[str, Any]],
        model_config: Dict[str, Any],
        input_data: EvaluatorInputData,
        parse_type: ParseType = ParseType.TEXT,
        prompt_suffix: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> EvaluatorOutputData:
        """
        运行 Prompt 评估器
        
        Args:
            message_list: 消息列表
            model_config: 模型配置（必须包含 model_config_id）
            input_data: 输入数据
            parse_type: 解析类型
            prompt_suffix: 提示后缀
            tools: 工具列表（已废弃，保留用于兼容性）
            
        Returns:
            评估器输出数据
        """
        start_time = time.time()
        
        try:
            # Build messages
            messages = self._build_messages(message_list, input_data, prompt_suffix)
            
            # Log prompt information for debugging
            self._log_prompt_info(
                message_list=message_list,
                messages=messages,
                input_data=input_data,
                model_config=model_config,
                prompt_suffix=prompt_suffix,
            )
            
            # Require model_config_id (must use AutoGen framework)
            model_config_id = model_config.get("model_config_id")
            if not model_config_id:
                raise ValueError("model_config_id is required. Please use model configuration from database.")
            
            if not self.db:
                raise ValueError("Database session is required to load model configuration.")
            
            # Load model config from database
            model_config_service = ModelConfigService(self.db)
            model_config_dict = model_config_service.get_config_by_id(
                model_config_id, 
                include_sensitive=True
            )
            
            if not model_config_dict:
                raise ValueError(f"Model configuration {model_config_id} not found")
            
            # Decrypt API key for internal use (get_config_by_id returns masked key)
            from app.models.model_config import ModelConfig
            from app.utils.crypto import decrypt_api_key
            db_config = self.db.query(ModelConfig).filter(ModelConfig.id == model_config_id).first()
            if db_config and db_config.api_key:
                model_config_dict['api_key'] = decrypt_api_key(db_config.api_key)
            
            # Use autogen framework
            return await self._run_with_autogen(
                message_list=message_list,
                model_config_dict=model_config_dict,
                input_data=input_data,
                parse_type=parse_type,
                prompt_suffix=prompt_suffix,
                start_time=start_time,
            )
            
        except Exception as e:
            time_consuming_ms = int((time.time() - start_time) * 1000)
            error = EvaluatorRunError(
                code=500,
                message=str(e),
            )
            return EvaluatorOutputData(
                evaluator_run_error=error,
                time_consuming_ms=time_consuming_ms,
            )
    
    async def _run_with_autogen(
        self,
        message_list: List[Dict[str, Any]],
        model_config_dict: Dict[str, Any],
        input_data: EvaluatorInputData,
        parse_type: ParseType,
        prompt_suffix: Optional[str],
        start_time: float,
    ) -> EvaluatorOutputData:
        """Run evaluator using AutoGen framework"""
        # Extract system message from message_list
        system_message = ""
        user_message = ""
        
        for msg in message_list:
            role = msg.get("role", "user")
            content = msg.get("content", {})
            if isinstance(content, dict):
                text = content.get("text", "")
            else:
                text = str(content)
            
            if role == "system":
                system_message = text
            elif role == "user":
                user_message = text
        
        # Replace variables in messages
        if input_data.input_fields:
            for key, value in input_data.input_fields.items():
                placeholder = f"{{{key}}}"
                if value and value.text:
                    system_message = system_message.replace(placeholder, value.text)
                    user_message = user_message.replace(placeholder, value.text)
        
        # Add prompt suffix
        if prompt_suffix:
            user_message += "\n" + prompt_suffix
        
        # Log prompt information for autogen path
        logger.info("=" * 80)
        logger.info("[EvaluatorPrompt] ========== AutoGen Prompt Information ==========")
        logger.info("[EvaluatorPrompt] Model Configuration:")
        logger.info(f"[EvaluatorPrompt]   - Provider: {model_config_dict.get('provider', 'N/A')}")
        logger.info(f"[EvaluatorPrompt]   - Model: {model_config_dict.get('model') or model_config_dict.get('model_version', 'N/A')}")
        logger.info(f"[EvaluatorPrompt]   - Temperature: {model_config_dict.get('temperature', 'N/A')}")
        logger.info(f"[EvaluatorPrompt]   - Max Tokens: {model_config_dict.get('max_tokens', 'N/A')}")
        
        logger.info("[EvaluatorPrompt] Dataset Fields (Input Data):")
        if input_data.input_fields:
            logger.info(f"[EvaluatorPrompt]   - Input Fields ({len(input_data.input_fields)} fields):")
            for key, content in input_data.input_fields.items():
                text_preview = (content.text or "")[:200] if hasattr(content, 'text') and content.text else "N/A"
                logger.info(f"[EvaluatorPrompt]     * {key}: {text_preview}...")
        else:
            logger.info("[EvaluatorPrompt]   - Input Fields: None")
        
        if input_data.evaluate_dataset_fields:
            logger.info(f"[EvaluatorPrompt]   - Evaluate Dataset Fields ({len(input_data.evaluate_dataset_fields)} fields):")
            for key, content in input_data.evaluate_dataset_fields.items():
                text_preview = (content.text or "")[:200] if hasattr(content, 'text') and content.text else "N/A"
                logger.info(f"[EvaluatorPrompt]     * {key}: {text_preview}...")
        else:
            logger.info("[EvaluatorPrompt]   - Evaluate Dataset Fields: None")
        
        if input_data.evaluate_target_output_fields:
            logger.info(f"[EvaluatorPrompt]   - Evaluate Target Output Fields ({len(input_data.evaluate_target_output_fields)} fields):")
            for key, content in input_data.evaluate_target_output_fields.items():
                text_preview = (content.text or "")[:200] if hasattr(content, 'text') and content.text else "N/A"
                logger.info(f"[EvaluatorPrompt]     * {key}: {text_preview}...")
        else:
            logger.info("[EvaluatorPrompt]   - Evaluate Target Output Fields: None")
        
        if prompt_suffix:
            logger.info(f"[EvaluatorPrompt] Prompt Suffix: {prompt_suffix[:200]}...")
        else:
            logger.info("[EvaluatorPrompt] Prompt Suffix: None")
        
        logger.info("[EvaluatorPrompt] Built Messages:")
        logger.info(f"[EvaluatorPrompt]   - System Message: {system_message[:500]}...")
        if len(system_message) > 500:
            logger.info(f"[EvaluatorPrompt]     ... (truncated, total length: {len(system_message)} chars)")
        logger.info(f"[EvaluatorPrompt]   - User Message: {user_message[:500]}...")
        if len(user_message) > 500:
            logger.info(f"[EvaluatorPrompt]     ... (truncated, total length: {len(user_message)} chars)")
        
        logger.info("[EvaluatorPrompt] ========== End AutoGen Prompt Information ==========")
        logger.info("=" * 80)
        
        # Create AutoGen evaluator
        autogen_config = {
            "system_message": system_message,
            "model_config_dict": model_config_dict,
        }
        
        evaluator = AutoGenEvaluator(autogen_config)
        
        # Build input data for autogen
        input_dict = {}
        if input_data.input_fields:
            for key, value in input_data.input_fields.items():
                if value and value.text:
                    input_dict[key] = value.text
        
        # Get actual output from input_data
        actual_output = ""
        if input_data.evaluate_target_output_fields:
            for key, value in input_data.evaluate_target_output_fields.items():
                if value and value.text:
                    actual_output = value.text
                    break
        
        # Get reference output if available
        # For Code evaluator: from evaluate_dataset_fields
        # For Prompt evaluator: from input_fields (since all fields are merged there)
        reference_output = None
        if input_data.evaluate_dataset_fields:
            # Code evaluator: use evaluate_dataset_fields
            for key, value in input_data.evaluate_dataset_fields.items():
                if value and value.text:
                    reference_output = value.text
                    break
        elif input_data.input_fields:
            # Prompt evaluator: try to find reference_output in input_fields
            # Check common field names for reference output
            reference_field_names = ["reference_output", "answer", "reference", "expected_output"]
            for field_name in reference_field_names:
                if field_name in input_data.input_fields:
                    value = input_data.input_fields[field_name]
                    if value and value.text:
                        reference_output = value.text
                        break
        
        # Evaluate using autogen (synchronous call)
        result = evaluator.evaluate(
            input_data=input_dict,
            actual_output=actual_output or user_message,
            reference_output=reference_output,
        )
        
        # Parse response
        parsed_result = self._parse_response(
            json.dumps(result) if isinstance(result, dict) else str(result),
            parse_type
        )
        
        # Build result
        evaluator_result = EvaluatorResult(
            score=parsed_result.get("score") or result.get("score"),
            reasoning=parsed_result.get("reason", "") or result.get("reason", ""),
        )
        
        # Extract token usage from result
        token_usage = result.get("token_usage", {})
        evaluator_usage = EvaluatorUsage(
            input_tokens=token_usage.get("input_tokens", 0) or 0,
            output_tokens=token_usage.get("output_tokens", 0) or 0,
        )
        
        # Calculate time
        time_consuming_ms = int((time.time() - start_time) * 1000)
        
        return EvaluatorOutputData(
            evaluator_result=evaluator_result,
            evaluator_usage=evaluator_usage,
            time_consuming_ms=time_consuming_ms,
        )
    

