import api from './api'

// ========== Type Definitions ==========

export interface Dataset {
  id: number
  name: string
  description?: string
  created_at: string
  updated_at: string
  created_by?: string
  status?: string  // Available, Deleted, Expired, Importing, Exporting, Indexing
  item_count?: number
  change_uncommitted?: boolean
  latest_version?: string
  next_version_num?: number
  biz_category?: string
  spec?: {
    max_item_count?: number
    max_field_count?: number
    max_item_size?: number
    max_item_data_nested_depth?: number
    multi_modal_spec?: MultiModalSpec
  }
  features?: {
    editSchema?: boolean
    repeatedData?: boolean
    multiModal?: boolean
  }
}

export interface MultiModalSpec {
  max_file_count?: number
  max_file_size?: number
  supported_formats?: string[]
  max_part_count?: number
}

export interface FieldSchema {
  key: string
  name: string
  description?: string
  content_type?: string  // Text, Image, Audio, MultiPart
  default_display_format?: string  // PlainText, Markdown, JSON, YAML, Code
  status?: string  // Available, Deleted
  text_schema?: string
  multi_model_spec?: MultiModalSpec
  hidden?: boolean
  is_required?: boolean
  default_transformations?: any[]
}

export interface DatasetSchema {
  id: number
  dataset_id: number
  name: string
  description?: string
  field_definitions: FieldSchema[]
  created_at: string
  updated_at: string
}

export interface DatasetVersion {
  id: number
  dataset_id: number
  version: string
  description?: string
  status: string
  schema_id?: number
  version_num?: number
  item_count?: number
  evaluation_set_schema?: {
    id: number
    field_definitions: FieldSchema[]
  }
  created_at: string
  updated_at: string
  created_by?: string
}

export interface Content {
  content_type?: string  // Text, Image, Audio, MultiPart
  format?: string  // PlainText, Markdown, JSON, YAML, Code
  text?: string
  image?: {
    name?: string
    url?: string
    uri?: string
    thumb_url?: string
    storage_provider?: string
  }
  multi_part?: Content[]
  audio?: {
    format?: string
    url?: string
  }
}

export interface FieldData {
  key: string
  name: string
  content?: Content
}

export interface Turn {
  id?: number
  field_data_list: FieldData[]
}

export interface DatasetItem {
  id: number
  dataset_id: number
  version_id?: number
  schema_id?: number
  item_key?: string
  data_content: {
    turns: Turn[]
  }
  created_at: string
  updated_at: string
}

export interface ItemErrorDetail {
  message?: string
  index?: number
  start_index?: number
  end_index?: number
}

export interface ItemErrorGroup {
  type: number
  type_name: string
  summary?: string
  error_count?: number
  details: ItemErrorDetail[]
}

export interface DatasetItemOutput {
  item_index?: number
  item_key?: string
  item_id?: number
  is_new_item?: boolean
}

// ========== Request/Response Types ==========

export interface DatasetCreateRequest {
  name: string
  description?: string
  field_schemas?: FieldSchema[]
  biz_category?: string
  spec?: Dataset['spec']
  features?: Dataset['features']
}

export interface DatasetListRequest {
  name?: string
  creators?: string[]
  dataset_ids?: number[]
  page_number?: number
  page_size?: number
  order_by?: string
  order_asc?: boolean
  include_deleted?: boolean
}

export interface VersionCreateRequest {
  version?: string
  schema_id?: number
  description?: string
}

export interface VersionListRequest {
  version_like?: string
  versions?: string[]
  page_number?: number
  page_size?: number
  order_by?: string
  order_asc?: boolean
}

export interface ItemListRequest {
  version_id?: number
  page_number?: number
  page_size?: number
  item_ids_not_in?: number[]
  order_by?: string
  order_asc?: boolean
}

export interface BatchItemCreateRequest {
  items: Array<{
    data_content: DatasetItem['data_content']
    item_key?: string
  }>
  skip_invalid_items?: boolean
  allow_partial_add?: boolean
}

export interface BatchItemUpdateRequest {
  items: Array<{
    id: number
    data_content?: DatasetItem['data_content']
  }>
  skip_invalid_items?: boolean
}

// ========== Service Methods ==========

export const datasetService = {
  // Dataset CRUD
  list: async (request?: DatasetListRequest) => {
    const response = await api.post('/datasets/list', request || {})
    return response.data
  },

  get: async (id: number, includeDeleted = false) => {
    const response = await api.get(`/datasets/${id}`, {
      params: { include_deleted: includeDeleted }
    })
    return response.data
  },

  create: async (data: DatasetCreateRequest) => {
    const response = await api.post('/datasets', data)
    return response.data
  },

  update: async (id: number, data: { name?: string; description?: string }) => {
    const response = await api.put(`/datasets/${id}`, data)
    return response.data
  },

  delete: async (id: number) => {
    const response = await api.delete(`/datasets/${id}`)
    return response.data
  },

  batchGet: async (datasetIds: number[], includeDeleted = false) => {
    const response = await api.post('/datasets/batch_get', datasetIds, {
      params: { include_deleted: includeDeleted }
    })
    return response.data
  },

  // Schema management
  getSchema: async (datasetId: number) => {
    const response = await api.get(`/datasets/${datasetId}/schema`)
    return response.data
  },

  updateSchema: async (datasetId: number, fieldSchemas: FieldSchema[]) => {
    const response = await api.patch(`/datasets/${datasetId}/schema`, {
      field_schemas: fieldSchemas
    })
    return response.data
  },

  // Version management
  listVersions: async (datasetId: number, request?: VersionListRequest) => {
    const response = await api.post(`/datasets/${datasetId}/versions/list`, request || {})
    return response.data
  },

  getVersion: async (datasetId: number, versionId: number, includeDeleted = false) => {
    const response = await api.get(`/datasets/${datasetId}/versions/${versionId}`, {
      params: { include_deleted: includeDeleted }
    })
    return response.data
  },

  createVersion: async (datasetId: number, data: VersionCreateRequest) => {
    const response = await api.post(`/datasets/${datasetId}/versions`, data)
    return response.data
  },

  batchGetVersions: async (versionIds: number[], includeDeleted = false) => {
    const response = await api.post('/datasets/versions/batch_get', versionIds, {
      params: { include_deleted: includeDeleted }
    })
    return response.data
  },

  // Item management
  listItems: async (datasetId: number, request?: ItemListRequest) => {
    const response = await api.post(`/datasets/${datasetId}/items/list`, request || {})
    return response.data
  },

  getItem: async (itemId: number) => {
    const response = await api.get(`/datasets/items/${itemId}`)
    return response.data
  },

  createItem: async (datasetId: number, versionId: number | null, data: {
    data_content: DatasetItem['data_content']
    item_key?: string
  }) => {
    const params = versionId ? { version_id: versionId } : {}
    const response = await api.post(`/datasets/${datasetId}/items/batch_create`, {
      items: [data],
      skip_invalid_items: false,
      allow_partial_add: false
    }, { params })
    return response.data.items?.[0] || response.data
  },

  batchCreateItems: async (
    datasetId: number,
    versionId: number | null,
    request: BatchItemCreateRequest
  ) => {
    const params = versionId ? { version_id: versionId } : {}
    const response = await api.post(
      `/datasets/${datasetId}/items/batch_create`,
      request,
      { params }
    )
    return response.data
  },

  updateItem: async (
    datasetId: number,
    itemId: number,
    data: {
      data_content?: DatasetItem['data_content']
      turns?: Turn[]
    }
  ) => {
    const response = await api.put(`/datasets/${datasetId}/items/${itemId}`, data)
    return response.data
  },

  batchUpdateItems: async (
    datasetId: number,
    request: BatchItemUpdateRequest
  ) => {
    const response = await api.post(`/datasets/${datasetId}/items/batch_update`, request)
    return response.data
  },

  deleteItem: async (itemId: number) => {
    const response = await api.delete(`/datasets/items/${itemId}`)
    return response.data
  },

  batchDeleteItems: async (datasetId: number, itemIds: number[]) => {
    const response = await api.post(`/datasets/${datasetId}/items/batch_delete`, {
      item_ids: itemIds
    })
    return response.data
  },

  batchGetItems: async (
    datasetId: number,
    itemIds: number[],
    versionId?: number
  ) => {
    const response = await api.post(`/datasets/${datasetId}/items/batch_get`, {
      item_ids: itemIds,
      version_id: versionId
    })
    return response.data
  },

  clearDraftItems: async (datasetId: number) => {
    const response = await api.post(`/datasets/${datasetId}/items/clear`)
    return response.data
  },

  // Import/Export
  uploadFile: async (datasetId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post(`/datasets/${datasetId}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  },

  importDataset: async (
    datasetId: number,
    data: {
      file_path: string
      file_format: string
      field_mappings: Array<{ source: string; target: string }>
      overwrite_dataset?: boolean
      version_id?: number
    }
  ) => {
    const response = await api.post(`/datasets/${datasetId}/import`, data)
    return response.data
  },

  getImportJob: async (jobId: number) => {
    const response = await api.get(`/datasets/io_jobs/${jobId}`)
    return response.data
  },

  listImportJobs: async (datasetId: number) => {
    const response = await api.get(`/datasets/${datasetId}/io_jobs`)
    return response.data
  },
}
