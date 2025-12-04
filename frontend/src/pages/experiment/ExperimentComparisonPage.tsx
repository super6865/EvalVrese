import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Select, Table, Space, message, Spin, Tag } from 'antd'
import { ArrowLeftOutlined, SwapOutlined } from '@ant-design/icons'
import { experimentService } from '../../services/experimentService'
import type { ColumnsType } from 'antd/es/table'

const { Option } = Select

interface Experiment {
  id: number
  name: string
  status: string
}

export default function ExperimentComparisonPage() {
  const navigate = useNavigate()
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [selectedExperimentIds, setSelectedExperimentIds] = useState<number[]>([])
  const [loading, setLoading] = useState(false)
  const [comparisonData, setComparisonData] = useState<any>(null)
  const [summaryData, setSummaryData] = useState<any>(null)

  useEffect(() => {
    loadExperiments()
  }, [])

  const loadExperiments = async () => {
    try {
      const response = await experimentService.list(0, 1000)
      setExperiments(response.experiments || [])
    } catch (error) {
      message.error('加载实验列表失败')
    }
  }

  const handleCompare = async () => {
    if (selectedExperimentIds.length < 2) {
      message.warning('请至少选择2个实验进行对比')
      return
    }

    setLoading(true)
    try {
      const [comparison, summary] = await Promise.all([
        experimentService.compareExperiments(selectedExperimentIds),
        experimentService.getComparisonSummary(selectedExperimentIds),
      ])
      setComparisonData(comparison)
      setSummaryData(summary)
    } catch (error) {
      message.error('对比失败')
    } finally {
      setLoading(false)
    }
  }

  const summaryColumns: ColumnsType<any> = [
    {
      title: '实验名称',
      dataIndex: 'experiment_name',
      key: 'experiment_name',
    },
    {
      title: '总样本数',
      dataIndex: 'total_count',
      key: 'total_count',
    },
    {
      title: '成功数',
      dataIndex: 'success_count',
      key: 'success_count',
    },
    {
      title: '失败数',
      dataIndex: 'failure_count',
      key: 'failure_count',
    },
    {
      title: '成功率',
      key: 'success_rate',
      render: (_: any, record: any) => (
        <Tag color={record.success_rate >= 80 ? 'green' : record.success_rate >= 50 ? 'orange' : 'red'}>
          {record.success_rate.toFixed(1)}%
        </Tag>
      ),
    },
  ]

  const buildComparisonColumns = (): ColumnsType<any> => {
    if (!comparisonData) return []

    const columns: ColumnsType<any> = [
      {
        title: '评估器',
        key: 'evaluator',
        fixed: 'left',
        width: 200,
        render: (_: any, record: any) => (
          <div>
            <div className="font-semibold">{record.evaluator.name}</div>
            <div className="text-xs text-gray-500">版本: {record.evaluator.version}</div>
          </div>
        ),
      },
    ]

    // Add columns for each experiment
    comparisonData.experiments.forEach((exp: any) => {
      columns.push({
        title: exp.experiment_name,
        key: `exp_${exp.experiment_id}`,
        children: [
          {
            title: '平均分',
            key: `exp_${exp.experiment_id}_avg`,
            render: (_: any, record: any) => {
              const expData = record.experiments.find(
                (e: any) => e.experiment_id === exp.experiment_id
              )
              if (!expData) return '-'
              const score = expData.average_score
              if (score === null || score === undefined) return '-'
              const color = score >= 0.8 ? 'green' : score >= 0.5 ? 'orange' : 'red'
              return <Tag color={color}>{score.toFixed(2)}</Tag>
            },
          },
          {
            title: '最大值',
            key: `exp_${exp.experiment_id}_max`,
            render: (_: any, record: any) => {
              const expData = record.experiments.find(
                (e: any) => e.experiment_id === exp.experiment_id
              )
              return expData?.max_score !== null && expData?.max_score !== undefined
                ? expData.max_score.toFixed(2)
                : '-'
            },
          },
          {
            title: '最小值',
            key: `exp_${exp.experiment_id}_min`,
            render: (_: any, record: any) => {
              const expData = record.experiments.find(
                (e: any) => e.experiment_id === exp.experiment_id
              )
              return expData?.min_score !== null && expData?.min_score !== undefined
                ? expData.min_score.toFixed(2)
                : '-'
            },
          },
          {
            title: '样本数',
            key: `exp_${exp.experiment_id}_count`,
            render: (_: any, record: any) => {
              const expData = record.experiments.find(
                (e: any) => e.experiment_id === exp.experiment_id
              )
              return expData?.total_count || 0
            },
          },
        ],
      })
    })

    return columns
  }

  const comparisonTableData = comparisonData
    ? Object.values(comparisonData.comparison_metrics).map((metric: any) => ({
        ...metric,
        key: metric.evaluator.evaluator_version_id,
      }))
    : []

  return (
    <div className="h-full flex flex-col p-4">
      <Card className="mb-4">
        <div className="flex items-center justify-between mb-4">
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/experiments')}>
              返回
            </Button>
            <h2 className="text-xl font-semibold m-0">实验对比</h2>
          </Space>
        </div>

        <Space direction="vertical" className="w-full">
          <div>
            <label className="block mb-2">选择要对比的实验（至少2个）:</label>
            <Select
              mode="multiple"
              style={{ width: '100%' }}
              placeholder="选择实验"
              value={selectedExperimentIds}
              onChange={setSelectedExperimentIds}
              showSearch
              filterOption={(input, option) =>
                (option?.children as unknown as string)
                  ?.toLowerCase()
                  .includes(input.toLowerCase())
              }
            >
              {experiments.map((exp) => (
                <Option key={exp.id} value={exp.id}>
                  {exp.name} (ID: {exp.id})
                </Option>
              ))}
            </Select>
          </div>
          <Button
            type="primary"
            icon={<SwapOutlined />}
            onClick={handleCompare}
            disabled={selectedExperimentIds.length < 2}
          >
            开始对比
          </Button>
        </Space>
      </Card>

      {loading && (
        <div className="flex justify-center items-center h-64">
          <Spin size="large" />
        </div>
      )}

      {summaryData && !loading && (
        <Card title="对比摘要" className="mb-4">
          <Table
            columns={summaryColumns}
            dataSource={summaryData.experiments}
            rowKey="experiment_id"
            pagination={false}
          />
        </Card>
      )}

      {comparisonData && !loading && (
        <Card title="详细对比" className="flex-1 overflow-hidden">
          <Table
            columns={buildComparisonColumns()}
            dataSource={comparisonTableData}
            rowKey="key"
            pagination={false}
            scroll={{ x: 'max-content' }}
          />
        </Card>
      )}
    </div>
  )
}

