import api from './api'

export interface Experiment {
  id: number
  name: string
  description?: string
  dataset_version_id: number
  evaluation_target_config: Record<string, any>
  evaluator_version_ids: number[]
  status: string
  progress: number
  group_id?: number
  created_at?: string
  updated_at?: string
}

export const experimentService = {
  list: async (skip = 0, limit = 100, name?: string, groupId?: number, status?: string[]) => {
    const params: any = { skip, limit }
    if (name) {
      params.name = name
    }
    if (groupId !== undefined) {
      params.group_id = groupId
    }
    if (status && status.length > 0) {
      params.status = status
    }
    const response = await api.get('/experiments', { params })
    return response.data
  },

  get: async (id: number) => {
    const response = await api.get(`/experiments/${id}`)
    return response.data
  },

  delete: async (id: number) => {
    const response = await api.delete(`/experiments/${id}`)
    return response.data
  },

  create: async (data: {
    name: string
    dataset_version_id: number
    evaluation_target_config: Record<string, any>
    evaluator_version_ids: number[]
    description?: string
    group_id?: number
  }) => {
    const response = await api.post('/experiments', data)
    return response.data
  },

  run: async (id: number) => {
    const response = await api.post(`/experiments/${id}/run`)
    return response.data
  },

  stop: async (id: number) => {
    const response = await api.post(`/experiments/${id}/stop`)
    return response.data
  },

  getResults: async (id: number, runId?: number) => {
    const response = await api.get(`/experiments/${id}/results`, { params: { run_id: runId } })
    return response.data
  },

  checkName: async (name: string, excludeId?: number) => {
    const response = await api.post('/experiments/check_name', { name, exclude_id: excludeId })
    return response.data
  },

  batchDelete: async (experimentIds: number[]) => {
    const response = await api.post('/experiments/batch_delete', { experiment_ids: experimentIds })
    return response.data
  },

  clone: async (id: number, name?: string) => {
    const response = await api.post(`/experiments/${id}/clone`, { name })
    return response.data
  },

  retry: async (id: number, retryMode: string = 'retry_all', itemIds?: number[]) => {
    const response = await api.post(`/experiments/${id}/retry`, {
      retry_mode: retryMode,
      item_ids: itemIds,
    })
    return response.data
  },

  getAggregateResults: async (id: number, runId?: number) => {
    const response = await api.get(`/experiments/${id}/aggregate_results`, {
      params: { run_id: runId },
    })
    return response.data
  },

  getStatistics: async (id: number, runId?: number) => {
    const response = await api.get(`/experiments/${id}/statistics`, {
      params: { run_id: runId },
    })
    return response.data
  },

  // Export functions
  createExport: async (id: number, runId?: number) => {
    const response = await api.post(`/experiments/${id}/export`, { run_id: runId })
    return response.data
  },

  listExports: async (id: number, skip = 0, limit = 100) => {
    const response = await api.get(`/experiments/${id}/exports`, {
      params: { skip, limit },
    })
    return response.data
  },

  getExport: async (exportId: number) => {
    const response = await api.get(`/experiments/exports/${exportId}`)
    return response.data
  },

  downloadExport: async (exportId: number, fileName?: string) => {
    const response = await api.get(`/experiments/exports/${exportId}/download`, {
      responseType: 'blob',
    })
    // Get filename from Content-Disposition header or use provided/default
    let downloadFileName = fileName || `export_${exportId}.csv`
    const contentDisposition = response.headers['content-disposition']
    if (contentDisposition) {
      const fileNameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (fileNameMatch && fileNameMatch[1]) {
        downloadFileName = fileNameMatch[1].replace(/['"]/g, '')
      }
    }
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv;charset=utf-8;' }))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', downloadFileName)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  // Comparison functions
  compareExperiments: async (experimentIds: number[], runIds?: Record<number, number>) => {
    const response = await api.post('/experiments/compare', {
      experiment_ids: experimentIds,
      run_ids: runIds,
    })
    return response.data
  },

  getComparisonSummary: async (experimentIds: number[], runIds?: Record<number, number>) => {
    const response = await api.post('/experiments/compare/summary', {
      experiment_ids: experimentIds,
      run_ids: runIds,
    })
    return response.data
  },

  validateComparison: async (experimentIds: number[]) => {
    const response = await api.post('/experiments/validate_comparison', {
      experiment_ids: experimentIds,
    })
    return response.data
  },

  getComparisonDetails: async (experimentIds: number[], runIds?: Record<number, number>) => {
    const response = await api.post('/experiments/compare/details', {
      experiment_ids: experimentIds,
      run_ids: runIds,
    })
    return response.data
  },

  getComparisonMetrics: async (experimentIds: number[], runIds?: Record<number, number>) => {
    const response = await api.post('/experiments/compare/metrics', {
      experiment_ids: experimentIds,
      run_ids: runIds,
    })
    return response.data
  },

  // Runs
  listRuns: async (experimentId: number) => {
    const response = await api.get(`/experiments/${experimentId}/runs`)
    return response.data
  },

  // Experiments with Celery logs
  listWithCeleryLogs: async (skip = 0, limit = 1000) => {
    const response = await api.get('/experiments/with-celery-logs', {
      params: { skip, limit },
    })
    return response.data
  },

  // Celery logs
  getCeleryLogs: async (experimentId: number, runId: number) => {
    const response = await api.get(`/experiments/${experimentId}/runs/${runId}/celery-logs`)
    return response.data
  },
}

