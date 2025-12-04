import { useState, useEffect } from 'react'
import { Button, Table, Modal, Form, Input, message, Space, Tag, Descriptions, Card } from 'antd'
import { PlusOutlined, EyeOutlined } from '@ant-design/icons'
import { datasetService, DatasetVersion } from '../../../services/datasetService'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

interface VersionManagementProps {
  datasetId: number
  onVersionChange?: (version: DatasetVersion | null) => void
  onVersionCreated?: () => void
}

export default function VersionManagement({ datasetId, onVersionChange, onVersionCreated }: VersionManagementProps) {
  const [versions, setVersions] = useState<DatasetVersion[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<DatasetVersion | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadVersions()
  }, [datasetId])

  const loadVersions = async () => {
    setLoading(true)
    try {
      const response = await datasetService.listVersions(datasetId, {
        page_number: 1,
        page_size: 100,
        order_by: 'version_num',
        order_asc: false,
      })
      setVersions(response.versions || [])
    } catch (error: any) {
      message.error('加载版本失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    form.resetFields()
    setModalVisible(true)
  }

  const handleCreateVersion = async (values: any) => {
    try {
      await datasetService.createVersion(datasetId, {
        version: values.version,
        description: values.description,
      })
      message.success('创建版本成功')
      setModalVisible(false)
      await loadVersions()
      // Notify parent component
      onVersionCreated?.()
      // Auto-select the newly created version
      if (versions.length === 0) {
        const response = await datasetService.listVersions(datasetId, {
          page_number: 1,
          page_size: 1,
          order_by: 'version_num',
          order_asc: false,
        })
        if (response.versions && response.versions.length > 0) {
          onVersionChange?.(response.versions[0])
        }
      }
    } catch (error: any) {
      message.error('创建版本失败: ' + (error.message || '未知错误'))
    }
  }

  const handleViewDetail = (version: DatasetVersion) => {
    setSelectedVersion(version)
    setDetailModalVisible(true)
  }

  const handleSelectVersion = (version: DatasetVersion) => {
    onVersionChange?.(version)
  }

  const columns: ColumnsType<DatasetVersion> = [
    {
      title: '版本号',
      dataIndex: 'version',
      key: 'version',
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '版本序号',
      dataIndex: 'version_num',
      key: 'version_num',
      width: 100,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '数据项数量',
      dataIndex: 'item_count',
      key: 'item_count',
      width: 120,
      render: (count: number) => count || 0,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const color = status === 'active' ? 'green' : 'default'
        return <Tag color={color}>{status}</Tag>
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: DatasetVersion) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => handleSelectVersion(record)}
          >
            选择
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold">版本管理</h3>
          {versions.length === 0 && (
            <p className="text-sm text-gray-500 mt-1">
              数据集创建后需要先创建版本，然后才能添加数据项
            </p>
          )}
        </div>
        <Button
          type="primary"
          size="large"
          icon={<PlusOutlined />}
          onClick={handleCreate}
        >
          创建版本
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={versions}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title="创建版本"
        open={modalVisible}
        onOk={() => form.submit()}
        onCancel={() => setModalVisible(false)}
        okText="创建"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateVersion}
        >
          <Form.Item
            name="version"
            label="版本号"
            rules={[{ required: true, message: '请输入版本号' }]}
            tooltip="留空将自动生成版本号"
          >
            <Input placeholder="例如: v1.0.0 (留空自动生成)" />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea
              rows={3}
              placeholder="版本描述（可选）"
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="版本详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {selectedVersion && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="版本号">{selectedVersion.version}</Descriptions.Item>
            <Descriptions.Item label="版本序号">{selectedVersion.version_num}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={selectedVersion.status === 'active' ? 'green' : 'default'}>
                {selectedVersion.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="数据项数量">{selectedVersion.item_count || 0}</Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>
              {selectedVersion.description || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间" span={2}>
              {dayjs(selectedVersion.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            {selectedVersion.evaluation_set_schema && (
              <Descriptions.Item label="Schema 快照" span={2}>
                <pre className="bg-gray-50 p-2 rounded text-xs overflow-auto max-h-60">
                  {JSON.stringify(selectedVersion.evaluation_set_schema, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

