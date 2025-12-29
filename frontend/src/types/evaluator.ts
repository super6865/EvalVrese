/**
 * Evaluator type definitions
 */

export type EvaluatorType = 'prompt' | 'code'
export type EvaluatorBoxType = 'white' | 'black'
export type EvaluatorVersionStatus = 'draft' | 'submitted' | 'archived'
export type EvaluatorRunStatus = 'unknown' | 'success' | 'fail'
export type ContentType = 'Text' | 'Image' | 'Audio' | 'MultiPart'
export type ParseType = 'json' | 'text'
export type LanguageType = 'Python' | 'JS'
export type Role = 'system' | 'user' | 'assistant' | 'tool'

export interface EvaluatorInfo {
  benchmark?: string
  vendor?: string
  vendor_url?: string
  user_manual_url?: string
}

export interface EvaluatorTags {
  'zh-CN'?: Record<string, string[]>
  'en-US'?: Record<string, string[]>
}

export interface Evaluator {
  id: number
  name: string
  description?: string
  evaluator_type: EvaluatorType
  latest_version?: string
  builtin?: boolean
  box_type?: EvaluatorBoxType
  evaluator_info?: EvaluatorInfo
  tags?: EvaluatorTags
  // Content fields (directly stored in evaluator)
  prompt_content?: PromptEvaluatorContent
  code_content?: CodeEvaluatorContent
  input_schemas?: ArgsSchema[]
  output_schemas?: ArgsSchema[]
  created_at?: string
  updated_at?: string
  created_by?: string
}

export interface ArgsSchema {
  key?: string
  support_content_types?: ContentType[]
  json_schema?: string
  default_value?: Content
}

export interface Content {
  content_type?: ContentType
  format?: string
  text?: string
  image?: {
    name?: string
    url?: string
    uri?: string
    thumb_url?: string
  }
  audio?: {
    format?: string
    url?: string
  }
  multi_part?: Content[]
}

export interface Message {
  role: Role
  content?: Content
  ext?: Record<string, string>
}

export interface ModelConfig {
  provider?: string
  model: string
  api_key?: string
  api_base?: string
  temperature?: number
  max_tokens?: number
  top_p?: number
  frequency_penalty?: number
  presence_penalty?: number
  timeout?: number
  extra_config?: Record<string, any>
  // New field: model configuration ID from model_configs table
  model_config_id?: number
}

export interface PromptEvaluatorContent {
  message_list: Message[]
  model_config: ModelConfig
  tools?: any[]
  parse_type?: ParseType
  prompt_suffix?: string
  receive_chat_history?: boolean
}

export interface CodeEvaluatorContent {
  code_content: string
  language_type: LanguageType
  code_template_key?: string
  code_template_name?: string
}

export interface EvaluatorVersion {
  id: number
  evaluator_id: number
  version: string
  description?: string
  status: EvaluatorVersionStatus
  input_schemas?: ArgsSchema[]
  output_schemas?: ArgsSchema[]
  prompt_content?: PromptEvaluatorContent
  code_content?: CodeEvaluatorContent
  content?: Record<string, any> // Legacy field
  created_at?: string
  updated_at?: string
  created_by?: string
}

export interface EvaluatorInputData {
  history_messages?: Message[]
  input_fields?: Record<string, Content>
  evaluate_dataset_fields?: Record<string, Content>
  evaluate_target_output_fields?: Record<string, Content>
  ext?: Record<string, string>
}

export interface EvaluatorResult {
  score?: number
  correction?: {
    score?: number
    explain?: string
    updated_by?: string
  }
  reasoning?: string
}

export interface EvaluatorUsage {
  input_tokens?: number
  output_tokens?: number
}

export interface EvaluatorRunError {
  code?: number
  message?: string
}

export interface EvaluatorOutputData {
  evaluator_result?: EvaluatorResult
  evaluator_usage?: EvaluatorUsage
  evaluator_run_error?: EvaluatorRunError
  time_consuming_ms?: number
  stdout?: string
}

export interface EvaluatorRecord {
  id: number
  evaluator_version_id: number
  experiment_id?: number
  experiment_run_id?: number
  dataset_item_id?: number
  turn_id?: number
  input_data: EvaluatorInputData
  output_data: EvaluatorOutputData
  status: EvaluatorRunStatus
  trace_id?: string
  log_id?: string
  ext?: Record<string, string>
  created_at?: string
  created_by?: string
}

