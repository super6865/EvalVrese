import { useState, useEffect } from 'react'
import { Select, Table, Tag, message, Space, Button, Input, Collapse, Typography, Pagination, Tooltip } from 'antd'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { PrimaryPage, TableHeader } from '../../components/common'
import { experimentService, Experiment } from '../../services/experimentService'
import type { ColumnsType } from 'antd/es/table'
import { formatTimestampWithMs } from '../../utils/dateUtils'

const { Panel } = Collapse
const { Text } = Typography

interface CeleryLog {
  id: number
  experiment_id: number
  run_id: number
  task_id: string
  log_level: string
  message: string
  step_name: string | null
  input_data: any
  output_data: any
  timestamp: string
  created_at: string
}

interface ExperimentRun {
  id: number
  experiment_id: number
  run_number: number
  status: string
  progress: number
  started_at?: string
  completed_at?: string
  task_id?: string
}

export default function TraceAnalysisPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [selectedExperimentId, setSelectedExperimentId] = useState<number | undefined>()
  const [runs, setRuns] = useState<ExperimentRun[]>([])
  const [selectedRunId, setSelectedRunId] = useState<number | undefined>()
  const [logs, setLogs] = useState<CeleryLog[]>([])
  const [loading, setLoading] = useState(false)
  const [experimentLoading, setExperimentLoading] = useState(false)
  const [runsLoading, setRunsLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)

  useEffect(() => {
    loadExperiments()
  }, [])

  useEffect(() => {
    if (selectedExperimentId && selectedRunId) {
      loadLogs()
    } else {
      setLogs([])
    }
  }, [selectedExperimentId, selectedRunId])

  const loadExperiments = async () => {
    setExperimentLoading(true)
    try {
      // Only load experiments that have Celery logs
      const response = await experimentService.listWithCeleryLogs(0, 1000)
      setExperiments(response.experiments || [])
    } catch (error) {
      message.error('加载实验列表失败')
    } finally {
      setExperimentLoading(false)
    }
  }

  const loadLogs = async () => {
    if (!selectedExperimentId || !selectedRunId) return
    
    setLoading(true)
    try {
      const response = await experimentService.getCeleryLogs(selectedExperimentId, selectedRunId)
      setLogs(response.logs || [])
    } catch (error) {
      message.error('加载日志失败')
    } finally {
      setLoading(false)
    }
  }

  const handleExperimentChange = (experimentId: number) => {
    setSelectedExperimentId(experimentId)
    setSelectedRunId(undefined)
    setLogs([])
    setRuns([])
    
    // Load runs for the selected experiment
    if (experimentId) {
      loadRunsForExperiment(experimentId)
    }
  }

  const loadRunsForExperiment = async (experimentId: number) => {
    setRunsLoading(true)
    try {
      const response = await experimentService.listRuns(experimentId)
      const runsList = response.runs || []
      setRuns(runsList.sort((a: ExperimentRun, b: ExperimentRun) => b.id - a.id))
      
      // Auto-select the latest run if available
      if (runsList.length > 0) {
        setSelectedRunId(runsList[0].id)
      }
    } catch (error) {
      message.error('加载运行信息失败')
    } finally {
      setRunsLoading(false)
    }
  }

  // Filter logs based on search text
  const filteredLogs = logs.filter(log => {
    if (!searchText) return true
    const searchLower = searchText.toLowerCase()
    return (
      log.message.toLowerCase().includes(searchLower) ||
      log.step_name?.toLowerCase().includes(searchLower) ||
      log.log_level.toLowerCase().includes(searchLower) ||
      log.task_id.toLowerCase().includes(searchLower)
    )
  })

  // Paginate filtered logs
  const paginatedLogs = filteredLogs.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  )

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [searchText, selectedExperimentId, selectedRunId])

  const columns: ColumnsType<CeleryLog> = [
    {
      title: '时间戳',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      sorter: (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      render: (text: string) => formatTimestampWithMs(text),
    },
    {
      title: '日志级别',
      dataIndex: 'log_level',
      key: 'log_level',
      width: 140,
      filters: [
        { text: 'INFO', value: 'INFO' },
        { text: 'ERROR', value: 'ERROR' },
        { text: 'WARNING', value: 'WARNING' },
        { text: 'DEBUG', value: 'DEBUG' },
      ],
      onFilter: (value, record) => record.log_level === value,
      render: (level: string) => {
        const colorMap: Record<string, string> = {
          INFO: 'blue',
          ERROR: 'red',
          WARNING: 'orange',
          DEBUG: 'default',
        }
        return <Tag color={colorMap[level] || 'default'}>{level}</Tag>
      },
    },
    {
      title: '步骤名称',
      dataIndex: 'step_name',
      key: 'step_name',
      width: 150,
      render: (text: string | null) => text || '-',
    },
    {
      title: '日志消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: {
        showTitle: false,
      },
      render: (text: string) => (
        <Tooltip placement="topLeft" title={text}>
          <span>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: '输入/输出',
      key: 'io_data',
      width: 150,
      render: (_: any, record: CeleryLog) => {
        const hasInput = record.input_data && Object.keys(record.input_data).length > 0
        const hasOutput = record.output_data && Object.keys(record.output_data).length > 0
        if (!hasInput && !hasOutput) return <Text type="secondary">-</Text>
        return (
          <Space>
            {hasInput && <Tag color="blue">输入</Tag>}
            {hasOutput && <Tag color="green">输出</Tag>}
          </Space>
        )
      },
    },
    {
      title: 'Task ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 200,
      ellipsis: true,
      render: (text: string) => (
        <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>{text}</span>
      ),
    },
  ]

  const filters = (
    <Space wrap style={{ width: '100%', marginBottom: 16 }}>
      <Select
        placeholder="选择实验"
        showSearch
        optionFilterProp="children"
        style={{ width: 300 }}
        loading={experimentLoading}
        value={selectedExperimentId}
        onChange={handleExperimentChange}
        filterOption={(input, option) =>
          (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
        }
        options={experiments.map(exp => ({
          value: exp.id,
          label: `${exp.name} (ID: ${exp.id})`,
        }))}
      />
      {selectedExperimentId && (
        <Select
          placeholder="选择运行"
          style={{ width: 200 }}
          loading={runsLoading}
          value={selectedRunId}
          onChange={setSelectedRunId}
          options={runs.map(run => ({ 
            value: run.id, 
            label: `运行 #${run.run_number} (${run.status})` 
          }))}
        />
      )}
      <Input
        placeholder="搜索日志内容"
        prefix={<SearchOutlined />}
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
        allowClear
        style={{ width: 300 }}
      />
      <Button icon={<ReloadOutlined />} onClick={loadLogs} disabled={!selectedExperimentId || !selectedRunId}>
        刷新
      </Button>
    </Space>
  )

  const renderIODetails = (record: CeleryLog) => {
    const hasInput = record.input_data && Object.keys(record.input_data).length > 0
    const hasOutput = record.output_data && Object.keys(record.output_data).length > 0
    
    if (!hasInput && !hasOutput) return null
    
    return (
      <Collapse size="small" style={{ marginTop: 8 }}>
        {hasInput && (
          <Panel header={<Text strong>输入数据</Text>} key="input">
            <pre style={{ 
              background: '#f5f5f5', 
              padding: '12px', 
              borderRadius: '4px',
              maxHeight: '400px',
              overflow: 'auto',
              fontSize: '12px',
              margin: 0
            }}>
              {JSON.stringify(record.input_data, null, 2)}
            </pre>
          </Panel>
        )}
        {hasOutput && (
          <Panel header={<Text strong>输出数据</Text>} key="output">
            <pre style={{ 
              background: '#f5f5f5', 
              padding: '12px', 
              borderRadius: '4px',
              maxHeight: '400px',
              overflow: 'auto',
              fontSize: '12px',
              margin: 0
            }}>
              {JSON.stringify(record.output_data, null, 2)}
            </pre>
          </Panel>
        )}
      </Collapse>
    )
  }

  return (
    <PrimaryPage 
      pageTitle="事件日志" 
      filterSlot={<TableHeader filters={filters} />}
      contentClassName="flex flex-col h-full"
    >
      <div className="flex-1 overflow-hidden flex flex-col min-h-0">
        <Table
          columns={columns}
          dataSource={paginatedLogs}
          loading={loading}
          rowKey="id"
          pagination={false}
          scroll={{ y: 'calc(100vh - 380px)' }}
          expandable={{
            expandedRowRender: (record) => renderIODetails(record),
            rowExpandable: (record) => {
              const hasInput = record.input_data && Object.keys(record.input_data).length > 0
              const hasOutput = record.output_data && Object.keys(record.output_data).length > 0
              return hasInput || hasOutput
            },
          }}
        />
      </div>
      {filteredLogs.length > 0 && (
        <div className="shrink-0 flex flex-row-reverse justify-between items-center pt-4 border-t border-gray-200">
          <Pagination
            current={currentPage}
            pageSize={pageSize}
            total={filteredLogs.length}
            showSizeChanger
            showTotal={(total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条日志`}
            onChange={(page, size) => {
              setCurrentPage(page)
              setPageSize(size)
            }}
            onShowSizeChange={(_current, size) => {
              setCurrentPage(1)
              setPageSize(size)
            }}
            pageSizeOptions={['20', '50', '100', '200']}
            locale={{
              items_per_page: ' / 页',
            }}
          />
        </div>
      )}
    </PrimaryPage>
  )
}

