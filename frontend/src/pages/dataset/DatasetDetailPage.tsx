import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button, Card, Descriptions, Tag, message, Space, Spin, Modal, Form, Input, Empty, Alert, Dropdown } from 'antd'
import { ArrowLeftOutlined, ReloadOutlined, EditOutlined, SettingOutlined, DownOutlined } from '@ant-design/icons'
import { datasetService, Dataset, DatasetVersion, FieldSchema } from '../../services/datasetService'
import DatasetItemList from './components/DatasetItemList'
import VersionManagement from './components/VersionManagement'
import SchemaEditor from './components/SchemaEditor'
import AddItemsPanel from './components/AddItemsPanel'
import ImportDatasetModal from './components/ImportDatasetModal'
import { formatTimestamp } from '../../utils/dateUtils'

const { TextArea } = Input

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<DatasetVersion | null>(null)
  const [schemaEditVisible, setSchemaEditVisible] = useState(false)
  const [fieldSchemas, setFieldSchemas] = useState<FieldSchema[]>([])
  const [versions, setVersions] = useState<DatasetVersion[]>([])
  const [addItemsPanelVisible, setAddItemsPanelVisible] = useState(false)
  const [importModalVisible, setImportModalVisible] = useState(false)
  const [versionModalVisible, setVersionModalVisible] = useState(false)
  const [schemaModalVisible, setSchemaModalVisible] = useState(false)
  const [itemListRefreshKey, setItemListRefreshKey] = useState(0)
  const [editForm] = Form.useForm()

  // Validate and convert id to number
  const datasetId = id && !isNaN(Number(id)) ? Number(id) : null

  useEffect(() => {
    if (datasetId) {
      loadDataset()
      loadSchema()
      loadVersions()
    } else if (id) {
      // Invalid id, redirect to list
      message.error('无效的数据集ID')
      navigate('/datasets')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId, id])

  const loadVersions = async () => {
    if (!datasetId) return
    try {
      const response = await datasetService.listVersions(datasetId, {
        page_number: 1,
        page_size: 100,
        order_by: 'version_num',
        order_asc: false,
      })
      const versionList = response.versions || []
      setVersions(versionList)
      // Auto-select the first version if available
      if (versionList.length > 0 && !selectedVersion) {
        setSelectedVersion(versionList[0])
      }
    } catch (error) {
      // Versions might not exist yet
      setVersions([])
    }
  }

  const loadDataset = async () => {
    if (!datasetId) return
    setLoading(true)
    try {
      const data = await datasetService.get(datasetId)
      setDataset(data)
    } catch (error: any) {
      message.error('加载数据集失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const loadSchema = async () => {
    if (!datasetId) return
    try {
      const schema = await datasetService.getSchema(datasetId)
      if (schema?.field_definitions) {
        setFieldSchemas(schema.field_definitions)
      }
    } catch (error) {
      // Schema might not exist
    }
  }

  const handleUpdateSchema = async (schemas: FieldSchema[]) => {
    if (!datasetId) return
    try {
      await datasetService.updateSchema(datasetId, schemas)
      message.success('Schema 更新成功')
      setSchemaEditVisible(false)
      setFieldSchemas(schemas)
      loadDataset()
    } catch (error: any) {
      message.error('Schema 更新失败: ' + (error.message || '未知错误'))
    }
  }

  const handleUpdateDataset = async (values: any) => {
    if (!datasetId) return
    try {
      await datasetService.update(datasetId, {
        name: values.name,
        description: values.description,
      })
      message.success('更新成功')
      loadDataset()
    } catch (error: any) {
      message.error('更新失败: ' + (error.message || '未知错误'))
    }
  }

  // Calculate hasVersion (must be before any early returns)
  const hasVersion = versions.length > 0
  const isDraftVersion = selectedVersion && versions.length > 0


  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'Available':
        return 'green'
      case 'Importing':
      case 'Exporting':
      case 'Indexing':
        return 'blue'
      case 'Deleted':
        return 'red'
      case 'Expired':
        return 'orange'
      default:
        return 'default'
    }
  }

  // Early returns must be after all hooks
  if (loading && !dataset) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  if (!dataset) {
    return <div>数据集不存在</div>
  }

  const handleRefresh = () => {
    loadDataset()
    // 触发列表刷新
    setItemListRefreshKey(prev => prev + 1)
  }

  const handleAddItemsSuccess = () => {
    handleRefresh()
  }

  const addDataMenuItems = [
    {
      key: 'manual',
      label: '手动添加',
      onClick: () => {
        if (!hasVersion) {
          message.warning('请先创建版本')
          return
        }
        setAddItemsPanelVisible(true)
      }
    },
    {
      key: 'import',
      label: '本地导入',
      onClick: () => {
        if (!hasVersion) {
          message.warning('请先创建版本')
          return
        }
        setImportModalVisible(true)
      }
    }
  ]

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto p-6">
      {!hasVersion && (
        <Alert
          message="请先创建版本"
          description="数据集创建后需要先创建版本，然后才能添加数据项。请前往「版本管理」标签页创建第一个版本。"
          type="info"
          showIcon
          className="mb-4"
          action={
            <Button
              type="primary"
              onClick={() => setVersionModalVisible(true)}
            >
              前往创建版本
            </Button>
          }
        />
      )}
      <Card className="mb-4">
        <div className="flex items-center justify-between mb-4">
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/datasets')}>
              返回
            </Button>
            <h2 className="text-xl font-semibold m-0">{dataset.name}</h2>
            <Tag color={getStatusColor(dataset.status)}>{dataset.status || 'Available'}</Tag>
          </Space>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
              刷新
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={() => {
                editForm.setFieldsValue({
                  name: dataset.name,
                  description: dataset.description,
                })
                Modal.confirm({
                  title: '编辑数据集',
                  width: 600,
                  content: (
                    <Form form={editForm} layout="vertical" className="mt-4">
                      <Form.Item
                        name="name"
                        label="名称"
                        rules={[{ required: true, message: '请输入名称' }]}
                      >
                        <Input />
                      </Form.Item>
                      <Form.Item name="description" label="描述">
                        <TextArea rows={4} />
                      </Form.Item>
                    </Form>
                  ),
                  onOk: () => {
                    return editForm.validateFields().then(handleUpdateDataset)
                  },
                })
              }}
            >
              编辑
            </Button>
            {isDraftVersion && (
              <>
                <span className="text-gray-400">|</span>
                <Dropdown
                  menu={{ items: addDataMenuItems }}
                  trigger={['click']}
                >
                  <Button type="primary">
                    添加数据 <DownOutlined />
                  </Button>
                </Dropdown>
              </>
            )}
            <Button onClick={() => setVersionModalVisible(true)}>
              版本管理
            </Button>
            <Button onClick={() => setSchemaModalVisible(true)}>
              Schema 管理
            </Button>
          </Space>
        </div>

        <Descriptions column={3} bordered>
          <Descriptions.Item label="ID">{dataset.id}</Descriptions.Item>
          <Descriptions.Item label="名称">{dataset.name}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={getStatusColor(dataset.status)}>{dataset.status || 'Available'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="描述">{dataset.description || '-'}</Descriptions.Item>
          <Descriptions.Item label="数据项数量">{dataset.item_count || 0}</Descriptions.Item>
          <Descriptions.Item label="最新版本">{dataset.latest_version || '-'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {formatTimestamp(dataset.created_at)}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {formatTimestamp(dataset.updated_at)}
          </Descriptions.Item>
          {dataset.features && (
            <Descriptions.Item label="特性" span={3}>
              <Space>
                {dataset.features.editSchema && <Tag>可编辑 Schema</Tag>}
                {dataset.features.repeatedData && <Tag>支持重复数据</Tag>}
                {dataset.features.multiModal && <Tag>支持多模态</Tag>}
              </Space>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card className="flex-1 overflow-hidden">
        {/* Data Items - Direct display without Tab */}
        {datasetId && hasVersion && (
          <DatasetItemList
            datasetId={datasetId}
            versionId={selectedVersion?.id}
            hasVersion={hasVersion}
            fieldSchemas={fieldSchemas}
            refreshKey={itemListRefreshKey}
          />
        )}
        {datasetId && !hasVersion && (
          <Empty
            description="请先创建版本"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <p className="text-gray-500">数据集创建后需要先创建版本，然后才能查看数据项</p>
          </Empty>
        )}
      </Card>

      {/* Schema Edit Modal */}
      <Modal
        title="编辑 Schema"
        open={schemaEditVisible}
        onCancel={() => setSchemaEditVisible(false)}
        footer={null}
        width={900}
      >
        <SchemaEditor
          value={fieldSchemas}
          onChange={(schemas) => {
            setFieldSchemas(schemas)
          }}
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button onClick={() => setSchemaEditVisible(false)}>取消</Button>
          <Button
            type="primary"
            onClick={() => {
              if (fieldSchemas.length > 0) {
                handleUpdateSchema(fieldSchemas)
              } else {
                message.warning('请至少添加一个字段')
              }
            }}
          >
            保存
          </Button>
        </div>
      </Modal>

      {/* Version Management Modal */}
      <Modal
        title="版本管理"
        open={versionModalVisible}
        onCancel={() => setVersionModalVisible(false)}
        footer={null}
        width={1000}
      >
        {datasetId && (
          <VersionManagement
            datasetId={datasetId}
            onVersionChange={(version) => {
              setSelectedVersion(version)
              loadVersions()
              setVersionModalVisible(false)
            }}
            onVersionCreated={() => {
              loadVersions()
            }}
          />
        )}
      </Modal>

      {/* Schema Management Modal */}
      <Modal
        title="Schema 管理"
        open={schemaModalVisible}
        onCancel={() => setSchemaModalVisible(false)}
        footer={null}
        width={900}
      >
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-semibold mb-1">字段 Schema</h3>
              <p className="text-sm text-gray-500">定义数据集的字段结构</p>
            </div>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => {
                setSchemaEditVisible(true)
              }}
            >
              编辑 Schema
            </Button>
          </div>

          {fieldSchemas.length > 0 ? (
            <div className="space-y-2">
              {fieldSchemas.map((schema, index) => (
                <Card key={index} size="small">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Tag color="blue">{schema.key}</Tag>
                        <span className="font-semibold">{schema.name}</span>
                        {schema.is_required && <Tag color="red">必填</Tag>}
                        {schema.hidden && <Tag>隐藏</Tag>}
                      </div>
                      {schema.description && (
                        <p className="text-sm text-gray-500 mb-1">{schema.description}</p>
                      )}
                      <div className="flex gap-4 text-sm text-gray-600">
                        <span>类型: {schema.content_type}</span>
                        <span>格式: {schema.default_display_format}</span>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              暂无 Schema，请先创建字段定义
            </div>
          )}
        </div>
      </Modal>

      {/* Add Items Panel */}
      <AddItemsPanel
        visible={addItemsPanelVisible}
        dataset={dataset}
        fieldSchemas={fieldSchemas}
        versionId={selectedVersion?.id}
        onClose={() => setAddItemsPanelVisible(false)}
        onSuccess={handleAddItemsSuccess}
      />

      {/* Import Dataset Modal */}
      <ImportDatasetModal
        visible={importModalVisible}
        dataset={dataset}
        fieldSchemas={fieldSchemas}
        versionId={selectedVersion?.id}
        onClose={() => setImportModalVisible(false)}
        onSuccess={handleAddItemsSuccess}
      />
      </div>
    </div>
  )
}
