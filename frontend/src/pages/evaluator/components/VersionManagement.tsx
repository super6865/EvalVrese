import { useState, useEffect } from 'react'
import { Card, Button, Space, Tag, message, Modal, Form, Input, Descriptions } from 'antd'
import { PlusOutlined, CheckOutlined } from '@ant-design/icons'
import { evaluatorService } from '../../../services/evaluatorService'
import { modelConfigService, type ModelConfig } from '../../../services/modelConfigService'
import type { EvaluatorVersion, EvaluatorVersionStatus, EvaluatorType } from '../../../types/evaluator'
import dayjs from 'dayjs'

const { TextArea } = Input

interface VersionManagementProps {
  evaluatorId: number
  evaluatorType: EvaluatorType
  onVersionChange?: () => void
}

export default function VersionManagement({ evaluatorId, evaluatorType, onVersionChange }: VersionManagementProps) {
  const [versions, setVersions] = useState<EvaluatorVersion[]>([])
  const [loading, setLoading] = useState(false)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [submitModalVisible, setSubmitModalVisible] = useState(false)
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<EvaluatorVersion | null>(null)
  const [modelConfig, setModelConfig] = useState<ModelConfig | null>(null)
  const [loadingModelConfig, setLoadingModelConfig] = useState(false)
  const [form] = Form.useForm()
  const [createForm] = Form.useForm()

  useEffect(() => {
    loadVersions()
  }, [evaluatorId])

  const loadVersions = async () => {
    setLoading(true)
    try {
      const response = await evaluatorService.listVersions(evaluatorId)
      setVersions(response.versions || [])
    } catch (error) {
      message.error('加载版本失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitVersion = async (versionId: number, description?: string) => {
    try {
      await evaluatorService.submitVersion(versionId, description)
      message.success('版本已提交')
      setSubmitModalVisible(false)
      loadVersions()
      onVersionChange?.()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '提交失败')
    }
  }

  const handleViewDetail = async (version: EvaluatorVersion) => {
    try {
      // Load full version details
      const fullVersion = await evaluatorService.getVersion(version.id)
      setSelectedVersion(fullVersion)
      setDetailModalVisible(true)
      
      // Load model config if model_config_id exists
      if (fullVersion.prompt_content?.model_config?.model_config_id) {
        setLoadingModelConfig(true)
        try {
          const config = await modelConfigService.getById(fullVersion.prompt_content.model_config.model_config_id)
          setModelConfig(config)
        } catch (error: any) {
          setModelConfig(null)
        } finally {
          setLoadingModelConfig(false)
        }
      } else {
        setModelConfig(null)
      }
    } catch (error: any) {
      message.error('加载版本详情失败: ' + (error.response?.data?.detail || '未知错误'))
    }
  }

  const generateNextVersion = (currentVersion: string): string => {
    if (!currentVersion) return 'v1.0'
    
    // Remove 'v' prefix if present
    let versionStr = currentVersion.trim()
    if (versionStr.toLowerCase().startsWith('v')) {
      versionStr = versionStr.substring(1)
    }
    
    // Try to parse version number (e.g., "1.0", "1.1", "2.0")
    const parts = versionStr.split('.')
    if (parts.length >= 2) {
      const major = parseInt(parts[0]) || 1
      const minor = parseInt(parts[1]) || 0
      return `v${major}.${minor + 1}`
    } else if (parts.length === 1) {
      const major = parseInt(parts[0]) || 1
      return `v${major}.1`
    }
    
    // Fallback
    return 'v1.0'
  }

  const handleCreateVersion = async (values: any) => {
    try {
      // Get the latest version to copy content from
      const latestVersion = versions.length > 0 ? versions[0] : null
      
      if (!latestVersion) {
        message.error('没有可复制的版本')
        return
      }

      // Generate version number if not provided
      let versionNumber = values.version?.trim()
      if (!versionNumber) {
        versionNumber = generateNextVersion(latestVersion.version)
      }

      // Copy content from latest version
      const versionData: any = {
        version: versionNumber,
        description: values.description,
        status: 'draft',
      }

      // Copy content based on evaluator type
      if (evaluatorType === 'prompt' && latestVersion.prompt_content) {
        versionData.prompt_content = latestVersion.prompt_content
      } else if (evaluatorType === 'code' && latestVersion.code_content) {
        versionData.code_content = latestVersion.code_content
      }

      // Copy schemas
      if (latestVersion.input_schemas) {
        versionData.input_schemas = latestVersion.input_schemas
      }
      if (latestVersion.output_schemas) {
        versionData.output_schemas = latestVersion.output_schemas
      }

      await evaluatorService.createVersion(evaluatorId, versionData)
      message.success('创建版本成功')
      setCreateModalVisible(false)
      createForm.resetFields()
      await loadVersions()
      onVersionChange?.()
    } catch (error: any) {
      message.error('创建版本失败: ' + (error.response?.data?.detail || '未知错误'))
    }
  }

  const getStatusTag = (status: EvaluatorVersionStatus) => {
    const statusMap = {
      draft: { color: 'orange', text: '草稿' },
      submitted: { color: 'green', text: '已提交' },
      archived: { color: 'default', text: '已归档' },
    }
    const config = statusMap[status] || { color: 'default', text: status }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  return (
    <div style={{ minHeight: 'fit-content' }}>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">版本列表</h3>
        {/* 暂时隐藏创建版本按钮 */}
        {/* <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateModalVisible(true)}
        >
          创建版本
        </Button> */}
      </div>

      <div className="space-y-2">
        {versions.map((version) => (
          <Card 
            key={version.id} 
            size="small" 
            className="mb-2 cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => handleViewDetail(version)}
          >
            <div className="flex items-center justify-between">
              <Space>
                <Tag color="blue">{version.version}</Tag>
                {getStatusTag(version.status)}
                <span>{version.description || '无描述'}</span>
              </Space>
              <Space onClick={(e) => e.stopPropagation()}>
                {version.status === 'draft' && (
                  <Button
                    type="link"
                    size="small"
                    icon={<CheckOutlined />}
                    onClick={() => {
                      setSelectedVersion(version)
                      setSubmitModalVisible(true)
                    }}
                  >
                    提交
                  </Button>
                )}
              </Space>
            </div>
          </Card>
        ))}
      </div>

      <Modal
        title="提交版本"
        open={submitModalVisible}
        onOk={() => {
          form.validateFields().then((values) => {
            if (selectedVersion) {
              handleSubmitVersion(selectedVersion.id, values.description)
            }
          })
        }}
        onCancel={() => {
          setSubmitModalVisible(false)
          setSelectedVersion(null)
          form.resetFields()
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="description" label="提交描述（可选）">
            <TextArea rows={3} placeholder="版本提交描述" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="创建版本"
        open={createModalVisible}
        onOk={() => {
          createForm.validateFields().then((values) => {
            handleCreateVersion(values)
          })
        }}
        onCancel={() => {
          setCreateModalVisible(false)
          createForm.resetFields()
        }}
        okText="创建"
        cancelText="取消"
      >
        <Form form={createForm} layout="vertical">
          <Form.Item
            name="version"
            label="版本号"
            tooltip="留空将自动生成版本号"
          >
            <Input placeholder="例如: v1.1 (留空自动生成)" />
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={3} placeholder="版本描述（可选）" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="版本详情"
        open={detailModalVisible}
        onCancel={() => {
          setDetailModalVisible(false)
          setSelectedVersion(null)
          setModelConfig(null)
        }}
        footer={[
          <Button key="close" onClick={() => {
            setDetailModalVisible(false)
            setSelectedVersion(null)
            setModelConfig(null)
          }}>
            关闭
          </Button>,
        ]}
        width={800}
        bodyStyle={{
          maxHeight: 'calc(100vh - 150px)',
          overflowY: 'auto'
        }}
      >
        {selectedVersion && (
          <div>
            <Descriptions column={2} bordered className="mb-4">
              <Descriptions.Item label="版本号">{selectedVersion.version}</Descriptions.Item>
              <Descriptions.Item label="状态">
                {getStatusTag(selectedVersion.status)}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedVersion.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>
                {selectedVersion.created_at ? dayjs(selectedVersion.created_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
              </Descriptions.Item>
            </Descriptions>

            {evaluatorType === 'prompt' && selectedVersion.prompt_content && (
              <div className="mb-4">
                <h4 className="font-semibold mb-2">Prompt 配置</h4>
                <Card size="small">
                  <Descriptions column={1} bordered size="small">
                    <Descriptions.Item label="模型配置">
                      {loadingModelConfig ? (
                        <span className="text-gray-500">加载中...</span>
                      ) : modelConfig ? (
                        <div>
                          <div className="mb-2">
                            <strong>模型名称：</strong>{modelConfig.config_name}
                          </div>
                          <div className="mb-2">
                            <strong>模型类型：</strong>{modelConfig.model_type}
                          </div>
                          {modelConfig.model_version && (
                            <div className="mb-2">
                              <strong>模型版本：</strong>{modelConfig.model_version}
                            </div>
                          )}
                          <details className="mt-2">
                            <summary className="cursor-pointer text-gray-600 text-xs">查看完整配置</summary>
                            <pre className="bg-gray-50 p-2 rounded text-xs overflow-auto max-h-40 mt-2">
                              {JSON.stringify(selectedVersion.prompt_content.model_config, null, 2)}
                            </pre>
                          </details>
                        </div>
                      ) : selectedVersion.prompt_content.model_config?.model_config_id ? (
                        <span className="text-gray-500">模型配置ID: {selectedVersion.prompt_content.model_config.model_config_id} (无法加载配置信息)</span>
                      ) : (
                        <pre className="bg-gray-50 p-2 rounded text-xs overflow-auto max-h-40">
                          {JSON.stringify(selectedVersion.prompt_content.model_config, null, 2)}
                        </pre>
                      )}
                    </Descriptions.Item>
                    <Descriptions.Item label="消息列表" span={1} style={{ overflow: 'visible' }}>
                      <div style={{ 
                        width: '100%',
                        maxWidth: '700px',
                        overflowX: 'auto',
                        overflowY: 'hidden',
                        WebkitOverflowScrolling: 'touch',
                        border: '1px solid transparent'
                      }}>
                        <pre className="bg-gray-50 p-2 rounded text-xs" style={{ 
                          whiteSpace: 'pre',
                          display: 'block',
                          margin: 0,
                          maxHeight: '240px',
                          overflowY: 'auto',
                          overflowX: 'hidden',
                          minWidth: 'max-content',
                          width: 'max-content'
                        }}>
                          {JSON.stringify(selectedVersion.prompt_content.message_list, null, 2)}
                        </pre>
                      </div>
                    </Descriptions.Item>
                    {selectedVersion.prompt_content.parse_type && (
                      <Descriptions.Item label="解析类型">
                        {selectedVersion.prompt_content.parse_type}
                      </Descriptions.Item>
                    )}
                    {selectedVersion.prompt_content.prompt_suffix && (
                      <Descriptions.Item label="Prompt 后缀">
                        {selectedVersion.prompt_content.prompt_suffix}
                      </Descriptions.Item>
                    )}
                  </Descriptions>
                </Card>
              </div>
            )}

            {evaluatorType === 'code' && selectedVersion.code_content && (
              <div className="mb-4">
                <h4 className="font-semibold mb-2">Code 配置</h4>
                <Card size="small">
                  <Descriptions column={1} bordered size="small">
                    <Descriptions.Item label="编程语言">
                      {selectedVersion.code_content.language_type || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="代码内容">
                      <pre className="bg-gray-50 p-2 rounded text-xs overflow-auto max-h-96">
                        {selectedVersion.code_content.code_content || '-'}
                      </pre>
                    </Descriptions.Item>
                  </Descriptions>
                </Card>
              </div>
            )}

            {selectedVersion.input_schemas && selectedVersion.input_schemas.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold mb-2">输入 Schema</h4>
                <Card size="small">
                  <pre className="bg-gray-50 p-2 rounded text-xs overflow-auto max-h-60">
                    {JSON.stringify(selectedVersion.input_schemas, null, 2)}
                  </pre>
                </Card>
              </div>
            )}

            {selectedVersion.output_schemas && selectedVersion.output_schemas.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold mb-2">输出 Schema</h4>
                <Card size="small">
                  <pre className="bg-gray-50 p-2 rounded text-xs overflow-auto max-h-60">
                    {JSON.stringify(selectedVersion.output_schemas, null, 2)}
                  </pre>
                </Card>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

