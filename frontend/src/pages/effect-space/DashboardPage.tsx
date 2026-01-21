import { useState, useEffect, useMemo } from 'react'
import {
  Button,
  Select,
  Table,
  Space,
  message,
  Spin,
  Tag,
  Card,
  Tabs,
  Empty,
  Tooltip,
  Modal,
  Pagination,
  Layout,
  Tree,
  Input,
} from 'antd'
import { FolderOutlined, SearchOutlined } from '@ant-design/icons'
import {
  PlusOutlined,
  ReloadOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClearOutlined,
  UpOutlined,
  DownOutlined,
} from '@ant-design/icons'
import { experimentService, Experiment } from '../../services/experimentService'
import { experimentGroupService, ExperimentGroup } from '../../services/experimentGroupService'
import { datasetService } from '../../services/datasetService'
import { evaluatorService } from '../../services/evaluatorService'
import { modelSetService } from '../../services/modelSetService'
import { promptService } from '../../services/promptService'
import type { ColumnsType } from 'antd/es/table'
import type { DataNode } from 'antd/es/tree'

const { Option } = Select

interface ComparisonDetail {
  dataset_item_id: number
  input: string
  reference_output: string
  actual_output: string
  experiments: Array<{
    experiment_id: number
    experiment_name: string
    response: string
    status: string
    execution_time_ms: number
    input_tokens: number
    output_tokens: number
    score?: number
    evaluator_name?: string
    error_message?: string
  }>
}

interface ComparisonMetrics {
  evaluator_scores: {
    common_evaluators: Array<{
      evaluator_version_id: number
      name: string
      version: string
    }>
    comparison_metrics: Record<number, {
      evaluator: {
        evaluator_version_id: number
        name: string
        version: string
      }
      experiments: Array<{
        experiment_id: number
        experiment_name: string
        average_score?: number
        max_score?: number
        min_score?: number
        sum_score?: number
        total_count: number
      }>
    }>
  }
  runtime_metrics: {
    total_latency: {
      metric_name: string
      unit: string
      experiments: Array<{
        experiment_id: number
        experiment_name: string
        value: number
        avg_value?: number
        max_value?: number
        min_value?: number
      }>
    }
    input_tokens: {
      metric_name: string
      unit: string
      experiments: Array<{
        experiment_id: number
        experiment_name: string
        value: number
        avg_value?: number
        max_value?: number
        min_value?: number
      }>
    }
    output_tokens: {
      metric_name: string
      unit: string
      experiments: Array<{
        experiment_id: number
        experiment_name: string
        value: number
        avg_value?: number
        max_value?: number
        min_value?: number
      }>
    }
    total_tokens: {
      metric_name: string
      unit: string
      experiments: Array<{
        experiment_id: number
        experiment_name: string
        value: number
        avg_value?: number
        max_value?: number
        min_value?: number
      }>
    }
  }
}

interface ExperimentTooltipData {
  experimentId: number
  experimentName: string
  groupLabel: string
  datasetName: string
  datasetVersion: string
  evaluationTarget: {
    type: string
    name: string
    version: string
  }
  evaluators: Array<{
    evaluatorVersionId: number
    name: string
    version: string
    type: string
    currentValue?: number
    color: string
  }>
}

const { Sider, Content } = Layout

export default function DashboardPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [baselineExperimentId, setBaselineExperimentId] = useState<number | null>(null)
  const [comparisonExperimentIds, setComparisonExperimentIds] = useState<number[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('data-details')
  const [comparisonDetails, setComparisonDetails] = useState<ComparisonDetail[]>([])
  const [comparisonMetrics, setComparisonMetrics] = useState<ComparisonMetrics | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [evaluatorAggregation, setEvaluatorAggregation] = useState<Record<string, 'avg' | 'max' | 'min' | 'sum' | 'count'>>({})
  const [runtimeAggregation, setRuntimeAggregation] = useState<Record<string, 'total' | 'avg' | 'max' | 'min'>>({})
  
  // Collapse states for main sections
  const [evaluatorScoresCollapsed, setEvaluatorScoresCollapsed] = useState(false)
  const [runtimeMetricsCollapsed, setRuntimeMetricsCollapsed] = useState(false)
  
  // Tooltip data cache
  const [tooltipDataCache, setTooltipDataCache] = useState<Record<number, ExperimentTooltipData | null>>({})
  const [tooltipLoading, setTooltipLoading] = useState<Record<number, boolean>>({})
  
  // Modal states
  const [selectModalVisible, setSelectModalVisible] = useState(false)
  const [selectStep, setSelectStep] = useState<'experiments' | 'baseline'>('experiments')
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null)
  const [treeData, setTreeData] = useState<DataNode[]>([])
  const [tempSelectedExperimentIds, setTempSelectedExperimentIds] = useState<number[]>([])
  const [tempBaselineExperimentId, setTempBaselineExperimentId] = useState<number | null>(null)
  const [searchText, setSearchText] = useState('')
  const [hasRestored, setHasRestored] = useState(false)

  useEffect(() => {
    loadExperiments()
    loadGroups()
  }, [])

  // Restore comparison data after experiments are loaded
  useEffect(() => {
    if (experiments.length > 0 && !hasRestored) {
      restoreComparisonData()
      setHasRestored(true)
    }
  }, [experiments, hasRestored])

  // Restore comparison data from localStorage
  const restoreComparisonData = async () => {
    try {
      const savedBaselineId = localStorage.getItem('comparison_baseline_id')
      const savedComparisonIds = localStorage.getItem('comparison_experiment_ids')
      
      if (savedBaselineId && savedComparisonIds) {
        const baselineId = parseInt(savedBaselineId)
        const comparisonIds = JSON.parse(savedComparisonIds)
        
        // Verify experiments still exist
        const allIds = [baselineId, ...comparisonIds]
        const allExist = allIds.every(id => experiments.some(e => e.id === id))
        
        if (allExist && allIds.length >= 2) {
          setBaselineExperimentId(baselineId)
          setComparisonExperimentIds(comparisonIds)
          
          // Load comparison data
          setLoading(true)
          try {
            const validation = await experimentService.validateComparison(allIds)
            if (validation.valid) {
              const [details, metrics] = await Promise.all([
                experimentService.getComparisonDetails(allIds),
                experimentService.getComparisonMetrics(allIds),
              ])
              setComparisonDetails(details.details || [])
              setComparisonMetrics(metrics)
            } else {
              // Clear invalid data
              localStorage.removeItem('comparison_baseline_id')
              localStorage.removeItem('comparison_experiment_ids')
            }
          } catch (error) {
            // Clear on error
            localStorage.removeItem('comparison_baseline_id')
            localStorage.removeItem('comparison_experiment_ids')
          } finally {
            setLoading(false)
          }
        }
      }
    } catch (error) {
      // Ignore restore errors
    }
  }

  // Save comparison data to localStorage
  const saveComparisonData = (baselineId: number, comparisonIds: number[]) => {
    localStorage.setItem('comparison_baseline_id', baselineId.toString())
    localStorage.setItem('comparison_experiment_ids', JSON.stringify(comparisonIds))
  }

  // Clear comparison data
  const handleClearComparison = () => {
    Modal.confirm({
      title: '确认清空',
      content: '确定要清空当前对比数据吗？',
      onOk: () => {
        setBaselineExperimentId(null)
        setComparisonExperimentIds([])
        setComparisonDetails([])
        setComparisonMetrics(null)
        setCurrentPage(1)
        localStorage.removeItem('comparison_baseline_id')
        localStorage.removeItem('comparison_experiment_ids')
        message.success('对比数据已清空')
      },
      okText: '确定',
      cancelText: '取消',
    })
  }

  const loadExperiments = async () => {
    try {
      const response = await experimentService.list(0, 1000)
      setExperiments(response.experiments || [])
    } catch (error) {
      message.error('加载实验列表失败')
    }
  }

  const loadGroups = async () => {
    try {
      const response = await experimentGroupService.getTree()
      const groups = response.groups || []
      const treeNodes = convertGroupsToTreeNodes(groups)
      const rootNode: DataNode = {
        title: '全部实验',
        key: 'root',
        icon: <FolderOutlined />,
        children: treeNodes,
      }
      setTreeData([rootNode])
    } catch (error) {
      // Ignore error
    }
  }

  const convertGroupsToTreeNodes = (groups: ExperimentGroup[]): DataNode[] => {
    return groups.map(group => ({
      title: group.name,
      key: `group-${group.id}`,
      icon: <FolderOutlined />,
      children: group.children ? convertGroupsToTreeNodes(group.children) : undefined,
      data: group,
    }))
  }

  const handleTreeSelect = (selectedKeys: React.Key[]) => {
    if (selectedKeys.length === 0) {
      setSelectedGroupId(null)
      return
    }
    
    const key = selectedKeys[0] as string
    if (key === 'root') {
      setSelectedGroupId(null)
    } else if (key.startsWith('group-')) {
      const groupId = parseInt(key.replace('group-', ''))
      setSelectedGroupId(groupId)
    }
  }

  const getFilteredExperiments = () => {
    let filtered = experiments
    
    // Filter by group
    if (selectedGroupId !== null) {
      filtered = filtered.filter(exp => exp.group_id === selectedGroupId)
    }
    
    // Filter by search text
    if (searchText) {
      filtered = filtered.filter(exp => 
        exp.name.toLowerCase().includes(searchText.toLowerCase())
      )
    }
    
    return filtered
  }

  const handleOpenSelectModal = () => {
    setSelectModalVisible(true)
    setSelectStep('experiments')
    setTempSelectedExperimentIds([])
    setTempBaselineExperimentId(null)
    setSelectedGroupId(null)
    setSearchText('')
  }

  const handleSelectExperimentsNext = () => {
    if (tempSelectedExperimentIds.length < 2) {
      message.warning('请至少选择2个实验进行对比')
      return
    }
    setSelectStep('baseline')
  }

  const handleConfirmComparison = async () => {
    if (!tempBaselineExperimentId) {
      message.warning('请选择基准实验')
      return
    }

    const allExperimentIds = [tempBaselineExperimentId, ...tempSelectedExperimentIds.filter(id => id !== tempBaselineExperimentId)]
    
    // Validate comparison
    setLoading(true)
    try {
      const validation = await experimentService.validateComparison(allExperimentIds)
      if (!validation.valid) {
        Modal.error({
          title: '无法进行对比',
          content: validation.message || '选择的实验使用了不同的数据集或版本，无法进行对比。请确保所有实验使用相同的数据集和相同版本。',
        })
        setLoading(false)
        return
      }

      // Set the selected experiments
      const newComparisonIds = tempSelectedExperimentIds.filter(id => id !== tempBaselineExperimentId)
      setBaselineExperimentId(tempBaselineExperimentId)
      setComparisonExperimentIds(newComparisonIds)

      // Save to localStorage
      saveComparisonData(tempBaselineExperimentId, newComparisonIds)

      // Load comparison data
      const [details, metrics] = await Promise.all([
        experimentService.getComparisonDetails(allExperimentIds),
        experimentService.getComparisonMetrics(allExperimentIds),
      ])

      setComparisonDetails(details.details || [])
      setComparisonMetrics(metrics)
      setCurrentPage(1)
      setSelectModalVisible(false)
      message.success('对比数据加载成功')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载对比数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handleBaselineChange = async (newBaselineId: number) => {
    if (!baselineExperimentId || comparisonExperimentIds.length === 0) {
      setBaselineExperimentId(newBaselineId)
      return
    }

    // Update comparison experiment IDs: add old baseline, remove new baseline
    const oldBaselineId = baselineExperimentId
    const newComparisonIds = [
      ...comparisonExperimentIds.filter(id => id !== newBaselineId),
      oldBaselineId
    ]

    // Set new baseline and comparison IDs
    setBaselineExperimentId(newBaselineId)
    setComparisonExperimentIds(newComparisonIds)

    // Save to localStorage
    saveComparisonData(newBaselineId, newComparisonIds)

    // Reload comparison data with new baseline
    const allExperimentIds = [newBaselineId, ...newComparisonIds]
    setLoading(true)
    try {
      const [details, metrics] = await Promise.all([
        experimentService.getComparisonDetails(allExperimentIds),
        experimentService.getComparisonMetrics(allExperimentIds),
      ])
      setComparisonDetails(details.details || [])
      setComparisonMetrics(metrics)
      setCurrentPage(1)
      message.success('基准已切换')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '切换基准失败')
      // Revert on error
      setBaselineExperimentId(oldBaselineId)
      setComparisonExperimentIds(comparisonExperimentIds)
      saveComparisonData(oldBaselineId, comparisonExperimentIds)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    if (baselineExperimentId && comparisonExperimentIds.length > 0) {
      const allExperimentIds = [baselineExperimentId, ...comparisonExperimentIds]
      setLoading(true)
      try {
        const [details, metrics] = await Promise.all([
          experimentService.getComparisonDetails(allExperimentIds),
          experimentService.getComparisonMetrics(allExperimentIds),
        ])
        setComparisonDetails(details.details || [])
        setComparisonMetrics(metrics)
        setCurrentPage(1)
        message.success('数据已刷新')
      } catch (error: any) {
        message.error(error.response?.data?.detail || '刷新数据失败')
      } finally {
        setLoading(false)
      }
    }
  }

  const getStatusColor = (status: string) => {
    if (status === 'success') return 'success'
    if (status === 'failed') return 'error'
    return 'default'
  }

  const getStatusText = (status: string) => {
    if (status === 'success') return '成功'
    if (status === 'failed') return '失败'
    return '待处理'
  }

  // Build data details table columns
  const dataDetailsColumns = useMemo<ColumnsType<ComparisonDetail>>(() => {
    const allExperimentIds = baselineExperimentId
      ? [baselineExperimentId, ...comparisonExperimentIds]
      : []

    const columns: ColumnsType<ComparisonDetail> = [
      {
        title: 'ID',
        dataIndex: 'dataset_item_id',
        key: 'dataset_item_id',
        width: 100,
        fixed: 'left',
        render: (id: number) => `#${id}`,
      },
      {
        title: 'Input',
        dataIndex: 'input',
        key: 'input',
        width: 200,
        ellipsis: false,
        render: (text: string) => {
          if (!text) return '-'
          const maxLength = 50
          const shouldTruncate = text.length > maxLength
          const displayText = shouldTruncate ? text.substring(0, maxLength) + '...' : text
          
          return (
            <Tooltip title={text} placement="topLeft">
              <span style={{ cursor: shouldTruncate ? 'pointer' : 'default' }}>{displayText}</span>
            </Tooltip>
          )
        },
      },
      {
        title: 'Reference Output',
        dataIndex: 'reference_output',
        key: 'reference_output',
        width: 200,
        ellipsis: true,
        render: (text: string) => (
          <Tooltip title={text}>
            <span>{text || '-'}</span>
          </Tooltip>
        ),
      },
    ]

    // Add columns for each experiment
    allExperimentIds.forEach((expId, index) => {
      const experiment = experiments.find((e) => e.id === expId)
      const isBaseline = index === 0

      columns.push({
        title: isBaseline ? `基准组 - ${experiment?.name || ''}` : `实验组${index} - ${experiment?.name || ''}`,
        key: `exp_${expId}`,
        width: 300,
          render: (_: any, record: ComparisonDetail) => {
          const expData = record.experiments.find((e) => e.experiment_id === expId)
          if (!expData) return <Empty description="无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />

          return (
            <div className="space-y-2">
              <div className="text-sm mb-2">{expData.response || '-'}</div>
              <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                <span className="text-gray-400">&lt;&gt;</span>
                <span>{expData.evaluator_name || 'Unknown'}</span>
                {expData.score !== null && expData.score !== undefined && (
                  <span className="text-gray-400">{expData.score.toFixed(1)}</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Tag color={getStatusColor(expData.status)} icon={expData.status === 'success' ? <CheckCircleOutlined /> : <CloseCircleOutlined />}>
                  {getStatusText(expData.status)}
                </Tag>
                <span className="text-xs text-gray-500">{expData.execution_time_ms}ms</span>
                <span className="text-xs text-gray-500">{expData.input_tokens + expData.output_tokens}</span>
              </div>
            </div>
          )
        },
      })
    })

    columns.push({
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right',
      render: () => (
        <Button
          type="link"
          onClick={() => {
            message.info('详情功能暂未开发')
          }}
        >
          详情
        </Button>
      ),
    })

    return columns
  }, [baselineExperimentId, comparisonExperimentIds, experiments])

  // Vertical bar chart component
  const SimpleBarChart = ({
    data,
    maxValue,
    colors,
    getColor,
    currentEvaluatorId,
  }: {
    data: Array<{ name: string; value: number; experimentId?: number }>
    maxValue?: number
    colors?: string[]
    getColor?: (experimentId: number) => string
    currentEvaluatorId?: number
  }) => {
    // Calculate maxValue if not provided
    const calculatedMaxValue = maxValue !== undefined 
      ? maxValue 
      : Math.max(...data.map(item => item.value), 1)
    
    if (calculatedMaxValue === 0 || data.length === 0) {
      return <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
    }

    const chartHeight = 220 // 图表高度
    const labelSpace = 30 // 为数值标签预留的顶部空间
    const effectiveChartHeight = chartHeight - labelSpace // 实际可用于柱状图的高度
    const barWidth = Math.max(50, Math.floor(280 / data.length)) // 柱子宽度，根据数据量自适应
    const yAxisTicks = 6 // Y轴刻度数量（0, 0.2, 0.4, 0.6, 0.8, 1）

    // Use getColor function if provided, otherwise fall back to colors array or default light colors
    const defaultLightColors = [
      '#a8d5e2', '#b8e6b8', '#ffd4a3', '#e2b8e6', '#ffb3ba', '#bae1ff', '#ffffba', '#c7ceea'
    ]

    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        width: '100%',
        padding: '16px'
      }}>
        {/* Y轴标签和图表区域 */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'flex-end',
          height: `${chartHeight}px`,
          paddingLeft: '45px',
          paddingRight: '20px',
          position: 'relative',
          borderBottom: '1px solid #e8e8e8',
          marginBottom: '12px'
        }}>
          {/* Y轴刻度线和网格线 */}
          <div style={{
            position: 'absolute',
            left: 0,
            top: `${labelSpace}px`,
            bottom: 0,
            width: '45px'
          }}>
            {Array.from({ length: yAxisTicks }, (_, i) => {
              // 从最大值到0，从顶部到底部
              const ratio = 1 - (i / (yAxisTicks - 1))
              const value = calculatedMaxValue * ratio
              // 计算Y轴刻度的位置：从底部开始，0在底部，最大值在顶部
              const tickPosition = (ratio * effectiveChartHeight)
              return (
                <div key={ratio} style={{
                  position: 'absolute',
                  bottom: `${tickPosition}px`,
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  transform: 'translateY(50%)'
                }}>
                  <div style={{
                    fontSize: '12px',
                    color: '#666',
                    textAlign: 'right',
                    paddingRight: '8px',
                    width: '100%'
                  }}>
                    {value.toFixed(1)}
                  </div>
                  {/* 网格线 */}
                  <div style={{
                    position: 'absolute',
                    left: '45px',
                    right: '0',
                    height: '1px',
                    backgroundColor: '#f0f0f0',
                    zIndex: 0
                  }} />
                </div>
              )
            })}
          </div>

          {/* 柱状图区域 */}
          <div style={{ 
            flex: 1, 
            display: 'flex', 
            alignItems: 'flex-end',
            justifyContent: 'center',
            gap: '20px',
            paddingLeft: '10px',
            position: 'relative',
            zIndex: 1
          }}>
            {data.map((item, index) => {
              const percentage = calculatedMaxValue > 0 ? (item.value / calculatedMaxValue) * 100 : 0
              const barHeight = (percentage / 100) * effectiveChartHeight
              const barColor = getColor && item.experimentId 
                ? getColor(item.experimentId)
                : (colors && colors.length > 0 ? colors[index % colors.length] : defaultLightColors[index % defaultLightColors.length])
              
              return (
                <div 
                  key={item.name}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    width: `${barWidth}px`,
                    height: '100%',
                    position: 'relative'
                  }}
                >
                  {/* 数值标签（在柱子顶部上方） */}
                  {item.value > 0 && (
                    <div style={{
                      position: 'absolute',
                      bottom: `${barHeight + 8}px`,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      fontSize: '13px',
                      fontWeight: 500,
                      color: '#333',
                      whiteSpace: 'nowrap',
                      zIndex: 2,
                      pointerEvents: 'none'
                    }}>
                      {item.value.toLocaleString()}
                    </div>
                  )}
                  
                  {/* 柱子 */}
                  {item.experimentId ? (
                    <Tooltip
                      title={
                        <ExperimentTooltip
                          experimentId={item.experimentId}
                          currentEvaluatorValue={item.value}
                          currentEvaluatorId={currentEvaluatorId}
                        />
                      }
                      overlayStyle={{ maxWidth: 'none' }}
                      overlayInnerStyle={{ 
                        backgroundColor: '#fff',
                        color: '#333',
                        padding: 0
                      }}
                      color="#fff"
                      placement="top"
                      mouseEnterDelay={0.3}
                    >
                      <div
                        style={{
                          width: `${barWidth * 0.6}px`,
                          height: `${Math.max(barHeight, item.value > 0 ? 3 : 0)}px`,
                          backgroundColor: barColor,
                          borderRadius: '4px 4px 0 0',
                          transition: 'height 0.3s ease',
                          minHeight: item.value > 0 ? '3px' : '0',
                          position: 'relative',
                          cursor: 'pointer',
                          boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                        }}
                      />
                    </Tooltip>
                  ) : (
                    <div
                      style={{
                        width: `${barWidth * 0.6}px`,
                        height: `${Math.max(barHeight, item.value > 0 ? 3 : 0)}px`,
                        backgroundColor: barColor,
                        borderRadius: '4px 4px 0 0',
                        transition: 'height 0.3s ease',
                        minHeight: item.value > 0 ? '3px' : '0',
                        position: 'relative',
                        cursor: 'pointer',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                      }}
                      title={`${item.name}: ${item.value.toLocaleString()}`}
                    />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* X轴标签（实验名称） */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center',
          paddingLeft: '45px',
          paddingRight: '20px',
          gap: '20px',
          marginBottom: '16px'
        }}>
          {data.map((item) => (
            <div 
              key={item.name}
              style={{
                width: `${barWidth}px`,
                fontSize: '12px',
                color: '#666',
                textAlign: 'center',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}
              title={item.name}
            >
              {item.name}
            </div>
          ))}
        </div>

        {/* 图例 */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '24px',
          paddingTop: '8px',
          borderTop: '1px solid #f0f0f0'
        }}>
          {data.map((item, index) => {
            const barColor = getColor && item.experimentId 
              ? getColor(item.experimentId)
              : (colors && colors.length > 0 ? colors[index % colors.length] : defaultLightColors[index % defaultLightColors.length])
            
            return (
              <div 
                key={item.name}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <div style={{
                  width: '12px',
                  height: '12px',
                  backgroundColor: barColor,
                  borderRadius: '2px'
                }} />
                <span style={{
                  fontSize: '12px',
                  color: '#666'
                }}>
                  {item.name}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  // Helper function to get aggregated value for evaluator scores
  const getEvaluatorAggregatedValue = (exp: {
    average_score?: number
    max_score?: number
    min_score?: number
    sum_score?: number
    total_count: number
  }, aggregation: 'avg' | 'max' | 'min' | 'sum' | 'count'): number => {
    switch (aggregation) {
      case 'avg':
        return exp.average_score || 0
      case 'max':
        return exp.max_score || 0
      case 'min':
        return exp.min_score || 0
      case 'sum':
        return exp.sum_score !== undefined ? exp.sum_score : (exp.average_score || 0) * (exp.total_count || 0)
      case 'count':
        return exp.total_count || 0
      default:
        return exp.average_score || 0
    }
  }

  // Helper function to get aggregated value for runtime metrics
  const getRuntimeAggregatedValue = (
    exp: {
      value: number
      avg_value?: number
      max_value?: number
      min_value?: number
    },
    aggregation: 'total' | 'avg' | 'max' | 'min'
  ): number => {
    switch (aggregation) {
      case 'total':
        return exp.value || 0
      case 'avg':
        return exp.avg_value || 0
      case 'max':
        return exp.max_value || 0
      case 'min':
        return exp.min_value || 0
      default:
        return exp.value || 0
    }
  }

  // Helper function to get experiment group label (基准组, 实验组1, 实验组2, etc.)
  const getExperimentGroupLabel = (experimentId: number): string => {
    if (baselineExperimentId === experimentId) {
      return '基准组'
    }
    const index = comparisonExperimentIds.indexOf(experimentId)
    if (index >= 0) {
      return `实验组${index + 1}`
    }
    // Fallback: if not found, return original name (should not happen)
    return `实验${experimentId}`
  }

  // Light color palette for different experiment groups
  const lightColors = [
    '#a8d5e2', // 浅蓝色 - 基准组
    '#b8e6b8', // 浅绿色 - 实验组1
    '#ffd4a3', // 浅橙色 - 实验组2
    '#e2b8e6', // 浅紫色 - 实验组3
    '#ffb3ba', // 浅粉色 - 实验组4
    '#bae1ff', // 浅天蓝色 - 实验组5
    '#ffffba', // 浅黄色 - 实验组6
    '#c7ceea', // 浅蓝紫色 - 实验组7
  ]

  // Helper function to get color for experiment group
  const getExperimentColor = (experimentId: number): string => {
    if (baselineExperimentId === experimentId) {
      return lightColors[0] // 基准组使用第一个颜色
    }
    const index = comparisonExperimentIds.indexOf(experimentId)
    if (index >= 0) {
      return lightColors[(index + 1) % lightColors.length] // 实验组使用后续颜色
    }
    return lightColors[0] // Fallback
  }

  // Load experiment tooltip data
  const loadExperimentTooltipData = async (
    experimentId: number,
    currentEvaluatorValue?: number,
    currentEvaluatorId?: number
  ): Promise<ExperimentTooltipData | null> => {
    // Check cache first
    if (tooltipDataCache[experimentId] !== undefined) {
      return tooltipDataCache[experimentId]
    }

    // Check if already loading
    if (tooltipLoading[experimentId]) {
      return null
    }

    // Set loading state
    setTooltipLoading(prev => ({ ...prev, [experimentId]: true }))

    try {
      // Get experiment
      const experiment = await experimentService.get(experimentId)
      if (!experiment) {
        setTooltipDataCache(prev => ({ ...prev, [experimentId]: null }))
        return null
      }

      // Get dataset version
      let datasetName = '未知数据集'
      let datasetVersion = '未知版本'
      try {
        const datasetVersionData = await datasetService.getVersion(
          experiment.dataset_version_id,
          experiment.dataset_version_id
        )
        if (datasetVersionData?.version) {
          datasetVersion = datasetVersionData.version.version
        }
        if (datasetVersionData?.dataset) {
          datasetName = datasetVersionData.dataset.name
        }
      } catch (error) {
        console.error('Failed to load dataset version:', error)
      }

      // Get evaluation target info
      let evaluationTarget = {
        type: 'none',
        name: '无',
        version: ''
      }
      try {
        const evalTargetConfig = experiment.evaluation_target_config || {}
        if (evalTargetConfig.type === 'model_set' && evalTargetConfig.model_set_id) {
          const modelSet = await modelSetService.getById(evalTargetConfig.model_set_id)
          evaluationTarget = {
            type: 'model_set',
            name: modelSet.name || '未知模型集',
            version: ''
          }
        } else if (evalTargetConfig.type === 'prompt' && evalTargetConfig.prompt_id && evalTargetConfig.version) {
          const prompt = await promptService.get(evalTargetConfig.prompt_id)
          evaluationTarget = {
            type: 'prompt',
            name: prompt.prompt_basic?.display_name || '未知提示词',
            version: evalTargetConfig.version
          }
        }
      } catch (error) {
        console.error('Failed to load evaluation target:', error)
      }

      // Get evaluators
      const evaluators: ExperimentTooltipData['evaluators'] = []
      if (experiment.evaluator_version_ids && experiment.evaluator_version_ids.length > 0) {
        try {
          const evaluatorPromises = experiment.evaluator_version_ids.map(async (evaluatorVersionId: number) => {
            try {
              const evaluatorVersion = await evaluatorService.getVersion(evaluatorVersionId)
              const evaluator = await evaluatorService.get(evaluatorVersion.evaluator_id)
              return {
                evaluatorVersionId,
                name: evaluator.name || '未知评估器',
                version: evaluatorVersion.version || '未知版本',
                type: evaluator.evaluator_type || 'prompt',
                currentValue: currentEvaluatorId === evaluatorVersionId ? currentEvaluatorValue : undefined,
                color: getExperimentColor(experimentId)
              }
            } catch (error) {
              console.error(`Failed to load evaluator version ${evaluatorVersionId}:`, error)
              return null
            }
          })
          const evaluatorResults = await Promise.all(evaluatorPromises)
          evaluators.push(...evaluatorResults.filter((e): e is ExperimentTooltipData['evaluators'][0] => e !== null))
        } catch (error) {
          console.error('Failed to load evaluators:', error)
        }
      }

      const tooltipData: ExperimentTooltipData = {
        experimentId,
        experimentName: experiment.name || '未知实验',
        groupLabel: getExperimentGroupLabel(experimentId),
        datasetName,
        datasetVersion,
        evaluationTarget,
        evaluators
      }

      // Cache the data
      setTooltipDataCache(prev => ({ ...prev, [experimentId]: tooltipData }))
      return tooltipData
    } catch (error) {
      console.error(`Failed to load tooltip data for experiment ${experimentId}:`, error)
      setTooltipDataCache(prev => ({ ...prev, [experimentId]: null }))
      return null
    } finally {
      setTooltipLoading(prev => {
        const newState = { ...prev }
        delete newState[experimentId]
        return newState
      })
    }
  }

  // ExperimentTooltip component
  const ExperimentTooltip = ({ 
    experimentId, 
    currentEvaluatorValue,
    currentEvaluatorId 
  }: { 
    experimentId: number
    currentEvaluatorValue?: number
    currentEvaluatorId?: number
  }) => {
    const [tooltipData, setTooltipData] = useState<ExperimentTooltipData | null>(
      tooltipDataCache[experimentId] || null
    )
    const [loading, setLoading] = useState(false)

    useEffect(() => {
      // Check cache first
      if (tooltipDataCache[experimentId] !== undefined) {
        setTooltipData(tooltipDataCache[experimentId])
        return
      }

      // Load data if not in cache
      const loadData = async () => {
        setLoading(true)
        const data = await loadExperimentTooltipData(experimentId, currentEvaluatorValue, currentEvaluatorId)
        setTooltipData(data)
        setLoading(false)
      }
      loadData()
    }, [experimentId, currentEvaluatorValue, currentEvaluatorId])

    if (loading) {
      return (
        <div style={{ 
          padding: '12px', 
          minWidth: '200px',
          backgroundColor: '#fff',
          color: '#333'
        }}>
          <Spin size="small" /> 加载中...
        </div>
      )
    }

    if (!tooltipData) {
      return (
        <div style={{ 
          padding: '12px', 
          minWidth: '200px',
          backgroundColor: '#fff',
          color: '#333'
        }}>
          无法加载实验信息
        </div>
      )
    }

    return (
      <div style={{ 
        padding: '12px', 
        minWidth: '280px', 
        maxWidth: '400px',
        backgroundColor: '#fff',
        color: '#333'
      }}>
        {/* Title */}
        <div style={{ 
          fontSize: '14px', 
          fontWeight: 600, 
          marginBottom: '12px',
          color: '#333',
          borderBottom: '1px solid #f0f0f0',
          paddingBottom: '8px'
        }}>
          {tooltipData.groupLabel} - {tooltipData.experimentName}
        </div>

        {/* Evaluators */}
        {tooltipData.evaluators.length > 0 && (
          <div style={{ marginBottom: '12px' }}>
            {tooltipData.evaluators.map((ev) => (
              <div 
                key={ev.evaluatorVersionId}
                style={{ 
                  fontSize: '12px',
                  color: '#333',
                  lineHeight: '20px',
                  marginBottom: '4px'
                }}
              >
                评估器: {ev.name} {ev.version}
              </div>
            ))}
          </div>
        )}

        {/* Evaluation Target */}
        <div style={{ 
          marginBottom: '12px',
          fontSize: '12px',
          color: '#333',
          lineHeight: '20px'
        }}>
          评测对象: {tooltipData.evaluationTarget.name}
          {tooltipData.evaluationTarget.version && ` ${tooltipData.evaluationTarget.version}`}
        </div>

        {/* Dataset */}
        <div style={{ 
          marginBottom: '12px',
          fontSize: '12px',
          color: '#333',
          lineHeight: '20px'
        }}>
          评测集: {tooltipData.datasetName} {tooltipData.datasetVersion}
        </div>
      </div>
    )
  }

  const renderMetricsView = () => {
    if (!comparisonMetrics) {
      return (
        <div className="flex justify-center items-center h-full">
          <Empty description="请先选择实验进行对比" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </div>
      )
    }

    const { evaluator_scores, runtime_metrics } = comparisonMetrics

    // Get evaluator aggregation state (per evaluator)
    const getEvaluatorAggregationState = (evaluatorId: number): 'avg' | 'max' | 'min' | 'sum' | 'count' => {
      const key = `evaluator_${evaluatorId}`
      return evaluatorAggregation[key] || 'avg'
    }

    const setEvaluatorAggregationState = (evaluatorId: number, value: 'avg' | 'max' | 'min' | 'sum' | 'count') => {
      const key = `evaluator_${evaluatorId}`
      setEvaluatorAggregation({
        ...evaluatorAggregation,
        [key]: value
      })
    }

    return (
      <div className="space-y-6">
        {/* Evaluator Scores */}
        <Card 
          title="评估器得分"
          extra={
            <Button
              type="text"
              size="small"
              icon={evaluatorScoresCollapsed ? <DownOutlined /> : <UpOutlined />}
              onClick={() => setEvaluatorScoresCollapsed(!evaluatorScoresCollapsed)}
              style={{ padding: 0, height: 'auto' }}
            />
          }
        >
          {!evaluatorScoresCollapsed && (
            <>
              {(() => {
                // Use all_evaluators if available, otherwise fall back to common_evaluators
                const evaluatorsToShow = evaluator_scores.all_evaluators || evaluator_scores.common_evaluators || []
                
                if (evaluatorsToShow.length > 0) {
                  return (
                    <div className="grid grid-cols-2 gap-4">
                      {evaluatorsToShow.map((ev) => {
                        const evaluatorMetrics = evaluator_scores.comparison_metrics[ev.evaluator_version_id]
                        
                        if (!evaluatorMetrics || evaluatorMetrics.experiments.length === 0) {
                          return (
                            <Card 
                              key={ev.evaluator_version_id} 
                              size="small" 
                              title={
                                <Space>
                                  <span>{ev.name} {ev.version}</span>
                                  {ev.is_common === false && (
                                    <Tag color="orange" size="small">部分实验</Tag>
                                  )}
                                </Space>
                              }
                            >
                              <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                            </Card>
                          )
                        }

                        const aggregation = getEvaluatorAggregationState(ev.evaluator_version_id)
                        const maxValue = aggregation === 'count' ? undefined : 1

                        return (
                          <Card
                            key={ev.evaluator_version_id}
                            size="small"
                            title={
                              <Space>
                                <span>{ev.name} {ev.version}</span>
                                {ev.is_common === false && (
                                  <Tag color="orange" size="small">部分实验</Tag>
                                )}
                                <Select
                                  value={aggregation}
                                  onChange={(value) => setEvaluatorAggregationState(ev.evaluator_version_id, value)}
                                  size="small"
                                  style={{ width: 100, height: '24px' }}
                                  className="compact-select"
                                  dropdownStyle={{ 
                                    maxHeight: '120px', 
                                    zIndex: 1050,
                                    padding: '4px 0'
                                  }}
                                  dropdownClassName="aggregation-select-dropdown"
                                  getPopupContainer={() => document.body}
                                >
                                  <Option value="avg" style={{ padding: '0 12px', lineHeight: '20px', height: '20px', fontSize: '12px' }}>Avg</Option>
                                  <Option value="max" style={{ padding: '0 12px', lineHeight: '20px', height: '20px', fontSize: '12px' }}>Max</Option>
                                  <Option value="min" style={{ padding: '0 12px', lineHeight: '20px', height: '20px', fontSize: '12px' }}>Min</Option>
                                  <Option value="sum" style={{ padding: '0 12px', lineHeight: '20px', height: '20px', fontSize: '12px' }}>Sum</Option>
                                  <Option value="count" style={{ padding: '0 12px', lineHeight: '20px', height: '20px', fontSize: '12px' }}>Count</Option>
                                </Select>
                              </Space>
                            }
                          >
                            <SimpleBarChart
                              data={evaluatorMetrics.experiments.map((exp) => ({
                                name: getExperimentGroupLabel(exp.experiment_id),
                                value: getEvaluatorAggregatedValue(exp, aggregation),
                                experimentId: exp.experiment_id,
                              }))}
                              maxValue={maxValue}
                              getColor={getExperimentColor}
                              currentEvaluatorId={ev.evaluator_version_id}
                            />
                          </Card>
                        )
                      })}
                    </div>
                  )
                } else {
                  return (
                    <Empty description="暂无评估器数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  )
                }
              })()}
            </>
          )}
        </Card>

        {/* Runtime Metrics */}
        <Card 
          title="运行时指标"
          extra={
            <Button
              type="text"
              size="small"
              icon={runtimeMetricsCollapsed ? <DownOutlined /> : <UpOutlined />}
              onClick={() => setRuntimeMetricsCollapsed(!runtimeMetricsCollapsed)}
              style={{ padding: 0, height: 'auto' }}
            />
          }
        >
          {!runtimeMetricsCollapsed && (
            <>
              {Object.values(runtime_metrics).some(
                metric => metric.experiments && metric.experiments.length > 0
              ) ? (
                <div className="grid grid-cols-2 gap-4">
                  {Object.values(runtime_metrics).map((metric) => {
                    const aggregation = runtimeAggregation[metric.metric_name] || 'total'
                    const hasData = metric.experiments && metric.experiments.length > 0

                    if (!hasData) {
                      return (
                        <Card 
                          key={metric.metric_name} 
                          size="small" 
                          title={metric.metric_name}
                        >
                          <Empty 
                            description={
                              <div>
                                <div className="mb-2">暂无数据</div>
                                <div className="text-sm text-gray-500">
                                  该指标暂无数据，可能是实验未生成统计信息
                                </div>
                              </div>
                            }
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                          />
                        </Card>
                      )
                    }

                    const values = metric.experiments.map((exp) => 
                      getRuntimeAggregatedValue(exp, aggregation)
                    )
                    const maxValue = Math.max(...values, 1)
                    
                    return (
                      <Card 
                        key={metric.metric_name} 
                        size="small" 
                        title={
                          <Space>
                            <span>{metric.metric_name}</span>
                            <Select
                              value={aggregation}
                              onChange={(value) => setRuntimeAggregation({
                                ...runtimeAggregation,
                                [metric.metric_name]: value
                              })}
                              size="small"
                              style={{ width: 80, height: '24px' }}
                              className="compact-select"
                              dropdownStyle={{ 
                                maxHeight: '100px', 
                                zIndex: 1050,
                                padding: '4px 0'
                              }}
                              dropdownClassName="aggregation-select-dropdown"
                              getPopupContainer={() => document.body}
                            >
                              <Option value="total" style={{ padding: '0 12px', lineHeight: '20px', height: '20px', fontSize: '12px' }}>Total</Option>
                              <Option value="avg" style={{ padding: '0 12px', lineHeight: '20px', height: '20px', fontSize: '12px' }}>Avg</Option>
                              <Option value="max" style={{ padding: '0 12px', lineHeight: '20px', height: '20px', fontSize: '12px' }}>Max</Option>
                              <Option value="min" style={{ padding: '0 12px', lineHeight: '20px', height: '20px', fontSize: '12px' }}>Min</Option>
                            </Select>
                          </Space>
                        }
                      >
                        <SimpleBarChart
                          data={metric.experiments.map((exp) => ({
                            name: getExperimentGroupLabel(exp.experiment_id),
                            value: getRuntimeAggregatedValue(exp, aggregation),
                            experimentId: exp.experiment_id,
                          }))}
                          maxValue={maxValue}
                          getColor={getExperimentColor}
                        />
                      </Card>
                    )
                  })}
                </div>
              ) : (
                <Empty 
                  description={
                    <div>
                      <div className="mb-2">暂无数据</div>
                      <div className="text-sm text-gray-500">
                        实验完成后,再刷新重试
                      </div>
                    </div>
                  }
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              )}
            </>
          )}
        </Card>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full" style={{ height: '100%' }}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b" style={{ background: '#fff' }}>
          <div className="flex items-center gap-4">
            <span className="text-[20px] font-medium leading-6">实验比对效果看版</span>
          </div>
          <Space>
            {baselineExperimentId && (
              <Select
                value={baselineExperimentId}
                onChange={handleBaselineChange}
                placeholder="基准"
                style={{ width: 200 }}
                showSearch
                filterOption={(input, option) =>
                  (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
                }
              >
                {[baselineExperimentId, ...comparisonExperimentIds].map((expId) => {
                  const exp = experiments.find(e => e.id === expId)
                  return exp ? (
                    <Option key={exp.id} value={exp.id}>
                      {exp.name}
                    </Option>
                  ) : null
                })}
              </Select>
            )}
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleOpenSelectModal}
            >
              添加对比实验
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} />
            <Button icon={<DownloadOutlined />} />
            {baselineExperimentId && (
              <Button icon={<ClearOutlined />} onClick={handleClearComparison}>
                清空
              </Button>
            )}
          </Space>
        </div>

        {/* Tabs */}
        <div style={{ padding: '0 16px', borderBottom: '1px solid #f0f0f0', background: '#fff' }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              { key: 'data-details', label: '数据明细' },
              { key: 'metrics', label: '指标统计' },
            ]}
          />
        </div>

        {/* Content */}
        <div style={{ padding: '16px', overflow: 'auto', height: '100%' }}>
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <Spin size="large" />
            </div>
          ) : activeTab === 'data-details' ? (
              <div className="h-full flex flex-col">
                {comparisonDetails.length > 0 ? (
                  <>
                    <Table
                      columns={dataDetailsColumns}
                      dataSource={comparisonDetails.slice((currentPage - 1) * pageSize, currentPage * pageSize)}
                      rowKey="dataset_item_id"
                      pagination={false}
                      scroll={{ x: 'max-content', y: 'calc(100vh - 300px)' }}
                    />
                    <div className="flex justify-end mt-4">
                    <Pagination
                      current={currentPage}
                      pageSize={pageSize}
                      total={comparisonDetails.length}
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
                      pageSizeOptions={['10', '20', '50', '100']}
                      locale={{
                        items_per_page: ' / 页',
                      }}
                    />
                    </div>
                  </>
                ) : (
                  <div className="flex justify-center items-center h-full">
                    <Empty description="请先选择实验进行对比" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  </div>
                )}
              </div>
            ) : (
              renderMetricsView()
            )}
        </div>

        {/* Select Experiments Modal */}
        <Modal
          title={selectStep === 'experiments' ? '选择对比实验' : '选择基准实验'}
          open={selectModalVisible}
          width={800}
          onCancel={() => {
            setSelectModalVisible(false)
            setSelectStep('experiments')
            setTempSelectedExperimentIds([])
            setTempBaselineExperimentId(null)
          }}
          footer={
            selectStep === 'experiments' ? (
              <Space>
                <Button onClick={() => setSelectModalVisible(false)}>取消</Button>
                <Button
                  type="primary"
                  onClick={handleSelectExperimentsNext}
                  disabled={tempSelectedExperimentIds.length < 2}
                >
                  下一步
                </Button>
              </Space>
            ) : (
              <Space>
                <Button onClick={() => setSelectStep('experiments')}>上一步</Button>
                <Button onClick={() => setSelectModalVisible(false)}>取消</Button>
                <Button
                  type="primary"
                  onClick={handleConfirmComparison}
                  disabled={!tempBaselineExperimentId}
                >
                  确认对比
                </Button>
              </Space>
            )
          }
        >
          {selectStep === 'experiments' ? (
            <Layout style={{ height: '500px' }}>
              <Sider width={250} style={{ background: '#fff', borderRight: '1px solid #f0f0f0' }}>
                <div style={{ padding: '16px' }}>
                  <div style={{ marginBottom: '8px', fontWeight: 'bold' }}>分组</div>
                  <style>{`
                    /* 树容器宽度约束 */
                    .comparison-experiment-group-tree {
                      max-width: 100% !important;
                      overflow: hidden !important;
                    }
                    /* 紧凑的树形结构样式 */
                    .comparison-experiment-group-tree .ant-tree-treenode {
                      padding: 2px 0 !important;
                      max-width: 100% !important;
                      box-sizing: border-box !important;
                    }
                    .comparison-experiment-group-tree .ant-tree-switcher {
                      width: 16px !important;
                      height: 24px !important;
                      line-height: 24px !important;
                    }
                    .comparison-experiment-group-tree .ant-tree-iconEle {
                      width: 16px !important;
                      margin-right: 4px !important;
                    }
                    .comparison-experiment-group-tree .ant-tree-node-content-wrapper {
                      display: flex !important;
                      align-items: center !important;
                      flex: 1 !important;
                      min-width: 0 !important;
                      max-width: 100% !important;
                      padding: 0 4px !important;
                      overflow: hidden !important;
                    }
                    .comparison-experiment-group-tree .ant-tree-title {
                      flex: 1 !important;
                      min-width: 0 !important;
                      max-width: 100% !important;
                      overflow: hidden !important;
                    }
                    .comparison-experiment-group-tree .ant-tree-indent-unit {
                      width: 16px !important;
                    }
                    /* 分组名称样式 */
                    .comparison-group-name {
                      flex: 1 !important;
                      min-width: 0 !important;
                      max-width: 100% !important;
                      overflow: hidden !important;
                      text-overflow: ellipsis !important;
                      white-space: nowrap !important;
                      line-height: 24px !important;
                    }
                  `}</style>
                  <Tree
                    showIcon
                    defaultExpandAll
                    selectedKeys={selectedGroupId === null ? ['root'] : [`group-${selectedGroupId}`]}
                    onSelect={handleTreeSelect}
                    treeData={treeData}
                    className="comparison-experiment-group-tree"
                    style={{
                      fontSize: '14px',
                      width: '100%'
                    }}
                    titleRender={(node: DataNode) => (
                      <Tooltip title={String(node.title)} placement="right">
                        <span className="comparison-group-name">{String(node.title)}</span>
                      </Tooltip>
                    )}
        />
      </div>
              </Sider>
              <Content style={{ padding: '16px', overflow: 'auto' }}>
                <Input
                  placeholder="搜索实验名称"
                  prefix={<SearchOutlined />}
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  style={{ marginBottom: '16px' }}
                  allowClear
                />
                <div style={{ maxHeight: '400px', overflow: 'auto' }}>
                  {getFilteredExperiments().map((exp) => (
                    <div
                      key={exp.id}
                      style={{
                        padding: '8px',
                        marginBottom: '8px',
                        border: '1px solid #f0f0f0',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        backgroundColor: tempSelectedExperimentIds.includes(exp.id) ? '#e6f7ff' : '#fff',
                      }}
                      onClick={() => {
                        if (tempSelectedExperimentIds.includes(exp.id)) {
                          setTempSelectedExperimentIds(tempSelectedExperimentIds.filter(id => id !== exp.id))
                        } else {
                          setTempSelectedExperimentIds([...tempSelectedExperimentIds, exp.id])
                        }
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <input
                          type="checkbox"
                          checked={tempSelectedExperimentIds.includes(exp.id)}
                          onChange={() => {}}
                        />
                        <span style={{ fontWeight: 'bold' }}>{exp.name}</span>
                        <Tag color={exp.status === 'completed' ? 'success' : 'default'}>
                          {exp.status}
                        </Tag>
                      </div>
                      {exp.description && (
                        <div style={{ marginTop: '4px', color: '#666', fontSize: '12px' }}>
                          {exp.description}
                        </div>
                      )}
                    </div>
                  ))}
                  {getFilteredExperiments().length === 0 && (
                    <Empty description="没有找到实验" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  )}
                </div>
                <div style={{ marginTop: '16px', color: '#666', fontSize: '12px' }}>
                  已选择 {tempSelectedExperimentIds.length} 个实验（至少需要2个）
                </div>
              </Content>
            </Layout>
          ) : (
            <div style={{ padding: '16px' }}>
              <div style={{ marginBottom: '16px' }}>请从已选择的实验中选择一个作为基准：</div>
              <div style={{ maxHeight: '400px', overflow: 'auto' }}>
                {tempSelectedExperimentIds.map((expId) => {
                  const exp = experiments.find(e => e.id === expId)
                  if (!exp) return null
                  return (
                    <div
                      key={exp.id}
                      style={{
                        padding: '12px',
                        marginBottom: '8px',
                        border: '1px solid #f0f0f0',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        backgroundColor: tempBaselineExperimentId === exp.id ? '#e6f7ff' : '#fff',
                      }}
                      onClick={() => setTempBaselineExperimentId(exp.id)}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <input
                          type="radio"
                          checked={tempBaselineExperimentId === exp.id}
                          onChange={() => setTempBaselineExperimentId(exp.id)}
                        />
                        <span style={{ fontWeight: 'bold' }}>{exp.name}</span>
                        <Tag color={exp.status === 'completed' ? 'success' : 'default'}>
                          {exp.status}
                        </Tag>
                      </div>
                      {exp.description && (
                        <div style={{ marginTop: '4px', color: '#666', fontSize: '12px' }}>
                          {exp.description}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </Modal>
    </div>
  )
}
