import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Input, Space, Tag, message, Progress, Popconfirm } from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  StopOutlined,
  CopyOutlined,
  RedoOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { CrudListPage } from '../../components/crud'
import { experimentService, Experiment } from '../../services/experimentService'
import { formatTimestamp } from '../../utils/dateUtils'
import type { ColumnsType } from 'antd/es/table'

export default function ExperimentListPage() {
  const navigate = useNavigate()
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'default',
      running: 'processing',
      completed: 'success',
      failed: 'error',
      stopped: 'warning',
    }
    return colors[status] || 'default'
  }

  const handleRun = async (id: number, loadData: () => void) => {
    try {
      await experimentService.run(id)
      message.success('实验已启动')
      // 立即刷新状态
      loadData()
      // 短暂延迟后再次刷新，确保状态已更新
      setTimeout(() => {
        loadData()
      }, 1000)
    } catch (error) {
      message.error('启动实验失败')
    }
  }

  const handleStop = async (id: number, loadData: () => void) => {
    try {
      await experimentService.stop(id)
      message.success('实验已停止')
      // 立即刷新状态
      loadData()
      // 短暂延迟后再次刷新，确保状态已更新
      setTimeout(() => {
        loadData()
      }, 1000)
    } catch (error) {
      message.error('停止实验失败')
    }
  }

  const handleClone = async (id: number, loadData: () => void) => {
    try {
      // 获取完整的实验数据
      const experiment = await experimentService.get(id)
      // 跳转到创建页面，传递实验数据用于回显
      navigate('/experiments/create', { state: { cloneFrom: experiment } })
    } catch (error) {
      message.error('获取实验数据失败')
    }
  }

  const handleRetry = async (id: number, loadData: () => void) => {
    try {
      await experimentService.retry(id, 'retry_all')
      message.success('实验已重试')
      // 立即刷新状态
      loadData()
      // 短暂延迟后再次刷新，确保状态已更新
      setTimeout(() => {
        loadData()
      }, 1000)
    } catch (error) {
      message.error('重试实验失败')
    }
  }

  const handleDelete = async (id: number, name: string, loadData: () => void) => {
    try {
      await experimentService.delete(id)
      message.success('实验已删除')
      loadData()
    } catch (error) {
      message.error('删除实验失败')
    }
  }

  const handleBatchDelete = async (keys: React.Key[], loadData: () => void) => {
    if (keys.length === 0) {
      message.warning('请选择要删除的实验')
      return
    }
    try {
      await experimentService.batchDelete(keys as number[])
      message.success(`已删除 ${keys.length} 个实验`)
      setSelectedRowKeys([])
      loadData()
    } catch (error) {
      message.error('批量删除失败')
    }
  }

  const columns: ColumnsType<Experiment> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Experiment) => (
        <Button
          type="link"
          onClick={() => navigate(`/experiments/${record.id}`)}
          className="p-0"
        >
          {text}
        </Button>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 150,
      render: (progress: number) => (
        <Progress percent={progress} size="small" />
      ),
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
      fixed: 'right',
    },
  ]

  return (
    <CrudListPage<Experiment>
      pageTitle="实验列表"
      pageSizeStorageKey="experiment_list_page_size"
      columns={columns}
      loadData={async (params) => {
        const skip = (params.page_number - 1) * params.page_size
        const response = await experimentService.list(skip, params.page_size, params.name)
        // 按更新时间降序排序
        const sortedExperiments = [...(response.experiments || [])].sort((a, b) => {
          const timeA = new Date(a.updated_at || 0).getTime()
          const timeB = new Date(b.updated_at || 0).getTime()
          return timeB - timeA // 降序
        })
        return {
          items: sortedExperiments,
          total: response.total || 0,
        }
      }}
      itemsKey="items"
      totalKey="total"
      viewPath={(id) => `/experiments/${id}`}
      createPath="/experiments/create"
      searchPlaceholder="搜索实验名称"
      autoRefresh={5000}
      filters={(searchText, setSearchText) => (
        <Input
          placeholder="搜索实验名称"
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
          style={{ width: 250 }}
        />
      )}
      actions={(loadData) => (
        <>
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/experiments/create')}
          >
            创建实验
          </Button>
        </>
      )}
      customActions={(record, loadData) => (
        <Space style={{ gap: '2px' }}>
          {record.status === 'running' ? (
            <Button
              type="link"
              icon={<StopOutlined />}
              onClick={() => handleStop(record.id, loadData)}
            >
              停止
            </Button>
          ) : (
            <>
              {(record.status === 'stopped' || record.status === 'pending') && (
                <Button
                  type="link"
                  icon={<PlayCircleOutlined />}
                  onClick={() => handleRun(record.id, loadData)}
                >
                  运行
                </Button>
              )}
              {record.status === 'failed' && (
                <Button
                  type="link"
                  icon={<RedoOutlined />}
                  onClick={() => handleRetry(record.id, loadData)}
                >
                  重试
                </Button>
              )}
            </>
          )}
          <Button
            type="link"
            icon={<CopyOutlined />}
            onClick={() => handleClone(record.id, loadData)}
          >
            克隆
          </Button>
          <Button
            type="link"
            onClick={() => navigate(`/experiments/${record.id}`)}
          >
            查看
          </Button>
          <Popconfirm
            title="确认删除"
            description={`确定要删除实验 "${record.name}" 吗？此操作不可恢复。`}
            onConfirm={() => handleDelete(record.id, record.name, loadData)}
            okText="删除"
            okType="danger"
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
      )}
      batchActions={(keys, loadData) => (
        keys.length > 0 ? (
          <Popconfirm
            title="确定要删除选中的实验吗？"
            onConfirm={() => handleBatchDelete(keys, loadData)}
            okText="确定"
            cancelText="取消"
          >
            <Button danger icon={<DeleteOutlined />}>
              批量删除 ({keys.length})
            </Button>
          </Popconfirm>
        ) : null
      )}
      rowSelection={{
        selectedRowKeys,
        onChange: (keys: React.Key[]) => {
          setSelectedRowKeys(keys)
        },
      }}
    />
  )
}

