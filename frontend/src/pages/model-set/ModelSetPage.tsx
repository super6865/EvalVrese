import { useState, useEffect, useMemo } from 'react'
import { Button, Space, Modal, Form, Input, Select, message, Popconfirm, Tag, Card, Descriptions } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, BugOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { PrimaryPage, TableWithPagination, TableHeader } from '../../components/common'
import { ConfigurableForm, FormFieldConfig } from '../../components/form'
import { modelSetService, ModelSet, ModelSetType, DebugResponse } from '../../services/modelSetService'
import { usePagination } from '../../hooks/usePagination'
import { useModal } from '../../hooks/useModal'
import { MODEL_TYPES } from '../../constants'
import { formatTimestamp } from '../../utils/dateUtils'
import type { ColumnsType } from 'antd/es/table'

const { TextArea } = Input
const { Option } = Select

const MODEL_SET_TYPES: { label: string; value: ModelSetType }[] = [
  { label: '智能体API', value: 'agent_api' },
  { label: 'LLM模型', value: 'llm_model' },
]

export default function ModelSetPage() {
  const [modelSets, setModelSets] = useState<ModelSet[]>([])
  const [loading, setLoading] = useState(false)
  const { current, pageSize, handlePageChange } = usePagination({
    pageSizeStorageKey: 'model_set_list_page_size'
  })
  const { visible: modalVisible, editingItem: editingModelSet, form, openModal, closeModal } = useModal<ModelSet>()
  const [total, setTotal] = useState(0)
  const [searchText, setSearchText] = useState('')
  const [debugModalVisible, setDebugModalVisible] = useState(false)
  const [debuggingModelSet, setDebuggingModelSet] = useState<ModelSet | null>(null)
  const [debugResult, setDebugResult] = useState<DebugResponse | null>(null)
  const [debugForm] = Form.useForm()

  useEffect(() => {
    loadModelSets()
  }, [current, pageSize, searchText])

  const loadModelSets = async () => {
    setLoading(true)
    try {
      const skip = (current - 1) * pageSize
      const response = await modelSetService.list(skip, pageSize, searchText || undefined)
      // 按更新时间降序排序
      const sortedModelSets = [...(response.modelSets || [])].sort((a, b) => {
        const timeA = new Date(a.updated_at || 0).getTime()
        const timeB = new Date(b.updated_at || 0).getTime()
        return timeB - timeA // 降序
      })
      setModelSets(sortedModelSets)
      setTotal(response.total)
    } catch (error: any) {
      message.error('加载模型集失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    handlePageChange(1, pageSize)
  }

  const handleCreate = () => {
    form.resetFields()
    form.setFieldsValue({ type: 'agent_api' })
    openModal()
  }

  const handleEdit = (modelSet: ModelSet) => {
    // Don't include api_key when editing for security
    const configWithoutApiKey = { ...modelSet.config }
    if (configWithoutApiKey.api_key) {
      delete configWithoutApiKey.api_key
    }
    
    // Convert JSON fields from objects to formatted strings for textarea display
    const formValues: Record<string, any> = {
      name: modelSet.name,
      description: modelSet.description,
      type: modelSet.type,
    }
    
    // Handle agent_api type JSON fields
    if (modelSet.type === 'agent_api') {
      formValues.api_url = configWithoutApiKey.api_url || ''
      formValues.api_method = configWithoutApiKey.api_method || 'POST'
      formValues.api_headers = safeStringifyJSON(configWithoutApiKey.api_headers)
      formValues.api_body_template = safeStringifyJSON(configWithoutApiKey.api_body_template)
      formValues.input_mapping = safeStringifyJSON(configWithoutApiKey.input_mapping)
    } else {
      // For llm_model type, keep other fields as is
      Object.assign(formValues, configWithoutApiKey)
    }
    
    form.setFieldsValue(formValues)
    openModal(modelSet)
  }

  const handleDelete = async (id: number) => {
    try {
      await modelSetService.delete(id)
      message.success('删除成功')
      loadModelSets()
    } catch (error: any) {
      message.error('删除失败: ' + (error.message || '未知错误'))
    }
  }

  const handleDebug = (modelSet: ModelSet) => {
    setDebuggingModelSet(modelSet)
    debugForm.resetFields()
    setDebugResult(null)
    setDebugModalVisible(true)
  }

  const handleDebugSubmit = async () => {
    if (!debuggingModelSet) return
    
    // 清空之前的结果，避免显示上一次的调试结果
    setDebugResult(null)
    
    try {
      const values = await debugForm.validateFields()
      let testData: Record<string, any> = {}
      
      if (debuggingModelSet.type === 'agent_api') {
        testData = values.test_data ? JSON.parse(values.test_data) : {}
      } else {
        // 优先使用 messages，如果 messages 有值则使用 messages，否则使用 prompt
        if (values.messages && values.messages.trim()) {
          testData = { messages: JSON.parse(values.messages) }
        } else if (values.prompt && values.prompt.trim()) {
          testData = { prompt: values.prompt }
        }
      }
      
      const result = await modelSetService.debug(debuggingModelSet.id, testData)
      setDebugResult(result)
      if (result.success) {
        message.success('调试成功')
      } else {
        message.error(result.message || '调试失败')
      }
    } catch (error: any) {
      if (error.errorFields) {
        return
      }
      message.error('调试失败: ' + (error.message || '未知错误'))
    }
  }

  const safeParseJSON = (value: string | undefined, defaultValue: any = {}): any => {
    if (!value || typeof value !== 'string' || value.trim() === '') {
      return defaultValue
    }
    try {
      return JSON.parse(value.trim())
    } catch (e) {
      throw new Error(`无效的 JSON 格式: ${value}`)
    }
  }

  const safeStringifyJSON = (value: any): string => {
    if (value === null || value === undefined) {
      return ''
    }
    if (typeof value === 'string') {
      return value
    }
    try {
      return JSON.stringify(value, null, 2)
    } catch (e) {
      return ''
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const type = values.type
      
      let config: Record<string, any> = {}
      
      if (type === 'agent_api') {
        config = {
          api_url: values.api_url,
          api_method: values.api_method || 'POST',
          api_headers: safeParseJSON(values.api_headers, {}),
          api_body_template: safeParseJSON(values.api_body_template, {}),
          input_mapping: safeParseJSON(values.input_mapping, {}),
        }
      } else if (type === 'llm_model') {
        config = {
          model_type: values.model_type,
          model_version: values.model_version,
          api_base: values.api_base || undefined,
          temperature: values.temperature !== undefined && values.temperature !== null ? Number(values.temperature) : undefined,
          max_tokens: values.max_tokens !== undefined && values.max_tokens !== null ? Number(values.max_tokens) : undefined,
          timeout: values.timeout ? Number(values.timeout) : 60,
        }
        // Only include api_key if it's provided (for updates, if empty, keep existing value)
        if (values.api_key && values.api_key.trim()) {
          config.api_key = values.api_key
        }
        // Remove undefined values
        Object.keys(config).forEach(key => {
          if (config[key] === undefined) {
            delete config[key]
          }
        })
      }
      
      if (editingModelSet) {
        await modelSetService.update(editingModelSet.id, {
          name: values.name,
          description: values.description,
          type: type,
          config: config,
        })
        message.success('更新成功')
      } else {
        await modelSetService.create({
          name: values.name,
          description: values.description,
          type: type,
          config: config,
        })
        message.success('创建成功')
      }
      
      closeModal()
      loadModelSets()
    } catch (error: any) {
      if (error.errorFields) {
        return
      }
      // Check if it's a validation error from our JSON parsing
      if (error.message && error.message.includes('无效的 JSON 格式')) {
        message.error(error.message)
        return
      }
      // Check if it's an API error with detail message
      const errorMessage = error.response?.data?.detail || error.message || '未知错误'
      message.error('操作失败: ' + errorMessage)
    }
  }

  const getTypeLabel = (type: ModelSetType) => {
    const modelSetType = MODEL_SET_TYPES.find(t => t.value === type)
    return modelSetType?.label || type
  }

  const columns: ColumnsType<ModelSet> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: ModelSetType) => <Tag>{getTypeLabel(type)}</Tag>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      sorter: (a, b) =>
        new Date(a.updated_at || 0).getTime() - new Date(b.updated_at || 0).getTime(),
      render: (text: string) => formatTimestamp(text),
    },
    {
      title: '操作',
      key: 'action',
      width: 350,
      render: (_: any, record: ModelSet) => (
        <Space style={{ gap: '2px' }}>
          <Button
            type="link"
            icon={<BugOutlined />}
            onClick={() => handleDebug(record)}
          >
            调试
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个模型集吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const filters = (
    <Input
      placeholder="搜索模型集名称"
      prefix={<SearchOutlined />}
      value={searchText}
      onChange={(e) => setSearchText(e.target.value)}
      onPressEnter={handleSearch}
      allowClear
      style={{ width: 300 }}
    />
  )

  const actions = (
    <>
      <Button icon={<ReloadOutlined />} onClick={loadModelSets}>
        刷新
      </Button>
      <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
        新增模型集
      </Button>
    </>
  )

  const handleTypeChange = (newType: ModelSetType) => {
    // Clear only config-related fields, keep name and description
    const agentApiFields = ['api_url', 'api_method', 'api_headers', 'api_body_template', 'input_mapping']
    const llmModelFields = ['model_type', 'model_version', 'api_key', 'api_base', 'temperature', 'max_tokens', 'timeout']
    
    const fieldsToClear = newType === 'agent_api' ? llmModelFields : agentApiFields
    const clearValues: Record<string, undefined> = {}
    fieldsToClear.forEach(field => {
      clearValues[field] = undefined
    })
    
    form.setFieldsValue(clearValues)
  }

  const configFields: FormFieldConfig[] = useMemo(() => {
    const baseFields: FormFieldConfig[] = [
      {
        name: 'name',
        label: '名称',
        type: 'input',
        placeholder: '请输入名称',
        required: true,
      },
      {
        name: 'description',
        label: '描述',
        type: 'textarea',
        placeholder: '请输入描述',
        rows: 2,
      },
      {
        name: 'type',
        label: '类型',
        type: 'select',
        placeholder: '请选择类型',
        required: true,
        options: MODEL_SET_TYPES.map(type => ({ label: type.label, value: type.value })),
        render: (form) => (
          <Form.Item
            name="type"
            label="类型"
            rules={[{ required: true, message: '请选择类型' }]}
          >
            <Select placeholder="请选择类型" onChange={(value) => handleTypeChange(value as ModelSetType)}>
              {MODEL_SET_TYPES.map(type => (
                <Option key={type.value} value={type.value}>
                  {type.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
        ),
      },
    ]

    const agentApiFields: FormFieldConfig[] = [
      {
        name: 'api_url',
        label: 'API URL',
        type: 'input',
        placeholder: 'https://api.example.com/endpoint',
        required: true,
        groupCondition: (f) => f.getFieldValue('type') === 'agent_api',
      },
      {
        name: 'api_method',
        label: 'HTTP方法',
        type: 'select',
        initialValue: 'POST',
        options: [
          { label: 'GET', value: 'GET' },
          { label: 'POST', value: 'POST' },
          { label: 'PUT', value: 'PUT' },
          { label: 'PATCH', value: 'PATCH' },
        ],
        groupCondition: (f) => f.getFieldValue('type') === 'agent_api',
      },
      {
        name: 'api_headers',
        label: '请求头 (JSON)',
        type: 'textarea',
        placeholder: '{"Content-Type": "application/json"}',
        tooltip: '格式: {"Content-Type": "application/json", "Authorization": "Bearer token"}',
        rows: 3,
        groupCondition: (f) => f.getFieldValue('type') === 'agent_api',
      },
      {
        name: 'api_body_template',
        label: '请求体模板 (JSON)',
        type: 'textarea',
        placeholder: '{"input": "{input}"}',
        tooltip: '格式: {"input": "{input}", "param": "value"}，可以使用 {variable} 作为占位符',
        rows: 4,
        groupCondition: (f) => f.getFieldValue('type') === 'agent_api',
      },
      {
        name: 'input_mapping',
        label: '入参映射 (JSON)',
        type: 'textarea',
        placeholder: '{"api_input": "test_input"}',
        tooltip: '格式: {"api_param": "test_data_key"}，将测试数据的key映射到API参数',
        rows: 3,
        groupCondition: (f) => f.getFieldValue('type') === 'agent_api',
      },
    ]

    const llmModelFields: FormFieldConfig[] = [
      {
        name: 'model_type',
        label: '模型类型',
        type: 'select',
        placeholder: '请选择模型类型',
        required: true,
        options: MODEL_TYPES.map(type => ({ label: type.label, value: type.value })),
        groupCondition: (f) => f.getFieldValue('type') === 'llm_model',
      },
      {
        name: 'model_version',
        label: '模型版本',
        type: 'input',
        placeholder: '例如: gpt-4, qwen-plus',
        required: true,
        groupCondition: (f) => f.getFieldValue('type') === 'llm_model',
      },
      {
        name: 'api_key',
        label: 'API Key',
        type: 'password',
        placeholder: editingModelSet ? '如需更新请重新输入，留空则保持原值' : '请输入API Key',
        required: !editingModelSet,
        rules: editingModelSet ? [] : [{ required: true, message: '请输入API Key' }],
        groupCondition: (f) => f.getFieldValue('type') === 'llm_model',
      },
      {
        name: 'api_base',
        label: 'API Base URL',
        type: 'input',
        placeholder: '例如: https://api.openai.com/v1',
        groupCondition: (f) => f.getFieldValue('type') === 'llm_model',
      },
      {
        name: 'temperature',
        label: 'Temperature',
        type: 'number',
        placeholder: '0.7',
        min: 0,
        max: 2,
        step: 0.1,
        groupCondition: (f) => f.getFieldValue('type') === 'llm_model',
      },
      {
        name: 'max_tokens',
        label: 'Max Tokens',
        type: 'number',
        placeholder: '例如: 2000',
        min: 1,
        groupCondition: (f) => f.getFieldValue('type') === 'llm_model',
      },
      {
        name: 'timeout',
        label: '超时时间（秒）',
        type: 'number',
        placeholder: '60',
        tooltip: 'API 请求超时时间，默认 60 秒',
        min: 1,
        max: 600,
        groupCondition: (f) => f.getFieldValue('type') === 'llm_model',
      },
    ]

    return [...baseFields, ...agentApiFields, ...llmModelFields]
  }, [editingModelSet])

  const renderDebugFields = () => {
    if (!debuggingModelSet) return null
    
    if (debuggingModelSet.type === 'agent_api') {
      return (
        <Form.Item
          name="test_data"
          label="测试数据 (JSON)"
          rules={[{ required: true, message: '请输入测试数据' }]}
          tooltip='格式: {"key": "value"}'
        >
          <TextArea rows={6} placeholder='{"input": "测试输入"}' />
        </Form.Item>
      )
    } else {
      return (
        <>
          <Form.Item
            name="prompt"
            label="Prompt"
            tooltip="输入测试Prompt，或使用Messages格式"
          >
            <TextArea rows={4} placeholder="输入测试Prompt..." />
          </Form.Item>
          <Form.Item
            name="messages"
            label="Messages (JSON, 可选)"
            tooltip='格式: [{"role": "user", "content": "消息内容"}]'
          >
            <TextArea rows={4} placeholder='[{"role": "user", "content": "消息内容"}]' />
          </Form.Item>
        </>
      )
    }
  }

  return (
    <PrimaryPage
      pageTitle="模型集管理"
      filterSlot={<TableHeader filters={filters} actions={actions} />}
    >
      <TableWithPagination
        columns={columns}
        dataSource={modelSets}
        rowKey="id"
        loading={loading}
        total={total}
        current={current}
        pageSize={pageSize}
        onPageChange={handlePageChange}
        pageSizeStorageKey="model_set_list_page_size"
        heightFull
      />

      <Modal
        title={editingModelSet ? '编辑模型集' : '新增模型集'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={closeModal}
        width={700}
      >
        <ConfigurableForm
          form={form}
          fields={configFields}
        />
      </Modal>

      <Modal
        title={`调试模型集: ${debuggingModelSet?.name}`}
        open={debugModalVisible}
        onOk={handleDebugSubmit}
        onCancel={() => {
          setDebugModalVisible(false)
          debugForm.resetFields()
          setDebugResult(null)
        }}
        width={800}
        okText="执行调试"
        cancelText="关闭"
      >
        <Form
          form={debugForm}
          layout="vertical"
        >
          {renderDebugFields()}
        </Form>

        {debugResult && (
          <Card title="调试结果" style={{ marginTop: '16px' }}>
            <Descriptions column={1} bordered>
              <Descriptions.Item label="状态">
                <Tag color={debugResult.success ? 'green' : 'red'}>
                  {debugResult.success ? '成功' : '失败'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="消息">
                {debugResult.message}
              </Descriptions.Item>
              {debugResult.response && (
                <Descriptions.Item label="响应">
                  <pre style={{ 
                    margin: 0, 
                    maxHeight: '300px', 
                    overflow: 'auto', 
                    background: '#f5f5f5', 
                    padding: '8px', 
                    borderRadius: '4px',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    wordWrap: 'break-word',
                    overflowWrap: 'break-word'
                  }}>
                    {typeof debugResult.response === 'string' 
                      ? debugResult.response 
                      : JSON.stringify(debugResult.response, null, 2)}
                  </pre>
                </Descriptions.Item>
              )}
              {debugResult.status_code && (
                <Descriptions.Item label="HTTP状态码">
                  {debugResult.status_code}
                </Descriptions.Item>
              )}
              {debugResult.input_tokens !== undefined && (
                <Descriptions.Item label="输入Token">
                  {debugResult.input_tokens}
                </Descriptions.Item>
              )}
              {debugResult.output_tokens !== undefined && (
                <Descriptions.Item label="输出Token">
                  {debugResult.output_tokens}
                </Descriptions.Item>
              )}
              {debugResult.model && (
                <Descriptions.Item label="模型">
                  {debugResult.model}
                </Descriptions.Item>
              )}
              {debugResult.error && (
                <Descriptions.Item label="错误">
                  <Tag color="red">{debugResult.error}</Tag>
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        )}
      </Modal>
    </PrimaryPage>
  )
}
