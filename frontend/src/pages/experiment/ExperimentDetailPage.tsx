import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Descriptions, Tag, Button, Space, Tabs, message, Spin, Progress, Table, Modal, Tooltip, Pagination } from 'antd'
import { ArrowLeftOutlined, ReloadOutlined, PlayCircleOutlined, StopOutlined, RedoOutlined, CopyOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons'
import { experimentService, Experiment } from '../../services/experimentService'
import { observabilityService } from '../../services/observabilityService'
import type { ColumnsType } from 'antd/es/table'
import AggregateResultsPanel from './components/AggregateResultsPanel'
import StatisticsPanel from './components/StatisticsPanel'
import ScoreDistributionChart from './components/ScoreDistributionChart'
import ExportPanel from './components/ExportPanel'

const { TabPane } = Tabs

interface ExperimentResult {
  id: number
  dataset_item_id: number
  evaluator_version_id: number
  score: number
  reason: string
  actual_output: string
  trace_id?: string
  input?: string
  reference_output?: string
}

export default function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [experiment, setExperiment] = useState<Experiment | null>(null)
  const [results, setResults] = useState<ExperimentResult[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  useEffect(() => {
    if (id) {
      loadExperiment()
      loadResults()
      
      // 如果实验正在运行，轮询更新
      // 停止轮询当实验状态为stopped、completed或failed时
      if (experiment?.status === 'stopped' || experiment?.status === 'completed' || experiment?.status === 'failed') {
        return
      }
      
      const interval = setInterval(() => {
        if (experiment?.status === 'running') {
          loadExperiment()
          loadResults()
        } else {
          // 如果状态不再是running，清除轮询
          clearInterval(interval)
        }
      }, 3000)
      
      return () => clearInterval(interval)
    }
  }, [id, experiment?.status])

  const loadExperiment = async () => {
    if (!id) return
    setLoading(true)
    try {
      const data = await experimentService.get(Number(id))
      setExperiment(data)
    } catch (error) {
      message.error('加载实验失败')
    } finally {
      setLoading(false)
    }
  }

  const loadResults = async () => {
    if (!id) return
    try {
      const response = await experimentService.getResults(Number(id))
      setResults(response.results || [])
    } catch (error) {
      message.error('加载结果失败')
    }
  }

  const handleRun = async () => {
    if (!id) return
    try {
      await experimentService.run(Number(id))
      message.success('实验已启动')
      loadExperiment()
    } catch (error) {
      message.error('启动实验失败')
    }
  }

  const handleStop = async () => {
    if (!id) return
    try {
      await experimentService.stop(Number(id))
      message.success('实验已停止')
      loadExperiment()
    } catch (error) {
      message.error('停止实验失败')
    }
  }

  const handleRetry = async () => {
    if (!id) return
    try {
      await experimentService.retry(Number(id), 'retry_all')
      message.success('实验已重试')
      loadExperiment()
    } catch (error) {
      message.error('重试实验失败')
    }
  }

  const handleClone = async () => {
    if (!id) return
    try {
      const cloned = await experimentService.clone(Number(id))
      message.success('实验已克隆')
      navigate(`/experiments/${cloned.id}`)
    } catch (error) {
      message.error('克隆实验失败')
    }
  }

  const handleDelete = () => {
    if (!id) return
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除实验 "${experiment.name}" 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await experimentService.delete(Number(id))
          message.success('实验已删除')
          navigate('/experiments')
        } catch (error) {
          message.error('删除实验失败')
        }
      },
    })
  }

  if (loading && !experiment) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  if (!experiment) {
    return <div>实验不存在</div>
  }

  // 解析包含 Unicode 转义序列的字符串
  const parseUnicodeString = (str: string | undefined | null): string => {
    if (!str) return '-'
    try {
      // 如果字符串看起来像 JSON 对象，尝试解析
      if (str.trim().startsWith('{') && str.trim().endsWith('}')) {
        try {
          const parsed = JSON.parse(str)
          // 如果解析后是对象，提取 reason 字段
          if (typeof parsed === 'object' && parsed.reason) {
            return parsed.reason
          }
          // 如果解析后是对象但没有 reason，返回格式化的 JSON
          if (typeof parsed === 'object') {
            return JSON.stringify(parsed, null, 2)
          }
        } catch {
          // 解析失败，继续处理
        }
      }
      
      // 如果字符串包含 Unicode 转义序列，尝试解析
      if (str.includes('\\u')) {
        // 尝试将整个字符串作为 JSON 字符串解析
        try {
          const parsed = JSON.parse(`"${str}"`)
          return parsed
        } catch {
          // 如果失败，尝试直接替换 Unicode 转义
          return str.replace(/\\u([0-9a-fA-F]{4})/g, (match, code) => {
            return String.fromCharCode(parseInt(code, 16))
          })
        }
      }
      
      // 如果是普通字符串，直接返回
      return str
    } catch {
      return str
    }
  }

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

  // 判断actual_output的来源
  const getOutputSource = (): { source: 'evaluation_target' | 'dataset'; label: string; color: string } => {
    if (!experiment?.evaluation_target_config) {
      return { source: 'dataset', label: '来自数据集', color: 'blue' }
    }
    
    const targetType = experiment.evaluation_target_config.type
    if (targetType && targetType !== 'none') {
      return { source: 'evaluation_target', label: '来自评测对象', color: 'green' }
    }
    
    return { source: 'dataset', label: '来自数据集', color: 'blue' }
  }

  const resultColumns: ColumnsType<ExperimentResult> = [
    {
      title: '评测入参',
      dataIndex: 'input',
      key: 'input',
      width: 200,
      ellipsis: true,
      render: (text: string) => {
        const displayText = text || '-'
        return (
          <Tooltip title={displayText} placement="topLeft">
            <span>{displayText}</span>
          </Tooltip>
        )
      },
    },
    {
      title: '参考输出',
      dataIndex: 'reference_output',
      key: 'reference_output',
      width: 200,
      ellipsis: true,
      render: (text: string) => {
        const displayText = text || '-'
        return (
          <Tooltip title={displayText} placement="topLeft">
            <span>{displayText}</span>
          </Tooltip>
        )
      },
    },
    {
      title: '评分',
      dataIndex: 'score',
      key: 'score',
      width: 100,
      render: (score: number) => (
        <Tag color={score >= 0.8 ? 'green' : score >= 0.5 ? 'orange' : 'red'}>
          {score !== null && score !== undefined ? score.toFixed(2) : '-'}
        </Tag>
      ),
    },
    {
      title: '原因',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true,
      render: (text: string) => {
        const parsedText = parseUnicodeString(text)
        return (
          <Tooltip title={parsedText} placement="topLeft">
            <span>{parsedText}</span>
          </Tooltip>
        )
      },
    },
    {
      title: (
        <div className="flex items-center gap-2">
          <span>实际输出</span>
          {experiment && (
            <Tooltip
              title={
                getOutputSource().source === 'evaluation_target'
                  ? '此输出来自评测对象的执行结果'
                  : '此输出来自数据集中的output字段'
              }
            >
              <Tag color={getOutputSource().color} size="small">
                {getOutputSource().label}
              </Tag>
            </Tooltip>
          )}
        </div>
      ),
      dataIndex: 'actual_output',
      key: 'actual_output',
      ellipsis: true,
      render: (text: string) => {
        const outputSource = getOutputSource()
        const isError = text && text.startsWith('[评测对象调用失败]')
        const displayText = text || '-'
        
        return (
          <div className="flex items-center gap-2">
            {isError ? (
              <Tooltip title={displayText} placement="topLeft">
                <Tag color="error" style={{ margin: 0 }}>
                  {displayText}
                </Tag>
              </Tooltip>
            ) : (
              <Tooltip title={displayText} placement="topLeft">
                <span>{displayText}</span>
        </Tooltip>
            )}
            {!isError && (
              <Tag color={outputSource.color} size="small" style={{ margin: 0 }}>
                {outputSource.label}
              </Tag>
            )}
          </div>
        )
      },
    },
    {
      title: 'Trace',
      key: 'trace',
      width: 120,
      render: (_: any, record: ExperimentResult) => {
        if (!record.trace_id) {
          return <span>-</span>
        }
        return (
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/observability/traces/${record.trace_id}`)}
          >
            查看
          </Button>
        )
      },
    },
  ]

  return (
    <div className="h-full flex flex-col">
      <Card className="mb-4">
        <div className="flex items-center justify-between mb-4">
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/experiments')}>
              返回
            </Button>
            <h2 className="text-xl font-semibold m-0">{experiment.name}</h2>
            <Tag color={getStatusColor(experiment.status)}>
              {experiment.status.toUpperCase()}
            </Tag>
          </Space>
          <Space>
            {experiment.status === 'running' ? (
              <Button icon={<StopOutlined />} onClick={handleStop}>
                停止
              </Button>
            ) : (
              <>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleRun}
              >
                运行
              </Button>
                {experiment.status !== 'pending' && (
                  <Button icon={<RedoOutlined />} onClick={handleRetry}>
                    重试
                  </Button>
                )}
              </>
            )}
            <Button icon={<CopyOutlined />} onClick={handleClone}>
              克隆
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadExperiment}>
              刷新
            </Button>
            <Button 
              danger 
              icon={<DeleteOutlined />} 
              onClick={handleDelete}
            >
              删除
            </Button>
          </Space>
        </div>
        <Descriptions column={3} bordered>
          <Descriptions.Item label="ID">{experiment.id}</Descriptions.Item>
          <Descriptions.Item label="名称">{experiment.name}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={getStatusColor(experiment.status)}>
              {experiment.status.toUpperCase()}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="进度">
            <Progress percent={experiment.progress} size="small" />
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            {experiment.description || '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <Tabs activeKey={activeTab} onChange={setActiveTab} className="flex-1 flex flex-col">
          <TabPane tab="概览" key="overview">
            <div className="space-y-4 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 300px)' }}>
              <Card size="small" title="实验配置">
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="数据集版本ID">
                    {experiment.dataset_version_id}
                  </Descriptions.Item>
                  <Descriptions.Item label="评估器数量">
                    {experiment.evaluator_version_ids?.length || 0}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
              <StatisticsPanel experimentId={experiment.id} />
              <AggregateResultsPanel experimentId={experiment.id} />
              <ScoreDistributionChart experimentId={experiment.id} />
              <ExportPanel experimentId={experiment.id} />
            </div>
          </TabPane>
          <TabPane tab="结果" key="results" style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
            <div className="flex flex-col h-full min-h-0">
              <div className="flex-1 overflow-hidden min-h-0">
                <Table
                  columns={resultColumns}
                  dataSource={results.slice((currentPage - 1) * pageSize, currentPage * pageSize)}
                  rowKey="id"
                  pagination={false}
                  scroll={{ y: 'calc(100vh - 500px)' }}
                />
              </div>
              {results.length > 0 && (
                <div className="shrink-0 flex flex-row-reverse justify-between items-center pt-4 border-t border-gray-200">
                  <Pagination
                    current={currentPage}
                    pageSize={pageSize}
                    total={results.length}
                    showSizeChanger
                    showTotal={(total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`}
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
            </div>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

