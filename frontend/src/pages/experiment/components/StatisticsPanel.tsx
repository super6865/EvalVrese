import { useState, useEffect } from 'react'
import { Card, Statistic, Row, Col, Spin, message, Tag } from 'antd'
import { experimentService } from '../../../services/experimentService'

interface Statistics {
  experiment_id: number
  total_count: number
  success_count: number
  failure_count: number
  pending_count: number
  evaluator_aggregate_results: any[]
  token_usage: {
    input_tokens: number
    output_tokens: number
  }
}

interface StatisticsPanelProps {
  experimentId: number
  runId?: number
}

export default function StatisticsPanel({ experimentId, runId }: StatisticsPanelProps) {
  const [loading, setLoading] = useState(false)
  const [statistics, setStatistics] = useState<Statistics | null>(null)

  useEffect(() => {
    loadStatistics()
  }, [experimentId, runId])

  const loadStatistics = async () => {
    setLoading(true)
    try {
      const data = await experimentService.getStatistics(experimentId, runId)
      setStatistics(data)
    } catch (error) {
      message.error('加载统计信息失败')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Card title="统计信息" className="mb-4">
        <Spin />
      </Card>
    )
  }

  if (!statistics) {
    return null
  }

  const successRate =
    statistics.total_count > 0
      ? ((statistics.success_count / statistics.total_count) * 100).toFixed(1)
      : '0'

  return (
    <Card title="统计信息" className="mb-4">
      <Row gutter={16}>
        <Col span={5}>
          <Statistic title="总样本数" value={statistics.total_count} />
        </Col>
        <Col span={5}>
          <Statistic
            title="成功数"
            value={statistics.success_count}
            valueStyle={{ color: '#3f8600' }}
          />
        </Col>
        <Col span={5}>
          <Statistic
            title="失败数"
            value={statistics.failure_count}
            valueStyle={{ color: '#cf1322' }}
          />
        </Col>
        <Col span={5}>
          <Statistic
            title="待处理"
            value={statistics.pending_count}
            valueStyle={{ color: '#1890ff' }}
          />
        </Col>
        <Col span={4}>
          <Statistic
            title="成功率"
            value={successRate}
            suffix="%"
            valueStyle={{ color: '#3f8600' }}
          />
        </Col>
      </Row>
    </Card>
  )
}

