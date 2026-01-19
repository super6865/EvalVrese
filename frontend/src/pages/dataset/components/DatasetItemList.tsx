import { useState, useEffect } from 'react'
import { Button, Table, Space, message, Modal, Tag, Card, Collapse, Checkbox, Empty } from 'antd'
import { EditOutlined, DeleteOutlined, DownloadOutlined } from '@ant-design/icons'
import { datasetService, DatasetItem, FieldSchema, FieldData } from '../../../services/datasetService'
import { formatTimestamp } from '../../../utils/dateUtils'
import type { ColumnsType } from 'antd/es/table'
import ItemEditor from './ItemEditor'
import FieldDataCell from './FieldDataCell'

const { Panel } = Collapse

interface DatasetItemListProps {
  datasetId: number
  versionId?: number | null
  hasVersion?: boolean
  fieldSchemas?: FieldSchema[]
  refreshKey?: number  // 用于触发刷新的 key
}

export default function DatasetItemList({ datasetId, versionId, hasVersion = true, fieldSchemas: propFieldSchemas = [], refreshKey }: DatasetItemListProps) {
  const [items, setItems] = useState<DatasetItem[]>([])
  const [loading, setLoading] = useState(false)
  const [editorVisible, setEditorVisible] = useState(false)
  const [editingItem, setEditingItem] = useState<DatasetItem | null>(null)
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [internalFieldSchemas, setInternalFieldSchemas] = useState<FieldSchema[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [downloading, setDownloading] = useState(false)

  // Use prop fieldSchemas if provided, otherwise load from API
  const fieldSchemas = propFieldSchemas.length > 0 ? propFieldSchemas : internalFieldSchemas

  useEffect(() => {
    if (propFieldSchemas.length === 0) {
      loadSchema()
    }
  }, [datasetId, propFieldSchemas.length])

  useEffect(() => {
    loadItems()
  }, [datasetId, versionId, currentPage, pageSize, refreshKey])

  const loadSchema = async () => {
    try {
      const schema = await datasetService.getSchema(datasetId)
      if (schema?.field_definitions) {
        setInternalFieldSchemas(schema.field_definitions)
      }
    } catch (error) {
      // Schema might not exist yet
    }
  }

  const loadItems = async () => {
    setLoading(true)
    try {
      // When versionId is null or undefined, query draft items (version_id IS NULL)
      // When versionId is a number, query items for that specific version
      const requestParams: any = {
        page_number: currentPage,
        page_size: pageSize,
      }
      
      // Only include version_id if it's explicitly set (not null/undefined)
      // If versionId is null/undefined, don't pass it, so backend queries draft items
      if (versionId !== null && versionId !== undefined) {
        requestParams.version_id = versionId
      }
      
      const response = await datasetService.listItems(datasetId, requestParams)
      // 按更新时间降序排序
      const sortedItems = [...(response.items || [])].sort((a, b) => {
        const timeA = new Date(a.updated_at || 0).getTime()
        const timeB = new Date(b.updated_at || 0).getTime()
        return timeB - timeA // 降序
      })
      setItems(sortedItems)
      setTotal(response.total || 0)
    } catch (error: any) {
      message.error('加载数据项失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  // Reset page when version changes
  useEffect(() => {
    setCurrentPage(1)
    setSelectedRowKeys([])
  }, [versionId])

  const handleCreate = () => {
    setEditingItem(null)
    setEditorVisible(true)
  }

  const handleEdit = (item: DatasetItem) => {
    setEditingItem(item)
    setEditorVisible(true)
  }

  const handleSave = async (itemData: { data_content: DatasetItem['data_content']; item_key?: string }) => {
    try {
      if (editingItem) {
        await datasetService.updateItem(datasetId, editingItem.id, {
          data_content: itemData.data_content,
        })
        message.success('更新成功')
      } else {
        const response = await datasetService.batchCreateItems(datasetId, versionId, {
          items: [itemData],
          skip_invalid_items: false,
          allow_partial_add: false,
        })
        if (response.errors && response.errors.length > 0) {
          message.error('创建失败: ' + response.errors[0].summary)
          throw new Error(response.errors[0].summary || '创建失败')
        }
        message.success('创建成功')
      }
      setEditorVisible(false)
      setEditingItem(null)
      loadItems()
    } catch (error: any) {
      throw error
    }
  }

  const handleDelete = async (itemId: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个数据项吗？',
      onOk: async () => {
        try {
          await datasetService.deleteItem(itemId)
          message.success('删除成功')
          loadItems()
        } catch (error: any) {
          message.error('删除失败: ' + (error.message || '未知错误'))
        }
      },
    })
  }

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要删除的数据项')
      return
    }

    Modal.confirm({
      title: '确认批量删除',
      content: `确定要删除选中的 ${selectedRowKeys.length} 个数据项吗？`,
      onOk: async () => {
        try {
          await datasetService.batchDeleteItems(datasetId, selectedRowKeys as number[])
          message.success('批量删除成功')
          setSelectedRowKeys([])
          loadItems()
        } catch (error: any) {
          message.error('批量删除失败: ' + (error.message || '未知错误'))
        }
      },
    })
  }

  const handleDownload = async () => {
    if (!hasVersion || !versionId) {
      message.warning('请先选择版本')
      return
    }

    setDownloading(true)
    try {
      await datasetService.exportDataset(datasetId, versionId, 'csv')
      message.success('下载成功')
    } catch (error: any) {
      message.error('下载失败: ' + (error.message || '未知错误'))
    } finally {
      setDownloading(false)
    }
  }

  const renderTurnContent = (turns: any[]) => {
    if (!turns || turns.length === 0) {
      return <span className="text-gray-400">无数据</span>
    }

    return (
      <div className="space-y-2">
        {turns.map((turn, turnIndex) => (
          <Card key={turnIndex} size="small" title={`Turn ${turnIndex + 1}`} className="mb-2">
            {turn.field_data_list?.map((fieldData: any, fieldIndex: number) => {
              const schema = fieldSchemas.find(s => s.key === fieldData.key)
              return (
                <div key={fieldIndex} className="mb-2 pb-2 border-b last:border-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Tag color="blue">{fieldData.key}</Tag>
                    {fieldData.name && <span className="text-sm font-medium">{fieldData.name}</span>}
                  </div>
                  {fieldData.content && (
                    <div className="ml-4">
                      {fieldData.content.content_type === 'Text' && fieldData.content.text && (
                        <div className="text-sm whitespace-pre-wrap break-words">
                          {fieldData.content.text}
                        </div>
                      )}
                      {fieldData.content.content_type === 'Image' && fieldData.content.image?.url && (
                        <div>
                          <img
                            src={fieldData.content.image.url}
                            alt={fieldData.content.image.name || 'Image'}
                            className="max-w-xs max-h-32 object-contain"
                            onError={(e) => {
                              (e.target as HTMLImageElement).style.display = 'none'
                            }}
                          />
                          <div className="text-xs text-gray-500 mt-1">
                            {fieldData.content.image.name || fieldData.content.image.url}
                          </div>
                        </div>
                      )}
                      {fieldData.content.content_type === 'Audio' && fieldData.content.audio?.url && (
                        <div>
                          <audio controls src={fieldData.content.audio.url} className="w-full" />
                        </div>
                      )}
                      {fieldData.content.content_type === 'MultiPart' && (
                        <div className="text-sm text-gray-500">多部分内容</div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </Card>
        ))}
      </div>
    )
  }

  // Build columns dynamically based on schema
  const buildColumns = (): ColumnsType<DatasetItem> => {
    const baseColumns: ColumnsType<DatasetItem> = []

    // Add schema field columns
    const fieldColumns = fieldSchemas.map((field) => ({
      title: (
        <div className="flex items-center gap-1">
          <span>{field.name}</span>
          {field.is_required && <span className="text-red-500">*</span>}
        </div>
      ),
      key: field.key,
      width: 200,
      render: (_: any, record: DatasetItem) => {
        // Get field data from first turn
        const firstTurn = record.data_content?.turns?.[0]
        const fieldDataList = firstTurn?.field_data_list || []
        const fieldData = fieldDataList.find((fd: FieldData) => fd.key === field.key)
        
        return <FieldDataCell fieldSchema={field} fieldData={fieldData} />
      },
    }))

    // Add updated_at column
    const updatedAtColumn: ColumnsType<DatasetItem>[0] = {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      sorter: (a, b) =>
        new Date(a.updated_at || 0).getTime() - new Date(b.updated_at || 0).getTime(),
      render: (text: string) => formatTimestamp(text),
    }

    // Add action column
    const actionColumn: ColumnsType<DatasetItem>[0] = {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right',
      render: (_: any, record: DatasetItem) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    }

    return [...baseColumns, ...fieldColumns, updatedAtColumn, actionColumn]
  }

  const columns = buildColumns()

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => {
      setSelectedRowKeys(keys)
    },
  }

  if (!hasVersion) {
    return (
      <Empty
        description="请先创建版本"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      >
        <p className="text-gray-500">数据集创建后需要先创建版本，然后才能添加数据项</p>
      </Empty>
    )
  }

  if (!versionId) {
    return (
      <Empty
        description="请先选择版本"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      >
        <p className="text-gray-500">请从版本管理中选择一个版本，然后才能添加数据项</p>
      </Empty>
    )
  }

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <h3 className="text-lg font-semibold">数据项</h3>
        <Space>
          {selectedRowKeys.length > 0 && (
            <Button
              danger
              onClick={handleBatchDelete}
            >
              批量删除 ({selectedRowKeys.length})
            </Button>
          )}
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            loading={downloading}
            onClick={handleDownload}
          >
            下载数据集
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={items}
        rowKey="id"
        loading={loading}
        rowSelection={rowSelection}
        pagination={{
          current: currentPage,
          pageSize: pageSize,
          total: total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, size) => {
            setCurrentPage(page)
            setPageSize(size)
          },
          locale: {
            items_per_page: ' / 页',
          },
        }}
        scroll={{ x: 1200 }}
      />

      <ItemEditor
        visible={editorVisible}
        item={editingItem}
        fieldSchemas={fieldSchemas}
        onSave={handleSave}
        onCancel={() => {
          setEditorVisible(false)
          setEditingItem(null)
        }}
      />
    </div>
  )
}
