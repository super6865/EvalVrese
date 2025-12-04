import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Form, Button, message } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { evaluatorService } from '../../services/evaluatorService'
import type { EvaluatorType } from '../../types/evaluator'
import PromptEvaluatorForm from './components/PromptEvaluatorForm'
import CodeEvaluatorForm from './components/CodeEvaluatorForm'

export default function EvaluatorCreatePage() {
  const { type, id } = useParams<{ type: string; id?: string }>()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const evaluatorType = (type as EvaluatorType) || 'prompt'


  const handleSubmit = async (values: any) => {
    setLoading(true)
    try {
      let evaluatorContent: any = {}
      
      if (evaluatorType === 'prompt') {
        const promptData = values.current_version?.evaluator_content?.prompt_evaluator || {}
        
        const messageList: any[] = []
        const systemText = promptData.message_list?.[0]?.content?.text || ''
        const userText = promptData.message_list?.[1]?.content?.text || ''
        
        if (systemText) {
          messageList.push({
            role: 'system',
            content: { content_type: 'Text', text: systemText }
          })
        }
        if (userText) {
          messageList.push({
            role: 'user',
            content: { content_type: 'Text', text: userText }
          })
        }
        
        evaluatorContent.prompt_evaluator = {
          message_list: messageList,
          model_config: promptData.model_config || {},
          parse_type: promptData.parse_type || 'text',
          prompt_suffix: promptData.prompt_suffix,
        }
        
        if (messageList.length > 0) {
          const inputSchemas = generateInputSchemas(messageList)
          if (!values.current_version) {
            values.current_version = {}
          }
          values.current_version.input_schemas = inputSchemas
        }
      } else {
        const codeData = values.current_version?.evaluator_content?.code_evaluator || {}
        evaluatorContent.code_evaluator = {
          code_content: codeData.code_content || '',
          language_type: codeData.language_type || 'Python',
        }
      }

      const evaluator = await evaluatorService.create({
        name: values.name,
        evaluator_type: evaluatorType,
        description: values.description,
        current_version: {
          // version will be auto-generated as 'v1.0' by backend if not provided
          evaluator_content: evaluatorContent,
          input_schemas: values.current_version?.input_schemas,
          output_schemas: values.current_version?.output_schemas,
          description: values.description,
        },
      })
      
      message.success('创建成功')
      navigate(`/evaluators/${evaluator.id}`)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  // Generate input schemas from message list (extract variables in {{variable}} format)
  const generateInputSchemas = (messageList: any[]): any[] => {
    if (!messageList || messageList.length === 0) return []
    
    const variables = new Set<string>()
    
    messageList.forEach((msg: any) => {
      const text = msg.content?.text || ''
      const regex = /\{\{([^}]+)\}\}/g
      let match
      while ((match = regex.exec(text)) !== null) {
        variables.add(match[1].trim())
      }
    })
    
    return Array.from(variables).map((varName) => ({
      key: varName,
      support_content_types: ['Text'],
      json_schema: '{"type": "string"}',
    }))
  }

  return (
    <div className="h-full overflow-y-auto px-6 py-4">
      <div className="mb-4">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/evaluators')}>
          返回
        </Button>
      </div>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        autoComplete="off"
        className="w-[800px] mx-auto"
      >
        {evaluatorType === 'prompt' ? (
          <PromptEvaluatorForm form={form} onSubmit={handleSubmit} loading={loading} />
        ) : (
          <CodeEvaluatorForm form={form} onSubmit={handleSubmit} loading={loading} />
        )}
      </Form>
    </div>
  )
}

