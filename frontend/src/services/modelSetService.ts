import api from './api'

export type ModelSetType = 'agent_api' | 'llm_model'

export interface ModelSet {
  id: number
  name: string
  description?: string
  type: ModelSetType
  config: Record<string, any>
  created_at?: string
  updated_at?: string
  created_by?: string
}

export interface ModelSetCreate {
  name: string
  description?: string
  type: ModelSetType
  config: Record<string, any>
  created_by?: string
}

export interface ModelSetUpdate {
  name?: string
  description?: string
  type?: ModelSetType
  config?: Record<string, any>
  created_by?: string
}

export interface DebugRequest {
  test_data: Record<string, any>
}

export interface DebugResponse {
  success: boolean
  message: string
  response?: any
  status_code?: number
  input_tokens?: number
  output_tokens?: number
  model?: string
  error?: string
}

export const modelSetService = {
  list: async (skip: number = 0, limit: number = 20, name?: string): Promise<{ modelSets: ModelSet[]; total: number }> => {
    const response = await api.get('/model-sets', {
      params: { skip, limit, name },
    })
    return {
      modelSets: response.data.data || [],
      total: response.data.total || 0,
    }
  },

  getById: async (id: number): Promise<ModelSet> => {
    const response = await api.get(`/model-sets/${id}`)
    return response.data.data
  },

  create: async (data: ModelSetCreate): Promise<ModelSet> => {
    const response = await api.post('/model-sets', data)
    return response.data.data
  },

  update: async (id: number, data: ModelSetUpdate): Promise<ModelSet> => {
    const response = await api.put(`/model-sets/${id}`, data)
    return response.data.data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/model-sets/${id}`)
  },

  debug: async (id: number, testData: Record<string, any>): Promise<DebugResponse> => {
    const response = await api.post(`/model-sets/${id}/debug`, { test_data: testData })
    return response.data
  },
}

