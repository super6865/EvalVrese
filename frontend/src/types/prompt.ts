/**
 * Prompt type definitions
 */

export interface PromptBasic {
  id: number
  prompt_key: string
  display_name: string
  description?: string
  latest_version?: string
  created_at?: string
  updated_at?: string
  latest_committed_at?: string
  created_by?: string
}

export interface PromptDraft {
  draft_info?: {
    is_modified?: boolean
    updated_at?: string
    base_version?: string
  }
  detail?: any
}

export interface PromptCommit {
  commit_info?: {
    version?: string
    committed_at?: string
  }
  detail?: any
}

export interface Prompt {
  id: number
  prompt_key: string
  prompt_basic: PromptBasic
  prompt_draft?: PromptDraft
  prompt_commit?: PromptCommit
  user?: {
    user_id?: string
    nick_name?: string
    avatar_url?: string
  }
}

export interface PromptVersion {
  id: number
  prompt_id: number
  version: string
  description?: string
  content?: string
  created_at?: string
  updated_at?: string
  created_by?: string
}

export interface PromptCreateRequest {
  prompt_key: string
  prompt_name: string
  prompt_description?: string
  draft_detail?: any
}

export interface PromptUpdateRequest {
  prompt_name?: string
  prompt_description?: string
}

export interface PromptCloneRequest {
  prompt_id: number
  cloned_prompt_key: string
  cloned_prompt_name: string
  cloned_prompt_description?: string
  commit_version?: string
}

