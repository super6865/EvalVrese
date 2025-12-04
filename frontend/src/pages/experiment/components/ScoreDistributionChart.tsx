import { useState, useEffect } from 'react'
import { Card, Spin, message, Select, Table, Progress } from 'antd'
import { experimentService } from '../../../services/experimentService'
import type { ColumnsType } from 'antd/es/table'

interface DistributionItem {
  score_range: string
  count: number
  percentage: number
}

interface AggregateResult {
  evaluator_version_id: number
  name?: string
  version?: string
  aggregator_results: Array<{
    aggregator_type: string
    data: any
  }>
}

interface ScoreDistributionChartProps {
  experimentId: number
  runId?: number
}

export default function ScoreDistributionChart({
  experimentId,
  runId,
}: ScoreDistributionChartProps) {
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<AggregateResult[]>([])
  const [selectedEvaluator, setSelectedEvaluator] = useState<number | undefined>()

  useEffect(() => {
    loadAggregateResults()
  }, [experimentId, runId])

  useEffect(() => {
    if (results.length > 0 && !selectedEvaluator) {
      setSelectedEvaluator(results[0].evaluator_version_id)
    }
  }, [results])

  const loadAggregateResults = async () => {
    setLoading(true)
    try {
      const response = await experimentService.getAggregateResults(experimentId, runId)
      setResults(response.aggregate_results || [])
    } catch (error) {
      message.error('加载聚合结果失败')
    } finally {
      setLoading(false)
    }
  }

  const getDistributionData = (): DistributionItem[] => {
    if (!selectedEvaluator) return []

    const result = results.find(
      (r) => r.evaluator_version_id === selectedEvaluator
    )
    if (!result) return []

    const distResult = result.aggregator_results.find(
      (r) => r.aggregator_type === 'distribution'
    )
    if (!distResult) return []

    return distResult.data.distribution_items || []
  }

  const distributionData = getDistributionData()

  const columns: ColumnsType<DistributionItem> = [
    {
      title: '得分区间',
      dataIndex: 'score_range',
      key: 'score_range',
    },
    {
      title: '数量',
      dataIndex: 'count',
      key: 'count',
    },
    {
      title: '占比',
      dataIndex: 'percentage',
      key: 'percentage',
      render: (percentage: number) => (
        <div>
          <Progress
            percent={percentage}
            size="small"
            showInfo={false}
            strokeColor="#1890ff"
          />
          <span className="ml-2">{percentage}%</span>
        </div>
      ),
    },
  ]

  const selectedResult = results.find(
    (r) => r.evaluator_version_id === selectedEvaluator
  )

  return (
    <Card
      title="得分分布"
      className="mb-4"
      extra={
        <Select
          value={selectedEvaluator}
          onChange={setSelectedEvaluator}
          style={{ width: 200 }}
          placeholder="选择评估器"
        >
          {results.map((r) => (
            <Select.Option key={r.evaluator_version_id} value={r.evaluator_version_id}>
              {r.name || `评估器 ${r.evaluator_version_id}`}
            </Select.Option>
          ))}
        </Select>
      }
    >
      <Spin spinning={loading}>
        {distributionData.length > 0 ? (
          <Table
            columns={columns}
            dataSource={distributionData}
            rowKey="score_range"
            pagination={false}
            size="small"
          />
        ) : (
          <div className="text-center text-gray-400 py-8">
            {selectedResult
              ? '暂无分布数据'
              : '请选择评估器查看得分分布'}
          </div>
        )}
      </Spin>
    </Card>
  )
}

