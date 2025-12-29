import { useState, useEffect } from 'react'
import { Form, Input, Button, Card, message, Descriptions, Tag } from 'antd'
import { evaluatorService } from '../../../services/evaluatorService'
import type { EvaluatorType, EvaluatorInputData, EvaluatorOutputData, Evaluator } from '../../../types/evaluator'

const { TextArea } = Input

interface EvaluatorDebugPanelProps {
  evaluatorId: number
  evaluatorType: EvaluatorType
}

export default function EvaluatorDebugPanel({
  evaluatorId,
  evaluatorType,
}: EvaluatorDebugPanelProps) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<EvaluatorOutputData | null>(null)
  const [evaluator, setEvaluator] = useState<Evaluator | null>(null)
  const [loadingEvaluator, setLoadingEvaluator] = useState(false)

  // 加载评估器信息
  useEffect(() => {
    const loadEvaluator = async () => {
      setLoadingEvaluator(true)
      try {
        const evaluatorData = await evaluatorService.get(evaluatorId)
        setEvaluator(evaluatorData)
        
        // 根据评估器信息生成初始输入值
        if (evaluatorData.prompt_content && evaluatorType === 'prompt') {
          const promptContent = evaluatorData.prompt_content
          const messageList = promptContent.message_list || []
          
          // 从 message_list 中提取变量，生成示例输入
          const initialValues: any = {}
          
          // 提取 message_list 中的变量（如 {input}, {output} 等）
          const variables = new Set<string>()
          messageList.forEach((msg: any) => {
            const content = msg.content?.text || ''
            const matches = content.match(/\{(\w+)\}/g)
            if (matches) {
              matches.forEach((match: string) => {
                const varName = match.replace(/[{}]/g, '')
                variables.add(varName)
              })
            }
          })
          
          // 生成 input_fields（从 message_list 中提取所有变量，优先从 user message）
          const userMessage = messageList.find((msg: any) => msg.role === 'user')
          const systemMessage = messageList.find((msg: any) => msg.role === 'system')
          
          // 收集所有可能的输入变量（排除 output, target_output, reference, dataset 等）
          const inputVariables = new Set<string>()
          const excludeVars = ['output', 'target_output', 'reference', 'dataset', 'dataset_field']
          
          // 从 user message 中提取变量
          if (userMessage) {
            const userContent = userMessage.content?.text || ''
            const matches = userContent.match(/\{(\w+)\}/g)
            if (matches) {
              matches.forEach((match: string) => {
                const varName = match.replace(/[{}]/g, '')
                if (!excludeVars.includes(varName.toLowerCase())) {
                  inputVariables.add(varName)
                }
              })
            }
          }
          
          // 如果 user message 中没有变量，从 system message 中提取
          if (inputVariables.size === 0 && systemMessage) {
            const systemContent = systemMessage.content?.text || ''
            const matches = systemContent.match(/\{(\w+)\}/g)
            if (matches) {
              matches.forEach((match: string) => {
                const varName = match.replace(/[{}]/g, '')
                if (!excludeVars.includes(varName.toLowerCase())) {
                  inputVariables.add(varName)
                }
              })
            }
          }
          
          // 生成 input_fields
          if (inputVariables.size > 0) {
            const inputFields: any = {}
            inputVariables.forEach((varName) => {
              inputFields[varName] = {
                content_type: 'Text',
                text: `示例${varName}内容`
              }
            })
            initialValues.input_fields = JSON.stringify(inputFields, null, 2)
          } else {
            // 如果没有找到变量，使用默认示例
            initialValues.input_fields = JSON.stringify({
              input: {
                content_type: 'Text',
                text: '输入内容'
              }
            }, null, 2)
          }
          
          // 生成 evaluate_target_output_fields（通常使用 output 变量）
          if (variables.has('output') || variables.has('target_output')) {
            initialValues.evaluate_target_output_fields = JSON.stringify({
              output: {
                content_type: 'Text',
                text: '目标输出'
              }
            }, null, 2)
          } else {
            initialValues.evaluate_target_output_fields = JSON.stringify({
              output: {
                content_type: 'Text',
                text: '目标输出'
              }
            }, null, 2)
          }
          
          // 生成 evaluate_dataset_fields（检查各种可能的变量名）
          const datasetVarNames = ['reference', 'dataset', 'dataset_field', 'ref', 'ground_truth', 'expected']
          const hasDatasetVar = Array.from(variables).some(v => 
            datasetVarNames.some(name => v.toLowerCase() === name.toLowerCase())
          )
          
          if (hasDatasetVar) {
            // 找到匹配的变量名
            const matchedVar = Array.from(variables).find(v => 
              datasetVarNames.some(name => v.toLowerCase() === name.toLowerCase())
            )
            initialValues.evaluate_dataset_fields = JSON.stringify({
              [matchedVar || 'dataset_field']: {
                content_type: 'Text',
                text: '数据集值'
              }
            }, null, 2)
          } else {
            // 即使没有找到变量，也提供默认示例
            initialValues.evaluate_dataset_fields = JSON.stringify({
              dataset_field: {
                content_type: 'Text',
                text: '数据集值'
              }
            }, null, 2)
          }
          
          // 设置表单初始值
          form.setFieldsValue(initialValues)
        } else {
          // 对于非 prompt 类型或没有 prompt_content 的情况，使用默认值
          form.setFieldsValue({
            input_fields: JSON.stringify({
              input: {
                content_type: 'Text',
                text: '输入内容'
              }
            }, null, 2),
            evaluate_target_output_fields: JSON.stringify({
              output: {
                content_type: 'Text',
                text: '目标输出'
              }
            }, null, 2),
            evaluate_dataset_fields: JSON.stringify({
              dataset_field: {
                content_type: 'Text',
                text: '数据集值'
              }
            }, null, 2),
            history_messages: JSON.stringify([
              {
                role: 'user',
                content: {
                  content_type: 'Text',
                  text: '历史消息'
                }
              }
            ], null, 2)
          })
        }
      } catch (error) {
        // Failed to load evaluator info
        // 即使加载失败，也设置默认值
        form.setFieldsValue({
          input_fields: JSON.stringify({
            input: {
              content_type: 'Text',
              text: '输入内容'
            }
          }, null, 2),
          evaluate_target_output_fields: JSON.stringify({
            output: {
              content_type: 'Text',
              text: '目标输出'
            }
          }, null, 2),
          evaluate_dataset_fields: JSON.stringify({
            dataset_field: {
              content_type: 'Text',
              text: '数据集值'
            }
          }, null, 2),
          history_messages: JSON.stringify([
            {
              role: 'user',
              content: {
                content_type: 'Text',
                text: '历史消息'
              }
            }
          ], null, 2)
        })
      } finally {
        setLoadingEvaluator(false)
      }
    }
    
    if (evaluatorId) {
      loadEvaluator()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [evaluatorId, evaluatorType])

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

  const handleDebug = async (values: any) => {
    setLoading(true)
    try {
      // 构建输入数据
      const inputData: EvaluatorInputData = {
        input_fields: values.input_fields ? JSON.parse(values.input_fields) : {},
        evaluate_dataset_fields: values.evaluate_dataset_fields ? JSON.parse(values.evaluate_dataset_fields) : {},
        evaluate_target_output_fields: values.evaluate_target_output_fields ? JSON.parse(values.evaluate_target_output_fields) : {},
        history_messages: values.history_messages ? JSON.parse(values.history_messages) : undefined,
      }

      const response = await evaluatorService.debugByEvaluatorId(evaluatorId, {
        input_data: inputData,
      })
      setResult(response)
      message.success('调试成功')
    } catch (error: any) {
      message.error(error.response?.data?.detail || error.message || '调试失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card title="调试评估器" loading={loadingEvaluator}>
        <Form form={form} layout="vertical" onFinish={handleDebug}>
          <Form.Item
            name="input_fields"
            label="输入字段 (JSON)"
            tooltip='格式: {"field_name": {"content_type": "Text", "text": "value"}}'
          >
            <TextArea rows={4} placeholder='{"input": {"content_type": "Text", "text": "输入内容"}}' />
          </Form.Item>
          <Form.Item
            name="evaluate_dataset_fields"
            label="数据集字段 (JSON, 可选)"
            tooltip='格式: {"field_name": {"content_type": "Text", "text": "value"}}'
          >
            <TextArea rows={3} placeholder='{"dataset_field": {"content_type": "Text", "text": "数据集值"}}' />
          </Form.Item>
          <Form.Item
            name="evaluate_target_output_fields"
            label="目标输出字段 (JSON, 可选)"
            tooltip='格式: {"field_name": {"content_type": "Text", "text": "value"}}'
          >
            <TextArea rows={3} placeholder='{"output": {"content_type": "Text", "text": "目标输出"}}' />
          </Form.Item>
          <Form.Item
            name="history_messages"
            label="历史消息 (JSON, 可选)"
            tooltip='格式: [{"role": "user", "content": {"content_type": "Text", "text": "消息"}}]'
          >
            <TextArea rows={3} placeholder='[{"role": "user", "content": {"content_type": "Text", "text": "历史消息"}}]' />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              执行调试
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {result && (
        <Card title="调试结果">
          <Descriptions column={1} bordered>
            {result.evaluator_result && (
              <>
                <Descriptions.Item label="评分">
                  {result.evaluator_result.score !== null && result.evaluator_result.score !== undefined ? (
                    <Tag color={
                      result.evaluator_result.score >= 0.8 ? 'green' :
                      result.evaluator_result.score >= 0.5 ? 'orange' : 'red'
                    }>
                      {result.evaluator_result.score}
                    </Tag>
                  ) : (
                    '-'
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="原因">
                  <div className="whitespace-pre-wrap break-words max-h-96 overflow-y-auto">
                    {parseUnicodeString(result.evaluator_result.reasoning || result.evaluator_result.correction?.explain)}
                  </div>
                </Descriptions.Item>
                {result.evaluator_result.correction && (
                  <Descriptions.Item label="修正">
                    <Tag color="purple">已修正</Tag>
                    {result.evaluator_result.correction.updated_by && (
                      <span className="ml-2">修正人: {result.evaluator_result.correction.updated_by}</span>
                    )}
                  </Descriptions.Item>
                )}
              </>
            )}
            {result.evaluator_usage && (
              <>
                <Descriptions.Item label="输入Token">
                  {result.evaluator_usage.input_tokens || 0}
                </Descriptions.Item>
                <Descriptions.Item label="输出Token">
                  {result.evaluator_usage.output_tokens || 0}
                </Descriptions.Item>
              </>
            )}
            {result.time_consuming_ms && (
              <Descriptions.Item label="执行时间">
                {result.time_consuming_ms}ms
              </Descriptions.Item>
            )}
            {result.evaluator_run_error && (
              <Descriptions.Item label="错误">
                <Tag color="red">
                  [{result.evaluator_run_error.code}] {result.evaluator_run_error.message}
                </Tag>
              </Descriptions.Item>
            )}
            {result.stdout && (
              <Descriptions.Item label="标准输出">
                <pre className="m-0 text-xs bg-gray-50 p-2 rounded">
                  {result.stdout}
                </pre>
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>
      )}
    </div>
  )
}

