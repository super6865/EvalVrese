"""
AutoGen helper utilities for LLM invocation
"""
from typing import Dict, Any, Optional, List
import json
import re
import logging
from autogen import ConversableAgent
from app.utils.crypto import decrypt_api_key

logger = logging.getLogger(__name__)


def _clear_agent_chat_messages(agent: ConversableAgent) -> None:
    """
    Clear all chat messages and cached state from AutoGen ConversableAgent.
    This ensures each invocation is independent and doesn't reuse previous results.
    """
    if not agent:
        return
    
    try:
        # Clear chat_messages (primary message history)
        if hasattr(agent, 'chat_messages'):
            if isinstance(agent.chat_messages, list):
                agent.chat_messages.clear()
                logger.debug("[ClearCache] Cleared chat_messages (list)")
            elif isinstance(agent.chat_messages, dict):
                agent.chat_messages.clear()
                logger.debug("[ClearCache] Cleared chat_messages (dict)")
            else:
                try:
                    agent.chat_messages = []
                    logger.debug("[ClearCache] Reset chat_messages to empty list")
                except (AttributeError, TypeError):
                    pass
        
        # Clear _oai_messages if exists (OpenAI API messages cache)
        if hasattr(agent, '_oai_messages'):
            if isinstance(agent._oai_messages, list):
                agent._oai_messages.clear()
                logger.debug("[ClearCache] Cleared _oai_messages (list)")
            elif isinstance(agent._oai_messages, dict):
                agent._oai_messages.clear()
                logger.debug("[ClearCache] Cleared _oai_messages (dict)")
            else:
                try:
                    agent._oai_messages = []
                    logger.debug("[ClearCache] Reset _oai_messages to empty list")
                except (AttributeError, TypeError):
                    pass
        
        # DO NOT clear _oai_system_message - it's required by AutoGen's generate_oai_reply
        # AutoGen expects _oai_system_message to be a string or list, not None
        # The system message is part of the agent's configuration, not chat history
        # We only need to clear chat history (chat_messages and _oai_messages)
        
        # Clear client cache if exists (may contain token usage, cost, etc.)
        if hasattr(agent, 'client'):
            client = agent.client
            if client:
                # Clear cost cache if exists
                if hasattr(client, 'cost'):
                    try:
                        if isinstance(client.cost, dict):
                            client.cost.clear()
                            logger.debug("[ClearCache] Cleared client.cost")
                    except (AttributeError, TypeError):
                        pass
                
                # Clear usage cache if exists
                if hasattr(client, 'usage'):
                    try:
                        if isinstance(client.usage, dict):
                            client.usage.clear()
                            logger.debug("[ClearCache] Cleared client.usage")
                    except (AttributeError, TypeError):
                        pass
        
        # Clear any message history in nested structures
        if hasattr(agent, 'messages'):
            try:
                if isinstance(agent.messages, list):
                    agent.messages.clear()
                    logger.debug("[ClearCache] Cleared messages (list)")
                elif isinstance(agent.messages, dict):
                    agent.messages.clear()
                    logger.debug("[ClearCache] Cleared messages (dict)")
            except (AttributeError, TypeError):
                pass
        
        logger.info("[ClearCache] ✅ Successfully cleared all agent chat messages and cached state")
        
    except Exception as e:
        logger.warning(f"[ClearCache] ⚠️ Warning: Failed to clear some agent cache: {str(e)}")
        # Don't raise exception, just log warning


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
    
    # Merge extra_body to disable thinking mode for all models by default
    # This prevents models like kimi-k2-thinking from using deep thinking mode
    # Default values: disable thinking mode
    default_extra_body = {
        "enable_thinking": False,
        "thinking_depth": 0,
    }
    
    # If model_config_dict has extra_body, merge it with default values
    # Default values take priority, but user can override if needed
    if "extra_body" in model_config_dict and isinstance(model_config_dict["extra_body"], dict):
        user_extra_body = model_config_dict["extra_body"]
        # Merge: default values first, then user values (user can override defaults)
        merged_extra_body = {**default_extra_body, **user_extra_body}
        autogen_config["extra_body"] = merged_extra_body
    else:
        # If no user-defined extra_body, use default values
        autogen_config["extra_body"] = default_extra_body
    
    llm_config = {
        "config_list": [autogen_config],
        "timeout": timeout,
    }
    
    if model_config_dict.get('temperature') is not None:
        llm_config["temperature"] = model_config_dict['temperature']
    
    return llm_config


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
        self.agent = None  # Will be created fresh for each invocation
        self.tools = []
        
        # Store configuration but don't create agent yet
        # Agent will be created fresh for each invoke() call to avoid state pollution
        if self.target_type == "prompt":
            # Load prompt configuration (but don't create agent yet)
            self._load_prompt_config()
        elif self.target_type == "model_set":
            # Load model_set configuration (but don't create agent yet)
            self._load_model_set_config()
        elif self.target_type == "api":
            self._init_api_target()
        elif self.target_type == "none":
            pass
        else:
            raise ValueError(f"Unsupported target type: {self.target_type}")
    
    def _load_model_set_config(self):
        """Load model_set configuration (without creating agent)"""
        try:
            from app.models.model_set import ModelSet
        except ImportError as e:
            raise ImportError(
                f"Failed to import ModelSet: {str(e)}. "
                "Please ensure the module is available and Python path is correctly configured."
            ) from e
        
        model_set_id = self.config.get("model_set_id")
        if not model_set_id:
            raise ValueError("model_set_id is required for model_set type")
        
        try:
            # Load model_set directly from database to get original config (not masked)
            # This is for internal use, so we need the actual encrypted API key, not the masked version
            model_set = self.db.query(ModelSet).filter(ModelSet.id == model_set_id).first()
        except Exception as e:
            raise RuntimeError(f"Failed to load model set from database: {str(e)}") from e
        
        if not model_set:
            raise ValueError(f"Model set {model_set_id} not found")
        
        # Convert to dict format, but keep original config (don't mask API key for internal use)
        model_set_dict = {
            'id': model_set.id,
            'name': model_set.name,
            'description': model_set.description,
            'type': model_set.type,
            'config': model_set.config.copy() if model_set.config else {},  # Keep original config with encrypted API key
            'created_at': model_set.created_at.isoformat() if model_set.created_at else None,
            'updated_at': model_set.updated_at.isoformat() if model_set.updated_at else None,
            'created_by': model_set.created_by,
        }
        
        # Store model_set config for later use
        self.model_set_config = model_set_dict
    
    def _create_model_set_agent(self) -> ConversableAgent:
        """Create a fresh model_set agent instance for each invocation"""
        if not hasattr(self, 'model_set_config'):
            raise ValueError("Model set config not loaded. Call _load_model_set_config first.")
        
        model_set = self.model_set_config
        
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
            
            # Check and log temperature setting
            if temperature_value is None or temperature_value == 0:
                logger.warning(f"[CreateModelSetAgent] ⚠️ Temperature is {temperature_value}, which may cause deterministic responses. Consider setting temperature > 0 for randomness.")
            else:
                logger.info(f"[CreateModelSetAgent] Temperature set to {temperature_value}")
            
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
            
            # Decrypt API key if it exists
            # Model set config stores API key in encrypted format
            # decrypt_api_key handles both encrypted and plain text keys automatically
            encrypted_api_key = model_config.get("api_key")
            if not encrypted_api_key:
                raise ValueError("API key is required for llm_model type model_set")
            
            # decrypt_api_key will automatically detect if the key is encrypted or plain text
            # and return the appropriate value
            # Note: decrypt_api_key checks for 'gAAAAAB' prefix internally
            try:
                api_key = decrypt_api_key(encrypted_api_key)
                if api_key == encrypted_api_key and encrypted_api_key.startswith('gAAAAAB'):
                    # If decrypt_api_key returned the same value for an encrypted key, decryption failed
                    logger.error(f"[CreateModelSetAgent] API key decryption failed - key appears encrypted but was not decrypted")
                    raise ValueError("API key decryption failed")
                logger.info(f"[CreateModelSetAgent] Successfully processed API key (encrypted: {encrypted_api_key.startswith('gAAAAAB') if isinstance(encrypted_api_key, str) else False})")
            except ValueError as ve:
                # Re-raise ValueError as-is
                raise
            except Exception as e:
                logger.error(f"[CreateModelSetAgent] Failed to process API key: {str(e)}", exc_info=True)
                raise ValueError(f"Failed to process API key: {str(e)}")
            
            if not api_key:
                raise ValueError("API key is required for llm_model type model_set")
            
            # Convert model config to autogen config
            autogen_config = create_autogen_config_from_model_config({
                "model_type": model_config.get("model_type", "openai"),
                "model_version": model_config.get("model_version"),
                "api_key": api_key,  # Use decrypted API key
                "api_base": model_config.get("api_base"),
                "temperature": temperature_value,
                "max_tokens": max_tokens_value,
                "timeout": timeout_value,
            })
            
            # Create fresh agent instance for this invocation
            logger.info(f"[CreateModelSetAgent] Creating fresh agent instance (temperature={temperature_value})")
            agent = ConversableAgent(
                name="target",
                system_message="You are a helpful assistant. Respond to user requests directly and concisely.",
                llm_config=autogen_config,
                human_input_mode="NEVER",
                max_consecutive_auto_reply=1,
            )
            return agent
        elif model_set["type"] == "agent_api":
            # For agent API, create a simple agent
            self._create_api_tool(model_set["config"])
            logger.info(f"[CreateModelSetAgent] Creating fresh agent instance for API calls")
            agent = ConversableAgent(
                name="target",
                system_message="You are a helpful assistant that can call external APIs.",
                llm_config=None,  # No LLM needed for direct API calls
                human_input_mode="NEVER",
                max_consecutive_auto_reply=1,
            )
            return agent
        else:
            raise ValueError(f"Unsupported model set type: {model_set['type']}")
    
    def _load_prompt_config(self):
        """Load prompt configuration (without creating agent)"""
        if not self.db:
            raise ValueError("Prompt type target requires database session")
        
        # Get prompt_id and prompt_version from config
        prompt_id = self.config.get("prompt_id")
        if not prompt_id:
            raise ValueError("prompt_id is required for prompt type target")
        
        prompt_version = self.config.get("prompt_version")  # Can be None for draft
        
        # Load prompt configuration from database
        from app.services.prompt_service import PromptService
        prompt_service = PromptService(self.db)
        
        prompt = prompt_service.get_prompt(prompt_id)
        if not prompt:
            raise ValueError(f"Prompt {prompt_id} not found")
        
        # Load prompt content (from version or draft)
        prompt_content = None
        if prompt_version and prompt_version != "draft":
            # Load from version
            version = prompt_service.get_version(prompt_id, prompt_version)
            if not version:
                raise ValueError(f"Prompt version '{prompt_version}' not found")
            prompt_content = version.content
        else:
            # Load from draft
            if not prompt.draft_detail:
                raise ValueError(f"Prompt {prompt_id} has no draft or version")
            prompt_content = prompt.draft_detail
            # Remove metadata if exists
            if isinstance(prompt_content, dict) and '_metadata' in prompt_content:
                prompt_content = {k: v for k, v in prompt_content.items() if k != '_metadata'}
        
        if not prompt_content:
            raise ValueError(f"Prompt {prompt_id} has no content")
        
        # Extract configuration from prompt content
        self.prompt_messages = prompt_content.get("messages", [])
        self.prompt_model_config = prompt_content.get("model_config", {})
        self.prompt_tools = prompt_content.get("tools", [])
        
        # Convert variables to dict format if it's a list
        # Frontend may store variables as: [{"name": "var1", "value": "value1"}, ...]
        # Or as dict: {"var1": "value1", ...}
        variables_raw = prompt_content.get("variables", {})
        if isinstance(variables_raw, list):
            # Convert list format to dict: [{"name": "var1", "value": "value1"}] -> {"var1": "value1"}
            self.prompt_variables = {}
            for var_item in variables_raw:
                if isinstance(var_item, dict) and "name" in var_item:
                    var_name = var_item.get("name")
                    if var_name:  # Only add if var_name is not None or empty
                        var_value = var_item.get("value", "")
                        self.prompt_variables[var_name] = var_value
        elif isinstance(variables_raw, dict):
            # Already in dict format
            self.prompt_variables = variables_raw
        else:
            self.prompt_variables = {}
        
        # Store variable_mapping and user_input_mapping for later use
        self.variable_mapping = self.config.get("variable_mapping", {})
        self.user_input_mapping = self.config.get("user_input_mapping")  # Field key for user input
        
        # Store model_config_id for later use (will be used by LLMService)
        self.prompt_model_config_id = self.prompt_model_config.get("model_config_id")
        if not self.prompt_model_config_id:
            raise ValueError("Prompt model_config must contain model_config_id")
    
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
            # Use prompt agent - create fresh agent for each invocation
            return await self._invoke_prompt(input_data)
        
        raise ValueError(f"Unsupported target type: {self.target_type}")
    
    async def _invoke_llm(self, input_data: Dict[str, Any]) -> str:
        """Invoke LLM model using AutoGen agent or LLMService"""
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
        
        # Check if model_set config has model_config_id (preferred way)
        if not hasattr(self, 'model_set_config'):
            raise ValueError("Model set config not loaded. Call _load_model_set_config first.")
        
        model_set = self.model_set_config
        if model_set["type"] != "llm_model":
            raise ValueError(f"Expected llm_model type, got {model_set['type']}")
        
        model_config = model_set["config"]
        model_config_id = model_config.get("model_config_id")
        
        # Use LLMService if model_config_id is available
        if model_config_id:
            logger.info(f"[InvokeLLM] Using LLMService with model_config_id={model_config_id}")
            from app.services.llm_service import LLMService
            
            llm_service = LLMService(self.db)
            
            # Get temperature, max_tokens, timeout from model_config (may override model_config defaults)
            temperature = model_config.get("temperature")
            max_tokens = model_config.get("max_tokens")
            timeout = model_config.get("timeout")
            
            llm_response = await llm_service.invoke(
                messages=[{"role": "user", "content": prompt_text}],
                model_config_id=model_config_id,
                system_message="You are a helpful assistant. Respond to user requests directly and concisely.",
                temperature=float(temperature) if temperature is not None else None,
                max_tokens=int(max_tokens) if max_tokens is not None else None,
                timeout=int(timeout) if timeout is not None else None,
            )
            
            if llm_response.error:
                raise ValueError(f"LLM invocation error: {llm_response.error}")
            
            return llm_response.content
        else:
            # Fallback to old AutoGen agent creation (for backward compatibility)
            logger.warning("[InvokeLLM] model_config_id not found in model_set config, falling back to direct agent creation")
            
            # Create fresh agent instance for this invocation to avoid state pollution
            # This ensures each call is completely independent
            logger.info(f"[InvokeLLM] Creating fresh agent instance for this invocation")
            agent = self._create_model_set_agent()
            
            # Generate reply using AutoGen agent
            # Note: AutoGen's generate_reply is synchronous, but we're in async context
            # We need to run it in a thread pool
            import asyncio
            loop = asyncio.get_event_loop()
            
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: agent.generate_reply(
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
        # Log diagnostic information
        logger.info(f"[InvokePrompt] ========== Invoking prompt target ==========")
        logger.info(f"[InvokePrompt] user_input_mapping: {self.user_input_mapping}")
        logger.info(f"[InvokePrompt] variable_mapping: {self.variable_mapping}")
        logger.info(f"[InvokePrompt] input_data keys: {list(input_data.keys()) if isinstance(input_data, dict) else 'not a dict'}")
        logger.debug(f"[InvokePrompt] input_data content (first 500 chars): {json.dumps(input_data, ensure_ascii=False, default=str)[:500]}")
        
        # Get user input value from input_data using user_input_mapping
        # Add it to input_data as "user_input" for use in prompt templates
        # Since input_data only uses 'name' as keys, we need to convert user_input_mapping from 'key' to 'name' if needed
        user_input_set = False
        if self.user_input_mapping:
            user_input_value = None
            matched_key = None
            
            # Get key-to-name mapping from input_data (added by _call_target)
            key_to_name_mapping = input_data.get("_key_to_name_mapping", {})
            logger.info(f"[InvokePrompt] user_input_mapping: '{self.user_input_mapping}'")
            logger.info(f"[InvokePrompt] Key-to-name mapping: {key_to_name_mapping}")
            logger.info(f"[InvokePrompt] Available input_data keys: {list(input_data.keys())}")
            
            # Determine the actual field name to use
            # If user_input_mapping is a key (e.g., "输入"), convert it to name (e.g., "input")
            # If user_input_mapping is already a name, use it directly
            field_name_to_use = None
            
            # First, check if user_input_mapping is in key-to-name mapping (it's a key)
            if key_to_name_mapping and self.user_input_mapping in key_to_name_mapping:
                field_name_to_use = key_to_name_mapping[self.user_input_mapping]
                logger.info(f"[InvokePrompt] ✅ Converted key '{self.user_input_mapping}' to name '{field_name_to_use}' using mapping")
            # Otherwise, assume user_input_mapping is already a name
            elif self.user_input_mapping in input_data:
                field_name_to_use = self.user_input_mapping
                logger.info(f"[InvokePrompt] ✅ user_input_mapping '{self.user_input_mapping}' is already a name, using directly")
            else:
                # user_input_mapping is neither in mapping nor in input_data
                logger.warning(f"[InvokePrompt] ⚠️ user_input_mapping '{self.user_input_mapping}' not found in mapping or input_data")
            
            # Now try to get the value using the determined field name
            if field_name_to_use:
                if field_name_to_use in input_data:
                    user_input_value = input_data[field_name_to_use]
                    matched_key = field_name_to_use
                    # Log detailed information about the value
                    value_type = type(user_input_value).__name__
                    logger.info(f"[InvokePrompt] ✅ Found value using field name '{field_name_to_use}': type={value_type}, value={str(user_input_value)[:200]}...")
                    # If value is a dict, try to extract text field
                    if isinstance(user_input_value, dict):
                        if "text" in user_input_value:
                            user_input_value = user_input_value["text"]
                            logger.info(f"[InvokePrompt] ✅ Extracted 'text' from dict: {str(user_input_value)[:200]}...")
                        else:
                            logger.warning(f"[InvokePrompt] ⚠️ Value is dict but has no 'text' key. Keys: {list(user_input_value.keys())}")
                else:
                    logger.error(f"[InvokePrompt] ❌ Field name '{field_name_to_use}' (converted from '{self.user_input_mapping}') not found in input_data. Available keys: {list(input_data.keys())}")
            
            # Fallback: Try common field names that might correspond to user input
            if user_input_value is None:
                common_input_names = ["input", "user_input", "query", "text", "content", "message"]
                for name_key in common_input_names:
                    if name_key in input_data:
                        user_input_value = input_data[name_key]
                        matched_key = name_key
                        logger.warning(f"[InvokePrompt] ⚠️ Using fallback field '{name_key}' for user_input_mapping '{self.user_input_mapping}'")
                        break
            
            # Set user_input if we found a value
            if user_input_value is not None:
                # Ensure user_input_value is a string
                # Handle different value types
                if isinstance(user_input_value, dict):
                    # If it's a dict, try to extract text
                    if "text" in user_input_value:
                        user_input_value = user_input_value["text"]
                        logger.info(f"[InvokePrompt] ✅ Extracted 'text' from dict value")
                    else:
                        # Convert entire dict to string as fallback
                        user_input_value = json.dumps(user_input_value, ensure_ascii=False)
                        logger.warning(f"[InvokePrompt] ⚠️ Value is dict without 'text', converting to JSON string")
                elif not isinstance(user_input_value, str):
                    # Convert other types to string
                    user_input_value = str(user_input_value)
                    logger.info(f"[InvokePrompt] ✅ Converted value to string (type was {type(user_input_value).__name__})")
                
                input_data["user_input"] = str(user_input_value)
                user_input_set = True
                logger.info(f"[InvokePrompt] ✅ Set user_input (final value type: {type(input_data['user_input']).__name__}, length: {len(input_data['user_input'])}): {input_data['user_input'][:200]}...")
                if matched_key == self.user_input_mapping:
                    logger.info(f"[InvokePrompt] ✅ Set user_input from field '{self.user_input_mapping}'")
                else:
                    logger.info(f"[InvokePrompt] ✅ Set user_input from field '{matched_key}' (mapped from '{self.user_input_mapping}')")
            else:
                logger.error(f"[InvokePrompt] ❌ Field '{self.user_input_mapping}' not found in input_data. Available keys: {list(input_data.keys())}")
                logger.error(f"[InvokePrompt] ❌ Key-to-name mapping: {key_to_name_mapping}")
                logger.error(f"[InvokePrompt] ❌ This suggests that _call_target did not properly extract fields from data_content or the mapping is incorrect.")
        else:
            logger.warning(f"[InvokePrompt] ⚠️ user_input_mapping is not set")
        
        # Build messages from prompt configuration
        messages = []
        
        for msg_idx, msg_template in enumerate(self.prompt_messages):
            role = msg_template.get("role", "user")
            content_template = msg_template.get("content", "")
            
            # Extract text content
            if isinstance(content_template, dict):
                content_text = content_template.get("text", "")
            else:
                content_text = str(content_template)
            
            original_content = content_text  # Keep original for logging
            
            # Replace variables in content
            # Support both {variable} and {{variable}} formats
            # First, replace prompt variables (from variable_mapping or prompt default values)
            for var_name in self.prompt_variables.keys():
                # Determine the value to use for this variable
                value_str = None
                
                # Priority 1: Use variable_mapping if exists (map to dataset field)
                if self.variable_mapping and var_name in self.variable_mapping:
                    field_name = self.variable_mapping[var_name]
                    if field_name and field_name in input_data:
                        value = input_data[field_name]
                        value_str = str(value) if value is not None else ""
                        logger.debug(f"[InvokePrompt] Message[{msg_idx}] Variable '{var_name}' mapped to field '{field_name}': {value_str[:100]}...")
                    else:
                        logger.warning(f"[InvokePrompt] Message[{msg_idx}] Variable '{var_name}' mapped to field '{field_name}' but field not found in input_data")
                
                # Priority 2: Use prompt's default variable value (from prompt management)
                if value_str is None:
                    var_value = self.prompt_variables.get(var_name)
                    if var_value is not None:
                        value_str = str(var_value)
                        logger.debug(f"[InvokePrompt] Message[{msg_idx}] Variable '{var_name}' using default value: {value_str[:100]}...")
                
                # Replace placeholders if we have a value
                if value_str is not None:
                    placeholder_single = "{" + var_name + "}"
                    placeholder_double = "{{" + var_name + "}}"
                    # Replace double braces first, then single braces
                    content_text = content_text.replace(placeholder_double, value_str)
                    content_text = content_text.replace(placeholder_single, value_str)
            
            # Handle user input: user input is a default parameter, should be directly used as message content
            # For user role messages, append user input to the message content
            # User input is NOT a placeholder variable - it's a default parameter that should always be included
            if role == "user" and "user_input" in input_data:
                user_input_value = input_data["user_input"]
                if user_input_value:
                    # If message content is empty, use user input directly
                    if not content_text.strip():
                        content_text = str(user_input_value)
                        logger.warning(f"[InvokePrompt] Message[{msg_idx}] User message was empty, using user_input directly as content: {str(user_input_value)[:200]}...")
                    else:
                        # Otherwise, append user input to the message content
                        # Format: original_content + "\n" + user_input
                        content_text = content_text.strip() + "\n" + str(user_input_value)
                        logger.warning(f"[InvokePrompt] Message[{msg_idx}] Appended user_input to message content. Original: {original_content[:100]}..., User input: {str(user_input_value)[:200]}...")
                else:
                    logger.error(f"[InvokePrompt] Message[{msg_idx}] ⚠️ user_input exists in input_data but value is empty or None")
            elif role == "user" and "user_input" not in input_data:
                logger.error(f"[InvokePrompt] Message[{msg_idx}] ⚠️ user_input not found in input_data for user message. Available keys: {list(input_data.keys())}")
            
            # Check for any remaining unmatched placeholders
            remaining_placeholders = re.findall(r'\{\{?(\w+)\}?\}', content_text)
            if remaining_placeholders:
                logger.debug(f"[InvokePrompt] Message[{msg_idx}] Remaining placeholders after replacement: {remaining_placeholders}")
            
            logger.debug(f"[InvokePrompt] Message[{msg_idx}] Original: {original_content[:200]}...")
            logger.debug(f"[InvokePrompt] Message[{msg_idx}] Final: {content_text[:200]}...")
            
            messages.append({"role": role, "content": content_text})
        
        # Use LLMService for unified LLM invocation
        if not hasattr(self, 'prompt_model_config_id') or not self.prompt_model_config_id:
            raise ValueError("Prompt model_config_id not found. Prompt must have a valid model_config_id.")
        
        logger.info(f"[InvokePrompt] Using LLMService with model_config_id={self.prompt_model_config_id}")
        from app.services.llm_service import LLMService
        
        llm_service = LLMService(self.db)
        
        # Extract system message from messages
        system_message = None
        user_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                user_messages.append(msg)
        
        # If no system message found, use default
        if not system_message:
            system_message = "You are a helpful assistant."
        
        # Get temperature and max_tokens from prompt model_config (may override model_config defaults)
        temperature = self.prompt_model_config.get("temperature")
        max_tokens = self.prompt_model_config.get("max_tokens")
        
        # Use user_messages if available, otherwise use all messages
        messages_to_send = user_messages if user_messages else messages
        
        try:
            llm_response = await llm_service.invoke(
                messages=messages_to_send,
                model_config_id=self.prompt_model_config_id,
                system_message=system_message,
                temperature=float(temperature) if temperature is not None else None,
                max_tokens=int(max_tokens) if max_tokens is not None else None,
            )
            
            if llm_response.error:
                raise ValueError(f"LLM invocation error: {llm_response.error}")
            
            return llm_response.content
            
        except ValueError as e:
            # Re-raise ValueError (already formatted)
            raise
        except Exception as e:
            # Wrap other exceptions
            error_msg = str(e)
            error_type = type(e).__name__
            raise ValueError(f"LLM invocation error: {error_msg} (type: {error_type})")
    
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

