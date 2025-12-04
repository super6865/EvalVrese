"""
AutoGen helper for evaluator implementation
"""
from typing import Dict, Any, Optional, List
import json
import re
from autogen import ConversableAgent
from app.core.config import settings


def _clear_agent_chat_messages(agent: ConversableAgent) -> None:
    try:
        if hasattr(agent, 'chat_messages'):
            if isinstance(agent.chat_messages, list):
                agent.chat_messages.clear()
            elif isinstance(agent.chat_messages, dict):
                agent.chat_messages.clear()
            else:
                try:
                    agent.chat_messages = []
                except (AttributeError, TypeError):
                    pass
    except Exception:
        pass


def create_autogen_config_from_model_config(model_config_dict: Dict[str, Any]) -> Dict[str, Any]:
    model_type = model_config_dict.get('model_type', 'openai').lower()
    
    autogen_config = {
        "model": model_config_dict.get('model_version', 'gpt-4'),
        "api_key": model_config_dict.get('api_key'),
    }
    
    if model_config_dict.get('api_base'):
        autogen_config["base_url"] = model_config_dict['api_base']
    
    temperature = model_config_dict.get('temperature')
    if temperature is not None:
        if isinstance(temperature, str):
            try:
                temperature = float(temperature)
            except (ValueError, TypeError):
                temperature = None
        elif not isinstance(temperature, (int, float)):
            try:
                temperature = float(temperature)
            except (ValueError, TypeError):
                temperature = None
        if temperature is not None:
            autogen_config["temperature"] = temperature
    
    max_tokens = model_config_dict.get('max_tokens')
    if max_tokens is not None:
        if isinstance(max_tokens, str):
            try:
                max_tokens = int(max_tokens)
            except (ValueError, TypeError):
                max_tokens = None
        elif not isinstance(max_tokens, int):
            try:
                max_tokens = int(max_tokens)
            except (ValueError, TypeError):
                max_tokens = None
        if max_tokens is not None:
            autogen_config["max_tokens"] = max_tokens
    
    if model_type in ['qwen', 'aliyun', 'dashscope']:
        if not autogen_config.get('base_url'):
            autogen_config["base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    elif model_type == 'deepseek':
        if not autogen_config.get('base_url'):
            autogen_config["base_url"] = "https://api.deepseek.com"
    elif model_type == 'openai':
        if not autogen_config.get('base_url'):
            autogen_config["base_url"] = "https://api.openai.com/v1"
    
    timeout = model_config_dict.get('timeout', 120)
    if isinstance(timeout, str):
        try:
            timeout = int(timeout)
        except (ValueError, TypeError):
            timeout = 120
    elif not isinstance(timeout, int):
        timeout = int(timeout) if timeout is not None else 120
    
    autogen_config["timeout"] = timeout
    
    llm_config = {
        "config_list": [autogen_config],
        "timeout": timeout,
    }
    
    if model_config_dict.get('temperature') is not None:
        llm_config["temperature"] = model_config_dict['temperature']
    
    return llm_config


class AutoGenEvaluator:
    """AutoGen-based evaluator using ConversableAgent"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AutoGen evaluator
        
        Args:
            config: Configuration dictionary containing:
                - system_message: System prompt for evaluation
                - llm_config: LLM configuration (model, api_key, etc.) or model_config_dict
                - model_config_dict: Model configuration dictionary from database (alternative to llm_config)
        """
        self.system_message = config.get("system_message", self._default_system_message())
        
        if "model_config_dict" in config:
            self.llm_config = create_autogen_config_from_model_config(config["model_config_dict"])
        else:
            llm_config = config.get("llm_config", self._default_llm_config())
            if "config_list" not in llm_config:
                self.llm_config = {
                    "config_list": [llm_config] if isinstance(llm_config, dict) else llm_config,
                    "timeout": llm_config.get("timeout", 60) if isinstance(llm_config, dict) else 60,
                }
            else:
                self.llm_config = llm_config
        
        # Create evaluator agent
        self.evaluator_agent = ConversableAgent(
            name="evaluator",
            system_message=self.system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER",  # No human input needed
            max_consecutive_auto_reply=1,
        )
    
    def _default_system_message(self) -> str:
        """Default system message for evaluation"""
        return """You are an expert evaluator. Your task is to evaluate the quality of AI-generated outputs.

Given:
- Input: The input provided to the AI system
- Actual Output: The output generated by the AI system
- Reference Output: The expected/reference output (if available)

Evaluate the actual output and provide:
1. A score from 0.0 to 1.0 (where 1.0 is perfect)
2. A detailed reason explaining your evaluation

Return your response in JSON format:
{
    "score": 0.85,
    "reason": "The output is mostly correct but lacks some details..."
}"""
    
    def _default_llm_config(self) -> Dict[str, Any]:
        """Default LLM configuration"""
        return {
            "config_list": [{
                "model": settings.DEFAULT_LLM_MODEL,
                "api_key": settings.OPENAI_API_KEY,
            }],
            "timeout": 60,
            "temperature": 0.3,
        }
    
    def evaluate(
        self,
        input_data: Dict[str, Any],
        actual_output: str,
        reference_output: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate using AutoGen agent
        
        Args:
            input_data: Input data dictionary
            actual_output: Actual output from evaluation target
            reference_output: Reference output (optional)
        
        Returns:
            Dictionary with evaluation result:
            - score: float (0-1)
            - reason: str
            - details: dict (optional)
        """
        # Build evaluation message
        message_parts = [
            "Please evaluate the following:",
            f"\nInput: {json.dumps(input_data, ensure_ascii=False)}",
            f"\nActual Output: {actual_output}",
        ]
        
        if reference_output:
            message_parts.append(f"\nReference Output: {reference_output}")
        
        message_parts.append(
            "\n\nPlease provide your evaluation in JSON format with 'score' (0.0-1.0) and 'reason' fields."
        )
        
        message = "".join(message_parts)
        
        try:
            _clear_agent_chat_messages(self.evaluator_agent)
            
            response = self.evaluator_agent.generate_reply(
                messages=[{"role": "user", "content": message}]
            )
            
            token_usage = self._extract_token_usage()
            result = self._parse_evaluation_response(response)
            result["token_usage"] = token_usage
            
            return result
            
        except Exception as e:
            return {
                "score": None,
                "reason": f"Evaluation error: {str(e)}",
                "details": {"error": "evaluation_error", "message": str(e)},
                "token_usage": {"input_tokens": 0, "output_tokens": 0},
            }
    
    def _extract_token_usage(self) -> Dict[str, int]:
        """
        Extract token usage from AutoGen agent's internal state
        
        Returns:
            Dictionary with input_tokens and output_tokens
        """
        input_tokens = 0
        output_tokens = 0
        
        try:
            if hasattr(self.evaluator_agent, 'last_cost'):
                cost_info = self.evaluator_agent.last_cost
                if isinstance(cost_info, dict):
                    input_tokens = cost_info.get("input_tokens", 0) or cost_info.get("prompt_tokens", 0)
                    output_tokens = cost_info.get("output_tokens", 0) or cost_info.get("completion_tokens", 0)
            
            if hasattr(self.evaluator_agent, 'usage'):
                usage = self.evaluator_agent.usage
                if isinstance(usage, dict):
                    input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0) or input_tokens
                    output_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0) or output_tokens
            
            if hasattr(self.evaluator_agent, 'chat_messages'):
                messages = self.evaluator_agent.chat_messages
                if messages and len(messages) > 0:
                    last_message = messages[-1]
                    if isinstance(last_message, dict) and "usage" in last_message:
                        usage = last_message["usage"]
                        if isinstance(usage, dict):
                            input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0) or input_tokens
                            output_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0) or output_tokens
                    elif hasattr(last_message, "usage"):
                        usage = last_message.usage
                        if isinstance(usage, dict):
                            input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0) or input_tokens
                            output_tokens = usage.get("output_tokens", 0) or usage.get("completion_tokens", 0) or output_tokens
            
            if hasattr(self.evaluator_agent, 'client'):
                client = self.evaluator_agent.client
                if hasattr(client, 'last_response') and client.last_response:
                    response = client.last_response
                    if hasattr(response, 'usage'):
                        usage = response.usage
                        if hasattr(usage, 'prompt_tokens'):
                            input_tokens = usage.prompt_tokens or input_tokens
                        if hasattr(usage, 'completion_tokens'):
                            output_tokens = usage.completion_tokens or output_tokens
                    elif isinstance(response, dict) and "usage" in response:
                        usage = response["usage"]
                        if isinstance(usage, dict):
                            input_tokens = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or input_tokens
                            output_tokens = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or output_tokens
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to extract token usage from AutoGen agent: {str(e)}")
        
        return {
            "input_tokens": int(input_tokens) if input_tokens else 0,
            "output_tokens": int(output_tokens) if output_tokens else 0,
        }
    
    def _parse_evaluation_response(self, response: Any) -> Dict[str, Any]:
        """Parse evaluation response from AutoGen agent"""
        if isinstance(response, dict):
            content = response.get("content", "")
        elif hasattr(response, "content"):
            content = response.content
        else:
            content = str(response)
        
        json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                score = result.get("score")
                reason = result.get("reason", "")
                
                if score is not None:
                    try:
                        score = float(score)
                        score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                    except (ValueError, TypeError):
                        score = None
                
                return {
                    "score": score,
                    "reason": str(reason) if reason else "",
                    "details": result.get("details", {}),
                    "token_usage": {"input_tokens": 0, "output_tokens": 0},
                }
            except json.JSONDecodeError:
                pass
        
        # Fallback: try to extract score from text
        score_match = re.search(r'score["\s:]*([0-9.]+)', content, re.IGNORECASE)
        if score_match:
            try:
                score = float(score_match.group(1))
                score = max(0.0, min(1.0, score))
                return {
                    "score": score,
                    "reason": content,  # Use full content as reason (no truncation)
                    "details": {},
                    "token_usage": {"input_tokens": 0, "output_tokens": 0},  # Will be set by caller
                }
            except ValueError:
                pass
        
        return {
            "score": None,
            "reason": f"Could not parse evaluation result from response: {content}",
            "details": {"error": "parse_error", "raw_response": content},
            "token_usage": {"input_tokens": 0, "output_tokens": 0},
        }


class AutoGenTargetInvoker:
    """AutoGen-based target invoker for unified evaluation target calling"""
    
    def __init__(self, config: Dict[str, Any], db=None):
        """
        Initialize AutoGen target invoker
        
        Args:
            config: Configuration dictionary containing target type and settings
            db: Database session (optional, for loading model configs)
        """
        self.config = config
        self.db = db
        self.target_type = config.get("type", "none")
        self.agent = None
        self.tools = []
        
        if self.target_type == "model_set":
            self._init_model_set_target()
        elif self.target_type == "prompt":
            self._init_prompt_target()
        elif self.target_type == "api":
            self._init_api_target()
        elif self.target_type == "none":
            pass
        else:
            raise ValueError(f"Unsupported target type: {self.target_type}")
    
    def _init_model_set_target(self):
        """Initialize model_set type target using AutoGen"""
        try:
            from app.services.model_set_service import ModelSetService
        except ImportError as e:
            raise ImportError(
                f"Failed to import ModelSetService: {str(e)}. "
                "Please ensure the module is available and Python path is correctly configured."
            ) from e
        
        model_set_id = self.config.get("model_set_id")
        if not model_set_id:
            raise ValueError("model_set_id is required for model_set type")
        
        try:
            model_set_service = ModelSetService(self.db)
            model_set = model_set_service.get_model_set_by_id(model_set_id)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize model set service: {str(e)}") from e
        
        if not model_set:
            raise ValueError(f"Model set {model_set_id} not found")
        
        if model_set["type"] == "llm_model":
            # Use AutoGen ConversableAgent for LLM models
            model_config = model_set["config"]
            
            # Ensure timeout is an integer (may come as string from JSON)
            timeout_value = model_config.get("timeout", 60)
            if isinstance(timeout_value, str):
                try:
                    timeout_value = int(timeout_value)
                except (ValueError, TypeError):
                    timeout_value = 60
            elif not isinstance(timeout_value, int):
                timeout_value = int(timeout_value) if timeout_value is not None else 60
            
            # Ensure temperature is a float (may come as string from JSON)
            temperature_value = model_config.get("temperature")
            if temperature_value is not None:
                if isinstance(temperature_value, str):
                    try:
                        temperature_value = float(temperature_value)
                    except (ValueError, TypeError):
                        temperature_value = None
                elif not isinstance(temperature_value, (int, float)):
                    try:
                        temperature_value = float(temperature_value)
                    except (ValueError, TypeError):
                        temperature_value = None
            
            # Ensure max_tokens is an integer (may come as string from JSON)
            max_tokens_value = model_config.get("max_tokens")
            if max_tokens_value is not None:
                if isinstance(max_tokens_value, str):
                    try:
                        max_tokens_value = int(max_tokens_value)
                    except (ValueError, TypeError):
                        max_tokens_value = None
                elif not isinstance(max_tokens_value, int):
                    try:
                        max_tokens_value = int(max_tokens_value)
                    except (ValueError, TypeError):
                        max_tokens_value = None
            
            # Convert model config to autogen config
            autogen_config = create_autogen_config_from_model_config({
                "model_type": model_config.get("model_type", "openai"),
                "model_version": model_config.get("model_version"),
                "api_key": model_config.get("api_key"),
                "api_base": model_config.get("api_base"),
                "temperature": temperature_value,
                "max_tokens": max_tokens_value,
                "timeout": timeout_value,
            })
            
            # Create agent with minimal system message (just for calling, not evaluation)
            self.agent = ConversableAgent(
                name="target",
                system_message="You are a helpful assistant. Respond to user requests directly and concisely.",
                llm_config=autogen_config,
                human_input_mode="NEVER",
                max_consecutive_auto_reply=1,
            )
        elif model_set["type"] == "agent_api":
            # For agent API, we'll use AutoGen's function calling capability
            # Create a tool that wraps the API call
            self._create_api_tool(model_set["config"])
            
            # Create agent with the API tool
            # For API calls, we might not need LLM, but we can use a simple agent
            # or directly call the API. Let's use a simple approach with tool calling
            self.agent = ConversableAgent(
                name="target",
                system_message="You are a helpful assistant that can call external APIs.",
                llm_config=None,  # No LLM needed for direct API calls
                human_input_mode="NEVER",
                max_consecutive_auto_reply=1,
            )
        else:
            raise ValueError(f"Unsupported model set type: {model_set['type']}")
    
    def _init_prompt_target(self):
        """Initialize prompt type target using AutoGen"""
        # For prompt type, we need LLM config to call the model
        # Try to get model_config_id from config
        model_config_id = self.config.get("model_config_id")
        if not model_config_id or not self.db:
            raise ValueError("Prompt type target requires model_config_id and database session for LLM configuration")
        
        from app.services.model_config_service import ModelConfigService
        model_config_service = ModelConfigService(self.db)
        model_config_dict = model_config_service.get_config_by_id(
            model_config_id,
            include_sensitive=True
        )
        
        if not model_config_dict:
            raise ValueError(f"Model configuration {model_config_id} not found")
        
        prompt_template = self.config.get("prompt_template", "")
        autogen_config = create_autogen_config_from_model_config(model_config_dict)
        
        self.agent = ConversableAgent(
            name="target",
            system_message=prompt_template or "You are a helpful assistant.",
            llm_config=autogen_config,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )
    
    def _init_api_target(self):
        """Initialize API type target - create a tool for API calling"""
        api_config = {
            "url": self.config.get("url"),
            "method": self.config.get("method", "POST"),
            "headers": self.config.get("headers", {}),
        }
        self._create_api_tool(api_config)
        
        # For direct API calls, we might not need an agent
        # But we can create a simple one for consistency
        self.agent = ConversableAgent(
            name="target",
            system_message="You are a helpful assistant that can call external APIs.",
            llm_config=None,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
        )
    
    def _create_api_tool(self, api_config: Dict[str, Any]):
        """Create an AutoGen tool for API calling"""
        # Store API config for later use
        self.api_config = api_config
    
    async def invoke(self, input_data: Dict[str, Any]) -> str:
        """
        Invoke the evaluation target with input data
        
        Args:
            input_data: Input data dictionary
            
        Returns:
            Output string from the target
        """
        if self.target_type == "none":
            return str(input_data)
        
        if self.target_type == "api":
            # Direct API call
            return await self._invoke_api(input_data)
        
        if self.target_type == "model_set":
            model_set_id = self.config.get("model_set_id")
            try:
                from app.services.model_set_service import ModelSetService
            except ImportError as e:
                raise ImportError(
                    f"Failed to import ModelSetService: {str(e)}. "
                    "Please ensure the module is available and Python path is correctly configured."
                ) from e
            
            try:
                model_set_service = ModelSetService(self.db)
                model_set = model_set_service.get_model_set_by_id(model_set_id)
            except Exception as e:
                raise RuntimeError(f"Failed to get model set {model_set_id}: {str(e)}") from e
            
            if model_set["type"] == "agent_api":
                # Use API tool
                return await self._invoke_agent_api(model_set["config"], input_data)
            elif model_set["type"] == "llm_model":
                # Use LLM agent
                return await self._invoke_llm(input_data)
        
        if self.target_type == "prompt":
            # Use prompt agent
            return await self._invoke_prompt(input_data)
        
        raise ValueError(f"Unsupported target type: {self.target_type}")
    
    async def _invoke_llm(self, input_data: Dict[str, Any]) -> str:
        """Invoke LLM model using AutoGen agent"""
        # Build prompt from input_data
        prompt_text = None
        if "prompt" in input_data:
            prompt_text = input_data["prompt"]
        elif "input" in input_data:
            prompt_text = input_data["input"]
        else:
            # Use first text field
            for key, value in input_data.items():
                if isinstance(value, str):
                    prompt_text = value
                    break
        
        if not prompt_text:
            prompt_text = json.dumps(input_data, ensure_ascii=False)
        
        # Clear chat_messages history before generating reply
        # This ensures each target invocation is independent and doesn't reuse previous results
        if self.agent:
            _clear_agent_chat_messages(self.agent)
        
        # Generate reply using AutoGen agent
        # Note: AutoGen's generate_reply is synchronous, but we're in async context
        # We need to run it in a thread pool
        import asyncio
        loop = asyncio.get_event_loop()
        
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.agent.generate_reply(
                    messages=[{"role": "user", "content": prompt_text}]
                )
            )
        except Exception as e:
            # Capture connection errors and other exceptions from AutoGen/LLM calls
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Check for common connection-related errors
            if "connection" in error_msg.lower() or "connect" in error_msg.lower():
                raise ValueError(f"Connection error: Failed to connect to LLM service: {error_msg} (type: {error_type})")
            elif "timeout" in error_msg.lower():
                raise ValueError(f"Timeout error: LLM request timed out: {error_msg} (type: {error_type})")
            elif "api" in error_msg.lower() and "key" in error_msg.lower():
                raise ValueError(f"Authentication error: Invalid API key or authentication failed: {error_msg} (type: {error_type})")
            else:
                # Generic error handling
                raise ValueError(f"LLM invocation error: {error_msg} (type: {error_type})")
        
        # Extract content from response
        if isinstance(response, dict):
            content = response.get("content", "")
        elif hasattr(response, "content"):
            content = response.content
        else:
            content = str(response)
        
        return content
    
    async def _invoke_prompt(self, input_data: Dict[str, Any]) -> str:
        """Invoke prompt target using AutoGen agent"""
        prompt_template = self.config.get("prompt_template", "")
        variables = self.config.get("variables", {})
        
        # Replace variables in template
        prompt = prompt_template
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{key}}}", str(input_data.get(value, "")))
        
        # Use LLM agent to generate response
        return await self._invoke_llm({"prompt": prompt})
    
    async def _invoke_api(self, input_data: Dict[str, Any]) -> str:
        """Invoke direct API call"""
        import httpx
        
        api_url = self.config.get("url")
        method = self.config.get("method", "POST")
        headers = self.config.get("headers", {})
        body = self.config.get("body", input_data)
        
        # Configure timeout: 120 seconds total, 10 seconds for connection (increased from 60 to handle slow connections)
        timeout = httpx.Timeout(120.0, connect=10.0)
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method.upper() == "POST":
                    response = await client.post(api_url, json=body, headers=headers)
                elif method.upper() == "GET":
                    response = await client.get(api_url, params=body, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                response.raise_for_status()
                result = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                return json.dumps(result) if isinstance(result, dict) else str(result)
        except httpx.ConnectError as e:
            raise ValueError(f"Connection error: Failed to connect to {api_url} (method: {method}): {str(e)}")
        except httpx.TimeoutException as e:
            raise ValueError(f"Timeout error: Request to {api_url} (method: {method}) timed out after 120 seconds: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"HTTP error: {api_url} returned status {e.response.status_code}: {str(e)}")
        except httpx.HTTPError as e:
            raise ValueError(f"HTTP error: Request to {api_url} (method: {method}) failed: {str(e)}")
    
    async def _invoke_agent_api(self, api_config: Dict[str, Any], input_data: Dict[str, Any]) -> str:
        """Invoke agent API using configured API call"""
        import httpx
        
        api_url = api_config.get("api_url")
        api_method = api_config.get("api_method", "POST")
        api_headers = api_config.get("api_headers", {})
        api_body_template = api_config.get("api_body_template", {})
        input_mapping = api_config.get("input_mapping", {})
        
        # Map input_data to API body
        api_body = {}
        if input_mapping:
            for api_key, input_key in input_mapping.items():
                if input_key in input_data:
                    api_body[api_key] = input_data[input_key]
        else:
            api_body = input_data
        
        # Apply body template
        if api_body_template:
            for key, value in api_body_template.items():
                if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                    placeholder = value[1:-1]
                    if placeholder in api_body:
                        api_body[key] = api_body[placeholder]
                elif key not in api_body:
                    api_body[key] = value
        
        # Get timeout from config, default to 120 seconds (increased from 60 to handle slow connections)
        timeout_seconds = api_config.get("timeout", 120.0)
        timeout = httpx.Timeout(timeout_seconds, connect=10.0)
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if api_method.upper() == "POST":
                    response = await client.post(api_url, json=api_body, headers=api_headers)
                elif api_method.upper() == "GET":
                    response = await client.get(api_url, params=api_body, headers=api_headers)
                elif api_method.upper() == "PUT":
                    response = await client.put(api_url, json=api_body, headers=api_headers)
                elif api_method.upper() == "PATCH":
                    response = await client.patch(api_url, json=api_body, headers=api_headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {api_method}")
                response.raise_for_status()
                result = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                return json.dumps(result) if isinstance(result, dict) else str(result)
        except httpx.ConnectError as e:
            raise ValueError(f"Connection error: Failed to connect to {api_url} (method: {api_method}): {str(e)}")
        except httpx.TimeoutException as e:
            raise ValueError(f"Timeout error: Request to {api_url} (method: {api_method}) timed out after {timeout_seconds} seconds: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"HTTP error: {api_url} returned status {e.response.status_code}: {str(e)}")
        except httpx.HTTPError as e:
            raise ValueError(f"HTTP error: Request to {api_url} (method: {api_method}) failed: {str(e)}")

