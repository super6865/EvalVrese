import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Descriptions, Tag, Button, Space, message, Modal, Form, Input, InputNumber } from 'antd'
import { ArrowLeftOutlined, EditOutlined } from '@ant-design/icons'
import { evaluatorRecordService } from '../../services/evaluatorRecordService'
import type { EvaluatorRecord } from '../../types/evaluator'
import { formatTimestamp } from '../../utils/dateUtils'

const { TextArea } = Input

export default function EvaluatorRecordDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [record, setRecord] = useState<EvaluatorRecord | null>(null)
  const [loading, setLoading] = useState(false)
  const [correctModalVisible, setCorrectModalVisible] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    if (id) {
      loadRecord()
    }
  }, [id])

  const loadRecord = async () => {
    if (!id) return
    setLoading(true)
    try {
      const data = await evaluatorRecordService.get(Number(id))
      setRecord(data)
    } catch (error) {
      message.error('加载记录失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCorrect = async (values: { score?: number; explain?: string }) => {
    if (!id) return
    try {
      await evaluatorRecordService.correct(Number(id), values, 'current_user')
      message.success('修正成功')
      setCorrectModalVisible(false)
      loadRecord()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '修正失败')
    }
  }

  if (loading && !record) {
    return <div>加载中...</div>
  }

  if (!record) {
    return <div>记录不存在</div>
  }

  const score = record.output_data?.evaluator_result?.score ??
                record.output_data?.evaluator_result?.correction?.score
  const reasoning = record.output_data?.evaluator_result?.reasoning ??
                    record.output_data?.evaluator_result?.correction?.explain

  return (
    <div className="h-full flex flex-col">
      <Card className="mb-4">
        <div className="flex items-center justify-between mb-4">
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/evaluator-records')}>
              返回
            </Button>
            <h2 className="text-xl font-semibold m-0">评估器记录 #{record.id}</h2>
            <Tag color={record.status === 'success' ? 'green' : record.status === 'fail' ? 'red' : 'default'}>
              {record.status === 'success' ? '成功' : record.status === 'fail' ? '失败' : '未知'}
            </Tag>
          </Space>
          <Button
            icon={<EditOutlined />}
            onClick={() => {
              form.setFieldsValue({
                score: score,
                explain: reasoning,
              })
              setCorrectModalVisible(true)
            }}
          >
            修正
          </Button>
        </div>
        <Descriptions column={3} bordered>
          <Descriptions.Item label="记录ID">{record.id}</Descriptions.Item>
          <Descriptions.Item label="评估器版本ID">{record.evaluator_version_id}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={record.status === 'success' ? 'green' : record.status === 'fail' ? 'red' : 'default'}>
              {record.status}
            </Tag>
          </Descriptions.Item>
          {record.experiment_id && (
            <Descriptions.Item label="实验ID">{record.experiment_id}</Descriptions.Item>
          )}
          {record.experiment_run_id && (
            <Descriptions.Item label="实验运行ID">{record.experiment_run_id}</Descriptions.Item>
          )}
          {record.trace_id && (
            <Descriptions.Item label="追踪ID">{record.trace_id}</Descriptions.Item>
          )}
          <Descriptions.Item label="创建时间">
            {formatTimestamp(record.created_at)}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="评估结果" className="mb-4">
        <Descriptions column={1} bordered>
          <Descriptions.Item label="评分">
            {score !== null && score !== undefined ? (
              <Tag color={score >= 0.8 ? 'green' : score >= 0.5 ? 'orange' : 'red'}>
                {score}
              </Tag>
            ) : (
              '-'
            )}
          </Descriptions.Item>
          <Descriptions.Item label="原因">
            {reasoning || '-'}
          </Descriptions.Item>
          {record.output_data?.evaluator_usage && (
            <>
              <Descriptions.Item label="输入Token">
                {record.output_data.evaluator_usage.input_tokens || 0}
              </Descriptions.Item>
              <Descriptions.Item label="输出Token">
                {record.output_data.evaluator_usage.output_tokens || 0}
              </Descriptions.Item>
            </>
          )}
          {record.output_data?.time_consuming_ms && (
            <Descriptions.Item label="执行时间">
              {record.output_data.time_consuming_ms}ms
            </Descriptions.Item>
          )}
          {record.output_data?.evaluator_run_error && (
            <Descriptions.Item label="错误">
              <Tag color="red">
                [{record.output_data.evaluator_run_error.code}] {record.output_data.evaluator_run_error.message}
              </Tag>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title="输入数据" className="mb-4">
        <pre className="bg-gray-50 p-4 rounded text-xs overflow-auto">
          {JSON.stringify(record.input_data, null, 2)}
        </pre>
      </Card>

      <Card title="输出数据">
        <pre className="bg-gray-50 p-4 rounded text-xs overflow-auto">
          {JSON.stringify(record.output_data, null, 2)}
        </pre>
      </Card>

      <Modal
        title="修正记录"
        open={correctModalVisible}
        onOk={() => {
          form.validateFields().then((values) => {
            handleCorrect(values)
          })
        }}
        onCancel={() => {
          setCorrectModalVisible(false)
          form.resetFields()
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="score"
            label="评分"
            rules={[{ type: 'number', min: 0, max: 1, message: '评分必须在0-1之间' }]}
          >
            <InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="explain" label="说明">
            <TextArea rows={4} placeholder="修正说明" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

