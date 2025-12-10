import api from './api'
import type {
  Prompt,
  PromptBasic,
  PromptVersion,
  PromptCreateRequest,
  PromptUpdateRequest,
  PromptCloneRequest,
} from '../types/prompt'

export type { Prompt, PromptVersion }

export const promptService = {
  list: async (params: {
    page_number?: number
    page_size?: number
    name?: string
    key_word?: string
    order_by?: 'created_at' | 'committed_at'
    asc?: boolean
    created_bys?: string[]
  }) => {
    try {
      const response = await api.get('/prompts', { params })
      if (response.data.success && response.data.data) {
        return response.data.data
      }
      throw new Error(response.data.message || '获取列表失败')
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '获取列表失败'
      throw new Error(errorMessage)
    }
  },

  get: async (id: number): Promise<Prompt> => {
    try {
      const response = await api.get(`/prompts/${id}`)
      if (response.data.success && response.data.data) {
        return response.data.data
      }
      throw new Error(response.data.message || '获取 Prompt 失败')
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '获取 Prompt 失败'
      throw new Error(errorMessage)
    }
  },

  create: async (data: PromptCreateRequest): Promise<{ prompt_id: number }> => {
    try {
      const response = await api.post('/prompts', {
        prompt_key: data.prompt_key,
        prompt_name: data.prompt_name,
        prompt_description: data.prompt_description,
        draft_detail: data.draft_detail,
      })
      if (response.data.success && response.data.data) {
        return response.data.data
      }
      throw new Error(response.data.message || '创建 Prompt 失败')
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '创建 Prompt 失败'
      throw new Error(errorMessage)
    }
  },

  update: async (id: number, data: PromptUpdateRequest): Promise<void> => {
    try {
      const response = await api.put(`/prompts/${id}`, {
        prompt_name: data.prompt_name,
        prompt_description: data.prompt_description,
      })
      if (!response.data.success) {
        throw new Error(response.data.message || '更新 Prompt 失败')
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '更新 Prompt 失败'
      throw new Error(errorMessage)
    }
  },

  delete: async (id: number): Promise<void> => {
    try {
      const response = await api.delete(`/prompts/${id}`)
      if (!response.data.success) {
        throw new Error(response.data.message || '删除 Prompt 失败')
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '删除 Prompt 失败'
      throw new Error(errorMessage)
    }
  },

  clone: async (data: PromptCloneRequest): Promise<{ cloned_prompt_id: number }> => {
    try {
      const response = await api.post('/prompts/clone', {
        prompt_id: data.prompt_id,
        cloned_prompt_key: data.cloned_prompt_key,
        cloned_prompt_name: data.cloned_prompt_name,
        cloned_prompt_description: data.cloned_prompt_description,
        commit_version: data.commit_version,
      })
      if (response.data.success && response.data.data) {
        return response.data.data
      }
      throw new Error(response.data.message || '克隆 Prompt 失败')
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '克隆 Prompt 失败'
      throw new Error(errorMessage)
    }
  },

  listVersions: async (promptId: number): Promise<PromptVersion[]> => {
    try {
      const response = await api.get(`/prompts/${promptId}/versions`)
      if (response.data.success && response.data.data) {
        return response.data.data
      }
      throw new Error(response.data.message || '获取版本列表失败')
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '获取版本列表失败'
      throw new Error(errorMessage)
    }
  },

  getVersion: async (promptId: number, version: string): Promise<PromptVersion> => {
    try {
      const response = await api.get(`/prompts/${promptId}/versions/${version}`)
      if (response.data.success && response.data.data) {
        return response.data.data
      }
      throw new Error(response.data.message || '获取版本详情失败')
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '获取版本详情失败'
      throw new Error(errorMessage)
    }
  },

  // Save draft
  saveDraft: async (id: number, draftDetail: any, baseVersion?: string): Promise<void> => {
    try {
      const response = await api.put(`/prompts/${id}/draft`, {
        detail: draftDetail,
        base_version: baseVersion,
      })
      if (!response.data.success) {
        throw new Error(response.data.message || '保存草稿失败')
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '保存草稿失败'
      throw new Error(errorMessage)
    }
  },

  // Submit new version
  submitVersion: async (id: number, version: string, description?: string): Promise<void> => {
    try {
      const response = await api.post(`/prompts/${id}/versions`, {
        version,
        description,
      })
      if (!response.data.success) {
        throw new Error(response.data.message || '提交版本失败')
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '提交版本失败'
      throw new Error(errorMessage)
    }
  },

  // Debug/Execute prompt
  debug: async (params: {
    prompt_id: number
    messages?: Array<{ role: string; content: string }>
    variables?: Record<string, any>
    model_config?: any
  }): Promise<{
    content?: string
    error?: string
    usage?: {
      input_tokens?: number
      output_tokens?: number
    }
    time_consuming_ms?: number
  }> => {
    try {
      // Ensure model_config is not empty
      const requestBody = {
        messages: params.messages,
        variables: params.variables,
        model_config: params.model_config || {},
      }
      
      console.log('[promptService.debug] Request body:', {
        prompt_id: params.prompt_id,
        model_config: requestBody.model_config,
        model_config_id: requestBody.model_config?.model_config_id,
        model_config_keys: Object.keys(requestBody.model_config || {}),
      })
      
      const response = await api.post(`/prompts/${params.prompt_id}/debug`, requestBody)
      if (response.data.success && response.data.data) {
        return response.data.data
      }
      // Even if success is false, return the data which may contain error info
      if (response.data.data) {
        return response.data.data
      }
      throw new Error(response.data.message || '调试执行失败')
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '调试执行失败'
      return {
        error: errorMessage,
      }
    }
  },

  // Get execution history
  getExecutionHistory: async (promptId: number, limit: number = 20): Promise<any[]> => {
    try {
      const response = await api.get(`/prompts/${promptId}/executions`, {
        params: { limit },
      })
      if (response.data.success && response.data.data) {
        return response.data.data
      }
      throw new Error(response.data.message || '获取执行历史失败')
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || '获取执行历史失败'
      throw new Error(errorMessage)
    }
  },

  // Get prompt variables
  getVariables: async (promptId: number, version?: string | null): Promise<string[]> => {
    try {
      const params: any = {}
      if (version && version !== 'draft') {
        params.version = version
      }
      const response = await api.get(`/prompts/${promptId}/variables`, { params })
      if (response.data.success && response.data.data?.variables) {
        return response.data.data.variables
      }
      return []
    } catch (error: any) {
      console.error('获取Prompt变量失败', error)
      return []
    }
  },
}
