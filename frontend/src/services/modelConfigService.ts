import api from './api'

export interface ModelConfig {
  id: number
  config_name: string
  model_type: string
  model_version: string
  api_key?: string
  api_base?: string
  temperature?: number
  max_tokens?: number
  timeout?: number
  is_enabled: boolean
  created_at?: string
  updated_at?: string
  created_by?: string
}

export interface ModelConfigCreate {
  config_name: string
  model_type: string
  model_version: string
  api_key: string
  api_base?: string
  temperature?: number
  max_tokens?: number
  timeout?: number
  is_enabled?: boolean
  created_by?: string
}

export interface ModelConfigUpdate {
  config_name?: string
  model_type?: string
  model_version?: string
  api_key?: string
  api_base?: string
  temperature?: number
  max_tokens?: number
  timeout?: number
  is_enabled?: boolean
  created_by?: string
}

export const modelConfigService = {
  list: async (includeSensitive: boolean = false, skip: number = 0, limit: number = 20, name?: string): Promise<{ configs: ModelConfig[]; total: number }> => {
    const response = await api.get('/model-configs', {
      params: { include_sensitive: includeSensitive, skip, limit, name },
    })
    return {
      configs: response.data.data || [],
      total: response.data.total || 0,
    }
  },

  getById: async (id: number, includeSensitive: boolean = false): Promise<ModelConfig> => {
    const response = await api.get(`/model-configs/${id}`, {
      params: { include_sensitive: includeSensitive },
    })
    return response.data.data
  },

  create: async (data: ModelConfigCreate): Promise<ModelConfig> => {
    const response = await api.post('/model-configs', data)
    return response.data.data
  },

  update: async (id: number, data: ModelConfigUpdate): Promise<ModelConfig> => {
    const response = await api.put(`/model-configs/${id}`, data)
    return response.data.data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/model-configs/${id}`)
  },

  toggleEnabled: async (id: number, enabled: boolean): Promise<void> => {
    await api.put(`/model-configs/${id}/toggle-enabled`, { enabled })
  },
}

