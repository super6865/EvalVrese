import { useState, useEffect } from 'react'
import { Card, Table, Tag, Spin, message } from 'antd'
import { experimentService } from '../../../services/experimentService'
import type { ColumnsType } from 'antd/es/table'

interface AggregateResult {
  evaluator_version_id: number
  name?: string
  version?: string
  average_score: number | null
  total_count: number
  aggregator_results: Array<{
    aggregator_type: string
    data: any
  }>
}

interface AggregateResultsPanelProps {
  experimentId: number
  runId?: number
}

export default function AggregateResultsPanel({ experimentId, runId }: AggregateResultsPanelProps) {
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<AggregateResult[]>([])

  useEffect(() => {
    loadAggregateResults()
  }, [experimentId, runId])

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

  const columns: ColumnsType<AggregateResult> = [
    {
      title: '评估器',
      key: 'name',
      render: (_, record) => (
        <div>
          <div>{record.name || `评估器 ${record.evaluator_version_id}`}</div>
          {record.version && (
            <div className="text-xs text-gray-500">版本: {record.version}</div>
          )}
        </div>
      ),
    },
    {
      title: '平均分',
      dataIndex: 'average_score',
      key: 'average_score',
      render: (score: number | null) => {
        if (score === null) return '-'
        const color = score >= 0.8 ? 'green' : score >= 0.5 ? 'orange' : 'red'
        return <Tag color={color}>{score.toFixed(2)}</Tag>
      },
    },
    {
      title: '样本数',
      dataIndex: 'total_count',
      key: 'total_count',
    },
    {
      title: '最大值',
      key: 'max',
      render: (_, record) => {
        const maxResult = record.aggregator_results.find(
          (r) => r.aggregator_type === 'max'
        )
        return maxResult ? maxResult.data.value.toFixed(2) : '-'
      },
    },
    {
      title: '最小值',
      key: 'min',
      render: (_, record) => {
        const minResult = record.aggregator_results.find(
          (r) => r.aggregator_type === 'min'
        )
        return minResult ? minResult.data.value.toFixed(2) : '-'
      },
    },
    {
      title: '总和',
      key: 'sum',
      render: (_, record) => {
        const sumResult = record.aggregator_results.find(
          (r) => r.aggregator_type === 'sum'
        )
        return sumResult ? sumResult.data.value.toFixed(2) : '-'
      },
    },
  ]

  return (
    <Card title="聚合结果" className="mb-4">
      <Spin spinning={loading}>
        <Table
          columns={columns}
          dataSource={results}
          rowKey="evaluator_version_id"
          pagination={false}
        />
      </Spin>
    </Card>
  )
}

