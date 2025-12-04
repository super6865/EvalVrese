import api from './api'

export const observabilityService = {
  listTraces: async (params?: {
    service_name?: string
    start_time?: string
    end_time?: string
    skip?: number
    limit?: number
  }) => {
    const response = await api.get('/observability/traces', { params })
    return response.data
  },

  getTrace: async (traceId: string) => {
    const response = await api.get(`/observability/traces/${traceId}`)
    return response.data
  },

  listSpans: async (traceId: string) => {
    const response = await api.get(`/observability/traces/${traceId}/spans`)
    return response.data
  },

  getExperimentTraces: async (experimentId: number, runId?: number) => {
    const params = runId ? { run_id: runId } : {}
    const response = await api.get(`/experiments/${experimentId}/traces`, { params })
    return response.data
  },

  getRunTraces: async (experimentId: number, runId: number) => {
    const response = await api.get(`/experiments/${experimentId}/runs/${runId}/traces`)
    return response.data
  },

  getTraceDetail: async (traceId: string) => {
    const response = await api.get(`/observability/traces/${traceId}/detail`)
    return response.data
  },
}

