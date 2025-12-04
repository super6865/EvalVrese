import api from './api'
import type {
  EvaluatorRecord,
  EvaluatorRunStatus,
  Correction,
} from '../types/evaluator'

export type { EvaluatorRecord }

export const evaluatorRecordService = {
  get: async (recordId: number): Promise<EvaluatorRecord> => {
    const response = await api.get(`/evaluator-records/${recordId}`)
    return response.data
  },

  list: async (params: {
    evaluator_version_id?: number
    experiment_id?: number
    experiment_run_id?: number
    status?: EvaluatorRunStatus
    skip?: number
    limit?: number
  }) => {
    const response = await api.get('/evaluator-records', { params })
    return response.data
  },

  correct: async (recordId: number, data: {
    score?: number
    explain?: string
  }, updatedBy: string): Promise<EvaluatorRecord> => {
    const response = await api.post(`/evaluator-records/${recordId}/correct`, data, {
      params: { updated_by: updatedBy },
    })
    return response.data
  },
}

