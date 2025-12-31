import api from './api'

export interface ExperimentGroup {
  id: number
  name: string
  parent_id?: number
  description?: string
  created_at?: string
  updated_at?: string
  children?: ExperimentGroup[]
}

export const experimentGroupService = {
  list: async () => {
    const response = await api.get('/experiment-groups')
    return response.data
  },

  getTree: async () => {
    const response = await api.get('/experiment-groups/tree')
    return response.data
  },

  get: async (id: number) => {
    const response = await api.get(`/experiment-groups/${id}`)
    return response.data
  },

  create: async (data: {
    name: string
    parent_id?: number
    description?: string
  }) => {
    const response = await api.post('/experiment-groups', data)
    return response.data
  },

  update: async (id: number, data: {
    name?: string
    parent_id?: number
    description?: string
  }) => {
    const response = await api.put(`/experiment-groups/${id}`, data)
    return response.data
  },

  delete: async (id: number) => {
    const response = await api.delete(`/experiment-groups/${id}`)
    return response.data
  },
}

