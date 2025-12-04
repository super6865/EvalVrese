import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Input, Space, Tag, Select } from 'antd'
import { CrudListPage } from '../../components/crud'
import { evaluatorRecordService } from '../../services/evaluatorRecordService'
import type { EvaluatorRecord, EvaluatorRunStatus } from '../../types/evaluator'
import type { ColumnsType } from 'antd/es/table'
import { formatTimestamp } from '../../utils/dateUtils'

export default function EvaluatorRecordListPage() {
  const navigate = useNavigate()
  const [filters, setFilters] = useState({
    evaluator_version_id: undefined as number | undefined,
    experiment_id: undefined as number | undefined,
    status: undefined as EvaluatorRunStatus | undefined,
  })

  const getStatusTag = (status: EvaluatorRunStatus) => {
    const statusMap = {
      success: { color: 'green', text: '成功' },
      fail: { color: 'red', text: '失败' },
      unknown: { color: 'default', text: '未知' },
    }
    const config = statusMap[status] || { color: 'default', text: status }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const columns: ColumnsType<EvaluatorRecord> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '评估器版本ID',
      dataIndex: 'evaluator_version_id',
      key: 'evaluator_version_id',
      width: 120,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: EvaluatorRunStatus) => getStatusTag(status),
    },
    {
      title: '评分',
      key: 'score',
      width: 100,
      render: (_: any, record: EvaluatorRecord) => {
        const score = record.output_data?.evaluator_result?.score ??
                     record.output_data?.evaluator_result?.correction?.score
        return score !== null && score !== undefined ? (
          <Tag color={score >= 0.8 ? 'green' : score >= 0.5 ? 'orange' : 'red'}>
            {score}
          </Tag>
        ) : '-'
      },
    },
    {
      title: '实验ID',
      dataIndex: 'experiment_id',
      key: 'experiment_id',
      width: 100,
      render: (id: number) => id || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => formatTimestamp(time),
    },
  ]

  return (
    <CrudListPage<EvaluatorRecord>
      pageTitle="评估器记录"
      pageSizeStorageKey="evaluator_record_list_page_size"
      columns={columns}
      loadData={async (params) => {
        const skip = (params.page_number - 1) * params.page_size
        const response = await evaluatorRecordService.list({
          evaluator_version_id: filters.evaluator_version_id,
          experiment_id: filters.experiment_id,
          status: filters.status,
          skip,
          limit: params.page_size,
        })
        return {
          items: response.records || [],
          total: response.total || 0,
        }
      }}
      itemsKey="items"
      totalKey="total"
      viewPath={(id) => `/evaluator-records/${id}`}
      filters={(searchText, setSearchText) => (
        <Space>
          <Input
            placeholder="评估器版本ID"
            type="number"
            value={filters.evaluator_version_id}
            onChange={(e) => setFilters({ ...filters, evaluator_version_id: e.target.value ? Number(e.target.value) : undefined })}
            style={{ width: 150 }}
          />
          <Input
            placeholder="实验ID"
            type="number"
            value={filters.experiment_id}
            onChange={(e) => setFilters({ ...filters, experiment_id: e.target.value ? Number(e.target.value) : undefined })}
            style={{ width: 150 }}
          />
          <Select
            placeholder="状态"
            allowClear
            value={filters.status}
            onChange={(value) => setFilters({ ...filters, status: value })}
            style={{ width: 120 }}
          >
            <Select.Option value="success">成功</Select.Option>
            <Select.Option value="fail">失败</Select.Option>
            <Select.Option value="unknown">未知</Select.Option>
          </Select>
        </Space>
      )}
      additionalFilters={filters}
      onFilterChange={(newFilters) => {
        setFilters({
          evaluator_version_id: newFilters.evaluator_version_id,
          experiment_id: newFilters.experiment_id,
          status: newFilters.status,
        })
      }}
    />
  )
}

