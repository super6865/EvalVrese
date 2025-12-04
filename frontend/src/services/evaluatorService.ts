import api from './api'
import type {
  Evaluator,
  EvaluatorVersion,
  EvaluatorType,
  EvaluatorBoxType,
  EvaluatorVersionStatus,
  EvaluatorInputData,
  EvaluatorOutputData,
  PromptEvaluatorContent,
  CodeEvaluatorContent,
  ArgsSchema,
} from '../types/evaluator'

export type { Evaluator, EvaluatorVersion }

export const evaluatorService = {
  list: async (skip = 0, limit = 100, name?: string) => {
    const params: any = { skip, limit }
    if (name) {
      params.name = name
    }
    const response = await api.get('/evaluators', { params })
    return response.data
  },

  get: async (id: number): Promise<Evaluator> => {
    const response = await api.get(`/evaluators/${id}`)
    return response.data
  },

  create: async (data: {
    name: string
    evaluator_type: EvaluatorType
    description?: string
    builtin?: boolean
    box_type?: EvaluatorBoxType
    evaluator_info?: any
    tags?: any
    current_version?: {
      version?: string
      evaluator_content: {
        prompt_evaluator?: PromptEvaluatorContent
        code_evaluator?: CodeEvaluatorContent
      }
      input_schemas?: ArgsSchema[]
      output_schemas?: ArgsSchema[]
      description?: string
    }
  }): Promise<Evaluator> => {
    const response = await api.post('/evaluators', data)
    return response.data
  },

  update: async (id: number, data: {
    name?: string
    description?: string
    box_type?: EvaluatorBoxType
    evaluator_info?: any
    tags?: any
  }): Promise<Evaluator> => {
    const response = await api.put(`/evaluators/${id}`, data)
    return response.data
  },

  delete: async (id: number) => {
    const response = await api.delete(`/evaluators/${id}`)
    return response.data
  },

  listVersions: async (evaluatorId: number) => {
    const response = await api.get(`/evaluators/${evaluatorId}/versions`)
    return response.data
  },

  getVersion: async (versionId: number): Promise<EvaluatorVersion> => {
    const response = await api.get(`/evaluators/versions/${versionId}`)
    return response.data
  },

  createVersion: async (evaluatorId: number, data: {
    version: string
    content?: Record<string, any>
    prompt_content?: PromptEvaluatorContent
    code_content?: CodeEvaluatorContent
    input_schemas?: ArgsSchema[]
    output_schemas?: ArgsSchema[]
    description?: string
    status?: EvaluatorVersionStatus
  }): Promise<EvaluatorVersion> => {
    const response = await api.post(`/evaluators/${evaluatorId}/versions`, data)
    return response.data
  },

  submitVersion: async (versionId: number, description?: string): Promise<EvaluatorVersion> => {
    const response = await api.post(`/evaluators/versions/${versionId}/submit`, null, {
      params: { description },
    })
    return response.data
  },

  run: async (versionId: number, data: {
    input_data: EvaluatorInputData
    experiment_id?: number
    experiment_run_id?: number
    dataset_item_id?: number
    turn_id?: number
    disable_tracing?: boolean
  }): Promise<{ record_id: number; output_data: EvaluatorOutputData }> => {
    const response = await api.post(`/evaluators/versions/${versionId}/run`, data)
    return response.data
  },

  debug: async (versionId: number, data: {
    input_data: EvaluatorInputData
  }): Promise<EvaluatorOutputData> => {
    const response = await api.post(`/evaluators/versions/${versionId}/debug`, data)
    return response.data
  },

  batchDebug: async (data: {
    evaluator_type: EvaluatorType
    evaluator_content: {
      code_evaluator?: CodeEvaluatorContent
      prompt_evaluator?: PromptEvaluatorContent
    }
    input_data: EvaluatorInputData[]
    workspace_id?: string
  }): Promise<{ evaluator_output_data?: EvaluatorOutputData[] }> => {
    const response = await api.post('/evaluators/batch_debug', data)
    return response.data
  },
}

