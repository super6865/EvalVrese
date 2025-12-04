import { useState, useEffect, useRef } from 'react'
import { Card, Button, Table, Tag, message, Space, Popconfirm } from 'antd'
import { DownloadOutlined, ReloadOutlined, FileTextOutlined } from '@ant-design/icons'
import { experimentService } from '../../../services/experimentService'
import type { ColumnsType } from 'antd/es/table'
import { formatTimestamp } from '../../../utils/dateUtils'

interface ExportRecord {
  id: number
  status: string
  file_name: string | null
  file_url: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

interface ExportPanelProps {
  experimentId: number
}

export default function ExportPanel({ experimentId }: ExportPanelProps) {
  const [loading, setLoading] = useState(false)
  const [exports, setExports] = useState<ExportRecord[]>([])
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)
  const previousExportsRef = useRef<ExportRecord[]>([])

  useEffect(() => {
    loadExports()
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
    }
  }, [experimentId])

  const loadExports = async () => {
    setLoading(true)
    try {
      const response = await experimentService.listExports(experimentId)
      const newExports = response.exports || []
      
      // Check if any export just completed (was pending/running, now success)
      const previousExports = previousExportsRef.current
      const justCompleted = newExports.find((exp: ExportRecord) => {
        const statusUpper = exp.status.toUpperCase()
        if (statusUpper === 'SUCCESS') {
          const previous = previousExports.find(p => p.id === exp.id)
          if (previous) {
            const prevStatusUpper = previous.status.toUpperCase()
            return prevStatusUpper === 'PENDING' || prevStatusUpper === 'RUNNING'
          }
        }
        return false
      })
      
      // Update ref before setting state
      previousExportsRef.current = newExports
      setExports(newExports)
      
      // Auto-download if export just completed
      if (justCompleted) {
        setTimeout(() => {
          handleDownload(justCompleted.id)
        }, 500) // Small delay to ensure file is ready
      }
      
      // Stop polling if all exports are completed or failed
      const hasPending = newExports.some((exp: ExportRecord) => {
        const statusUpper = exp.status.toUpperCase()
        return statusUpper === 'PENDING' || statusUpper === 'RUNNING'
      })
      
      if (!hasPending && pollingInterval) {
        clearInterval(pollingInterval)
        setPollingInterval(null)
      }
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.message || '未知错误'
      message.error(`加载导出记录失败: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateExport = async () => {
    try {
      await experimentService.createExport(experimentId)
      message.success('导出任务已创建')
      loadExports()
      
      // Start polling for status updates
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
      const interval = setInterval(() => {
        loadExports()
      }, 2000)
      setPollingInterval(interval)
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.message || '未知错误'
      message.error(`创建导出任务失败: ${errorMessage}`)
    }
  }

  const handleDownload = async (exportId: number) => {
    try {
      const exportRecord = exports.find(exp => exp.id === exportId)
      const fileName = exportRecord?.file_name || `export_${exportId}.csv`
      
      await experimentService.downloadExport(exportId, fileName)
      message.success('下载成功')
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.message || '未知错误'
      message.error(`下载失败: ${errorMessage}`)
    }
  }

  const getStatusColor = (status: string) => {
    const statusLower = status.toLowerCase()
    const colors: Record<string, string> = {
      pending: 'default',
      running: 'processing',
      success: 'success',
      failed: 'error',
    }
    return colors[statusLower] || 'default'
  }

  const columns: ColumnsType<ExportRecord> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
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
      title: '文件名',
      dataIndex: 'file_name',
      key: 'file_name',
      render: (name: string) => name || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => formatTimestamp(time),
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      render: (time: string) => formatTimestamp(time),
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
      render: (msg: string) => (msg ? <span className="text-red-500">{msg}</span> : '-'),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: ExportRecord) => (
        <Space>
          {(record.status.toUpperCase() === 'SUCCESS') && (
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownload(record.id)}
            >
              下载
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <Card
      title="导出记录"
      className="mb-4"
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadExports}>
            刷新
          </Button>
          <Button type="primary" icon={<FileTextOutlined />} onClick={handleCreateExport}>
            创建导出
          </Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={exports}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
    </Card>
  )
}

