import { useState, useEffect, useMemo } from 'react'
import { Button, Space, Modal, message, Popconfirm, Tag, Switch, Input } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { PrimaryPage, TableWithPagination, TableHeader } from '../../components/common'
import { ConfigurableForm, FormFieldConfig } from '../../components/form'
import { modelConfigService, ModelConfig, ModelConfigCreate, ModelConfigUpdate } from '../../services/modelConfigService'
import { usePagination } from '../../hooks/usePagination'
import { useModal } from '../../hooks/useModal'
import { MODEL_TYPES } from '../../constants'
import { formatTimestamp } from '../../utils/dateUtils'
import type { ColumnsType } from 'antd/es/table'

export default function ModelConfigPage() {
  const [configs, setConfigs] = useState<ModelConfig[]>([])
  const [loading, setLoading] = useState(false)
  const { current, pageSize, handlePageChange } = usePagination({
    pageSizeStorageKey: 'model_config_list_page_size'
  })
  const { visible: modalVisible, editingItem: editingConfig, form, openModal, closeModal } = useModal<ModelConfig>()
  const [total, setTotal] = useState(0)
  const [searchText, setSearchText] = useState('')
  const [viewModalVisible, setViewModalVisible] = useState(false)
  const [viewingConfig, setViewingConfig] = useState<ModelConfig | null>(null)

  useEffect(() => {
    loadConfigs()
  }, [current, pageSize, searchText])

  const loadConfigs = async () => {
    setLoading(true)
    try {
      const skip = (current - 1) * pageSize
      const response = await modelConfigService.list(false, skip, pageSize, searchText || undefined)
      // 按更新时间降序排序
      const sortedConfigs = [...(response.configs || [])].sort((a, b) => {
        const timeA = new Date(a.updated_at || 0).getTime()
        const timeB = new Date(b.updated_at || 0).getTime()
        return timeB - timeA // 降序
      })
      setConfigs(sortedConfigs)
      setTotal(response.total)
    } catch (error: any) {
      message.error('加载模型配置失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    handlePageChange(1, pageSize)
  }

  const handleCreate = () => {
    openModal()
  }

  const handleEdit = (config: ModelConfig) => {
    form.setFieldsValue({
      config_name: config.config_name,
      model_type: config.model_type,
      model_version: config.model_version,
      api_base: config.api_base,
      temperature: config.temperature,
      max_tokens: config.max_tokens,
      timeout: config.timeout,
      is_enabled: config.is_enabled,
    })
    openModal(config)
  }

  const handleView = async (config: ModelConfig) => {
    try {
      const fullConfig = await modelConfigService.getById(config.id, true)
      setViewingConfig(fullConfig)
      setViewModalVisible(true)
    } catch (error: any) {
      message.error('获取配置详情失败: ' + (error.message || '未知错误'))
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await modelConfigService.delete(id)
      message.success('删除成功')
      loadConfigs()
    } catch (error: any) {
      message.error('删除失败: ' + (error.message || '未知错误'))
    }
  }

  const handleToggleEnabled = async (config: ModelConfig, enabled: boolean) => {
    try {
      await modelConfigService.toggleEnabled(config.id, enabled)
      message.success(`配置已${enabled ? '启用' : '禁用'}`)
      loadConfigs()
    } catch (error: any) {
      message.error('操作失败: ' + (error.message || '未知错误'))
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      
      if (editingConfig) {
        // Update
        const updateData: ModelConfigUpdate = {
          ...values,
        }
        // Only include api_key if it's provided (not empty)
        if (values.api_key) {
          updateData.api_key = values.api_key
        }
        await modelConfigService.update(editingConfig.id, updateData)
        message.success('更新成功')
      } else {
        // Create
        const createData: ModelConfigCreate = {
          ...values,
          api_key: values.api_key,
        }
        await modelConfigService.create(createData)
        message.success('创建成功')
      }
      
      closeModal()
      loadConfigs()
    } catch (error: any) {
      if (error.errorFields) {
        // Form validation errors
        return
      }
      message.error('操作失败: ' + (error.message || '未知错误'))
    }
  }

  const getModelTypeLabel = (type: string) => {
    const modelType = MODEL_TYPES.find(m => m.value === type)
    return modelType?.label || type
  }

  const formFields: FormFieldConfig[] = useMemo(() => [
    {
      name: 'config_name',
      label: '配置名称',
      type: 'input',
      placeholder: '请输入配置名称',
      required: true,
    },
    {
      name: 'model_type',
      label: '模型类型',
      type: 'select',
      placeholder: '请选择模型类型',
      required: true,
      options: MODEL_TYPES.map(type => ({ label: type.label, value: type.value })),
    },
    {
      name: 'model_version',
      label: '模型版本',
      type: 'input',
      placeholder: '例如: gpt-4, qwen-plus',
      required: true,
    },
    {
      name: 'api_key',
      label: 'API Key',
      type: 'password',
      placeholder: '请输入API Key',
      required: !editingConfig,
      rules: editingConfig ? [] : [{ required: true, message: '请输入API Key' }],
    },
    {
      name: 'api_base',
      label: 'API Base URL',
      type: 'input',
      placeholder: '例如: https://api.openai.com/v1',
    },
    {
      name: 'temperature',
      label: 'Temperature',
      type: 'number',
      placeholder: '0.7',
      min: 0,
      max: 2,
      step: 0.1,
    },
    {
      name: 'max_tokens',
      label: 'Max Tokens',
      type: 'number',
      placeholder: '例如: 2000',
      min: 1,
    },
    {
      name: 'timeout',
      label: '超时时间（秒）',
      type: 'number',
      placeholder: '60',
      tooltip: 'API 请求超时时间，默认 60 秒',
      min: 1,
      max: 600,
    },
    {
      name: 'is_enabled',
      label: '启用状态',
      type: 'switch',
      valuePropName: 'checked',
    },
  ], [editingConfig])

  const columns: ColumnsType<ModelConfig> = [
    {
      title: '配置名称',
      dataIndex: 'config_name',
      key: 'config_name',
    },
    {
      title: '模型类型',
      dataIndex: 'model_type',
      key: 'model_type',
      render: (type: string) => <Tag>{getModelTypeLabel(type)}</Tag>,
    },
    {
      title: '模型版本',
      dataIndex: 'model_version',
      key: 'model_version',
    },
    {
      title: '启用状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      render: (enabled: boolean, record: ModelConfig) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleToggleEnabled(record, checked)}
        />
      ),
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
      render: (_: any, record: ModelConfig) => (
        <Space style={{ gap: '2px' }}>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
          >
            查看
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个配置吗？"
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
      placeholder="搜索配置名称"
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
      <Button icon={<ReloadOutlined />} onClick={loadConfigs}>
        刷新
      </Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          创建配置
        </Button>
    </>
  )

  return (
    <PrimaryPage
      pageTitle="模型配置管理"
      filterSlot={<TableHeader filters={filters} actions={actions} />}
    >
      <TableWithPagination
        columns={columns}
        dataSource={configs}
        rowKey="id"
        loading={loading}
        total={total}
        current={current}
        pageSize={pageSize}
        onPageChange={handlePageChange}
        pageSizeStorageKey="model_config_list_page_size"
        heightFull
      />

      <Modal
        title={editingConfig ? '编辑模型配置' : '创建模型配置'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={closeModal}
        width={600}
      >
        <ConfigurableForm form={form} fields={formFields} />
      </Modal>

      <Modal
        title="配置详情"
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {viewingConfig && (
          <div>
            <div style={{ marginBottom: '16px' }}>
              <strong>配置名称：</strong>
              <span>{viewingConfig.config_name}</span>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <strong>模型类型：</strong>
              <Tag>{getModelTypeLabel(viewingConfig.model_type)}</Tag>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <strong>模型版本：</strong>
              <span>{viewingConfig.model_version}</span>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <strong>API Key：</strong>
              <span style={{ fontFamily: 'monospace', background: '#f5f5f5', padding: '2px 6px', borderRadius: '4px' }}>
                {viewingConfig.api_key?.substring(0, 20)}...
              </span>
            </div>
            {viewingConfig.api_base && (
              <div style={{ marginBottom: '16px' }}>
                <strong>API Base URL：</strong>
                <span>{viewingConfig.api_base}</span>
              </div>
            )}
            {viewingConfig.temperature !== undefined && viewingConfig.temperature !== null && (
              <div style={{ marginBottom: '16px' }}>
                <strong>Temperature：</strong>
                <span>{viewingConfig.temperature}</span>
              </div>
            )}
            {viewingConfig.max_tokens && (
              <div style={{ marginBottom: '16px' }}>
                <strong>Max Tokens：</strong>
                <span>{viewingConfig.max_tokens}</span>
              </div>
            )}
            <div style={{ marginBottom: '16px' }}>
              <strong>超时时间（秒）：</strong>
              <span>{viewingConfig.timeout || 60}</span>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <strong>启用状态：</strong>
              <Tag color={viewingConfig.is_enabled ? 'green' : 'default'}>
                {viewingConfig.is_enabled ? '启用' : '禁用'}
              </Tag>
            </div>
            {viewingConfig.created_at && (
              <div style={{ marginBottom: '16px' }}>
                <strong>创建时间：</strong>
                <span>{new Date(viewingConfig.created_at).toLocaleString('zh-CN')}</span>
              </div>
            )}
            {viewingConfig.updated_at && (
              <div style={{ marginBottom: '16px' }}>
                <strong>更新时间：</strong>
                <span>{new Date(viewingConfig.updated_at).toLocaleString('zh-CN')}</span>
              </div>
            )}
          </div>
        )}
      </Modal>
    </PrimaryPage>
  )
}

