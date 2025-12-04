import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Input, Space, message, Select, DatePicker } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { CrudListPage } from '../../components/crud'
import { observabilityService } from '../../services/observabilityService'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { formatTimestamp } from '../../utils/dateUtils'

const { RangePicker } = DatePicker

interface Trace {
  trace_id: string
  service_name: string
  operation_name: string
  start_time: string
  end_time?: string
  duration_ms?: number
  status_code?: string
}

export default function ObservabilityListPage() {
  const navigate = useNavigate()
  const [searchTraceId, setSearchTraceId] = useState('')
  const [serviceFilter, setServiceFilter] = useState<string | undefined>()
  const [experimentIdFilter, setExperimentIdFilter] = useState<number | undefined>()
  const [runIdFilter, setRunIdFilter] = useState<number | undefined>()
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
  const [traces, setTraces] = useState<Trace[]>([])

  const handleSearchTraceId = async (traceId: string) => {
    if (!traceId) {
      return
    }
    try {
      const trace = await observabilityService.getTrace(traceId)
      if (trace && trace.trace) {
        setTraces([trace.trace])
      } else {
        setTraces([])
        message.warning('未找到Trace')
      }
    } catch (error) {
      message.error('查询Trace失败')
    }
  }

  const uniqueServices = useMemo(() => {
    const services = new Set(traces.map((t) => t.service_name).filter(Boolean))
    return Array.from(services)
  }, [traces])

  const columns: ColumnsType<Trace> = [
    {
      title: 'Trace ID',
      dataIndex: 'trace_id',
      key: 'trace_id',
      ellipsis: true,
      render: (text: string) => (
        <Button
          type="link"
          onClick={() => navigate(`/observability/traces/${text}`)}
          className="p-0 font-mono text-xs"
        >
          {text}
        </Button>
      ),
    },
    {
      title: '服务名',
      dataIndex: 'service_name',
      key: 'service_name',
      width: 150,
    },
    {
      title: '操作名',
      dataIndex: 'operation_name',
      key: 'operation_name',
      width: 200,
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 180,
      sorter: (a, b) =>
        new Date(a.start_time).getTime() - new Date(b.start_time).getTime(),
      render: (text: string) => formatTimestamp(text),
    },
    {
      title: '持续时间(ms)',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      width: 120,
      render: (ms: number) => (ms ? `${ms.toFixed(2)}ms` : '-'),
    },
    {
      title: '状态',
      dataIndex: 'status_code',
      key: 'status_code',
      width: 100,
      render: (code: string) => code || '-',
    },
  ]

  return (
    <CrudListPage<Trace>
      pageTitle="链路追踪"
      pageSizeStorageKey="trace_list_page_size"
      rowKey="trace_id"
      columns={columns}
      loadData={async (params) => {
        if (experimentIdFilter) {
          const response = await observabilityService.getExperimentTraces(experimentIdFilter, runIdFilter)
          return {
            items: response.traces || [],
            total: response.total || 0,
          }
        } else {
          const apiParams: any = {
            skip: (params.page_number - 1) * params.page_size,
            limit: params.page_size,
          }
          if (serviceFilter) {
            apiParams.service_name = serviceFilter
          }
          if (dateRange) {
            apiParams.start_time = dateRange[0].toISOString()
            apiParams.end_time = dateRange[1].toISOString()
          }
          const response = await observabilityService.listTraces(apiParams)
          return {
            items: response.traces || [],
            total: response.total || 0,
          }
        }
      }}
      itemsKey="items"
      totalKey="total"
      viewPath={(traceId) => `/observability/traces/${traceId}`}
      filters={(searchText, setSearchText) => (
        <Space wrap>
          <Input
            placeholder="搜索Trace ID"
            prefix={<SearchOutlined />}
            value={searchTraceId}
            onChange={(e) => {
              setSearchTraceId(e.target.value)
              if (!e.target.value) {
                setSearchText('')
              }
            }}
            onPressEnter={() => handleSearchTraceId(searchTraceId)}
            allowClear
            style={{ width: 300 }}
          />
          <Input
            type="number"
            placeholder="实验ID"
            value={experimentIdFilter}
            onChange={(e) => setExperimentIdFilter(e.target.value ? Number(e.target.value) : undefined)}
            allowClear
            style={{ width: 120 }}
          />
          <Input
            type="number"
            placeholder="运行ID"
            value={runIdFilter}
            onChange={(e) => setRunIdFilter(e.target.value ? Number(e.target.value) : undefined)}
            allowClear
            style={{ width: 120 }}
            disabled={!experimentIdFilter}
          />
          <Select
            placeholder="筛选服务"
            allowClear
            value={serviceFilter}
            onChange={setServiceFilter}
            style={{ width: 200 }}
            disabled={!!experimentIdFilter}
          >
            {uniqueServices.map((service) => (
              <Select.Option key={service} value={service}>
                {service}
              </Select.Option>
            ))}
          </Select>
          <RangePicker
            showTime
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
            disabled={!!experimentIdFilter}
          />
        </Space>
      )}
      additionalFilters={{
        service_name: serviceFilter,
        experiment_id: experimentIdFilter,
        run_id: runIdFilter,
        start_time: dateRange?.[0]?.toISOString(),
        end_time: dateRange?.[1]?.toISOString(),
      }}
      onLoadSuccess={(data) => {
        if (!searchTraceId) {
          setTraces(data)
        }
      }}
    />
  )
}

