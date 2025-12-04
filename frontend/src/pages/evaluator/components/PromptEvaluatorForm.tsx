import { Form, Input, Select, Button, Space, Tooltip } from 'antd'
import { PlusOutlined, DeleteOutlined, InfoCircleOutlined, ClearOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Message, ModelConfig, Role } from '../../../types/evaluator'
import { modelConfigService, ModelConfig as ModelConfigType } from '../../../services/modelConfigService'

const { TextArea } = Input

interface PromptEvaluatorFormProps {
  form: any
  onSubmit?: (values: any) => void
  loading?: boolean
  initialValues?: {
    message_list?: Message[]
    model_config?: ModelConfig
    parse_type?: string
    prompt_suffix?: string
  }
}

export default function PromptEvaluatorForm({ form, onSubmit, loading }: PromptEvaluatorFormProps) {
  const navigate = useNavigate()
  const [refreshKey, setRefreshKey] = useState(0)
  const [modelConfigs, setModelConfigs] = useState<ModelConfigType[]>([])
  const [loadingConfigs, setLoadingConfigs] = useState(false)
  
  // Initialize with default System message
  const defaultMessages: Message[] = [
    { role: 'system', content: { content_type: 'Text', text: '' } },
  ]
  
  const [messageList, setMessageList] = useState<Message[]>(defaultMessages)
  
  // Load model configurations
  useEffect(() => {
    const loadModelConfigs = async () => {
      setLoadingConfigs(true)
      try {
        const response = await modelConfigService.list(false)
        setModelConfigs(response.configs)
      } catch (error) {
        // Error loading model configurations
      } finally {
        setLoadingConfigs(false)
      }
    }
    loadModelConfigs()
  }, [])

  // Initialize form with message list on mount
  useEffect(() => {
      form.setFieldsValue({
        current_version: {
          evaluator_content: {
            prompt_evaluator: {
              message_list: messageList
            }
          }
        }
      })
  }, [])

  const addUserMessage = () => {
    const newList: Message[] = [...messageList, { role: 'user' as Role, content: { content_type: 'Text' as const, text: '' } }]
    setMessageList(newList)
    form.setFieldsValue({ 
      current_version: {
        evaluator_content: {
          prompt_evaluator: {
            message_list: newList
          }
        }
      }
    })
  }

  const removeUserMessage = () => {
    if (messageList.length > 1) {
      const newList = messageList.slice(0, 1) // Keep only System message
      setMessageList(newList)
      form.setFieldsValue({ 
        current_version: {
          evaluator_content: {
            prompt_evaluator: {
              message_list: newList
            }
          }
        }
      })
    }
  }

  const updateMessage = (index: number, text: string) => {
    const newList = [...messageList]
    newList[index].content = { ...newList[index].content, text }
    setMessageList(newList)
    form.setFieldsValue({ 
      current_version: {
        evaluator_content: {
          prompt_evaluator: {
            message_list: newList
          }
        }
      }
    })
  }

  const clearPrompt = () => {
    const clearedList = [
      { role: 'system' as Role, content: { content_type: 'Text' as const, text: '' } }
    ]
    setMessageList(clearedList)
    form.setFieldsValue({ 
      current_version: {
        evaluator_content: {
          prompt_evaluator: {
            message_list: clearedList
          }
        }
      }
    })
    setRefreshKey(prev => prev + 1)
  }

  const handleSubmit = async () => {
    try {
      // Ensure message_list is up to date before validation
      const currentValues = form.getFieldsValue()
      const systemText = currentValues.current_version?.evaluator_content?.prompt_evaluator?.message_list?.[0]?.content?.text || ''
      const userText = currentValues.current_version?.evaluator_content?.prompt_evaluator?.message_list?.[1]?.content?.text || ''
      
      // Rebuild message_list from form values
      const updatedMessageList: Message[] = [
        { role: 'system', content: { content_type: 'Text', text: systemText } }
      ]
      if (userText || userMessage) {
        updatedMessageList.push({ role: 'user', content: { content_type: 'Text', text: userText } })
      }
      
      // Update form with complete message_list
      form.setFieldsValue({
        current_version: {
          evaluator_content: {
            prompt_evaluator: {
              message_list: updatedMessageList
            }
          }
        }
      })
      
      const values = await form.validateFields()
      if (onSubmit) {
        onSubmit(values)
      } else {
        form.submit()
      }
    } catch (error) {
      // Validation failed
    }
  }

  const systemMessage = messageList[0]
  const userMessage = messageList[1]

  return (
    <div className="space-y-6">
      {/* 基础信息 */}
      <div>
        <div className="h-[28px] mb-3 text-[16px] leading-7 font-medium text-gray-900">
          基础信息
        </div>
        <Form.Item
          name="name"
          label="名称"
          rules={[{ required: true, message: '请输入名称' }]}
                >
          <Input 
            placeholder="请输入名称" 
            maxLength={50}
            showCount
          />
        </Form.Item>
        <Form.Item 
          name="description" 
          label="描述"
        >
              <TextArea
            rows={2} 
            placeholder="请输入描述" 
            maxLength={200}
            showCount
              />
        </Form.Item>
      </div>

      {/* 配置信息 */}
      <div>
        <div className="h-[28px] mb-3 text-[16px] leading-7 font-medium text-gray-900">
          配置信息
        </div>

        {/* 模型配置选择 */}
        <Form.Item
          name={['current_version', 'evaluator_content', 'prompt_evaluator', 'model_config', 'model_config_id']}
          label="模型配置"
          rules={[{ required: true, message: '请选择模型配置' }]}
        >
          <Select 
            placeholder="选择模型配置" 
            loading={loadingConfigs}
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
          >
            {modelConfigs.map((config) => (
              <Select.Option 
                key={config.id} 
                value={config.id}
                label={`${config.config_name} (${config.model_type}/${config.model_version})`}
              >
                {config.config_name} ({config.model_type}/{config.model_version})
                {config.is_enabled && <span className="text-green-500 ml-2">●</span>}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>
        <div className="text-sm text-gray-500 mb-4">
          <Tooltip title="如果列表为空，请先在模型管理页面创建模型配置">
            <span>没有找到模型配置？<a onClick={() => navigate('/model-configs')} style={{ cursor: 'pointer', color: '#1890ff' }}>前往模型管理</a></span>
          </Tooltip>
        </div>

        {/* Prompt字段 */}
        <div className="py-[10px]">
          <div className="flex flex-row items-center justify-between mb-1">
            <span className="text-sm font-medium text-gray-900">
              Prompt <span className="text-red-500">*</span>
            </span>
            <Button
              size="small"
              type="text"
              icon={<ClearOutlined />}
              onClick={clearPrompt}
              className="text-xs"
              style={{ fontSize: '12px' }}
            >
              清空
            </Button>
          </div>
          
          {/* System消息 */}
          <div className="mb-1 relative">
        <Form.Item
              name={['current_version', 'evaluator_content', 'prompt_evaluator', 'message_list', '0', 'content', 'text']}
              rules={[{ required: true, message: 'System消息不能为空' }]}
              className="!mb-0"
            >
              <div className="relative">
                <div className="absolute top-2 left-2 text-sm text-gray-600 z-10 pointer-events-none">System</div>
                <TextArea
                  key={refreshKey}
                  rows={6}
                  placeholder="请输入内容,支持按此格式书写变量:{{USER_NAME}}"
                  value={systemMessage?.content?.text || ''}
                  onChange={(e) => updateMessage(0, e.target.value)}
                  style={{ paddingTop: '28px' }}
                />
              </div>
        </Form.Item>
          </div>

          {/* User消息 */}
          {userMessage ? (
            <div className="relative">
              <div className="absolute top-2 right-2 z-10">
                <Button
                  size="small"
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={removeUserMessage}
                >
                  删除
                </Button>
              </div>
        <Form.Item
                name={['current_version', 'evaluator_content', 'prompt_evaluator', 'message_list', '1', 'content', 'text']}
                rules={[{ required: true, message: 'User消息不能为空' }]}
                className="!mb-0"
        >
           <div className="relative">
             <div className="absolute top-2 left-2 text-sm text-gray-600 z-10 pointer-events-none">User</div>
          <TextArea
                    rows={6}
                    placeholder="请输入内容,支持按此格式书写变量:{{USER_NAME}}"
                    value={userMessage?.content?.text || ''}
                    onChange={(e) => updateMessage(1, e.target.value)}
                    style={{ paddingTop: '28px' }}
           />
           </div>
         </Form.Item>
            </div>
          ) : (
            <Button
              type="dashed"
              icon={<PlusOutlined />}
              onClick={addUserMessage}
              block
              className="mb-3"
            >
              + 添加 User Prompt
            </Button>
          )}
        </div>
      </div>

      {/* 输出 */}
      <div>
        <div className="flex items-center h-5 text-sm font-medium text-gray-900 mb-2">
          输出
          <Tooltip title="评估器输出格式说明">
            <InfoCircleOutlined className="ml-1 text-gray-400" />
          </Tooltip>
        </div>
        <div className="text-sm text-gray-600 leading-5 mb-[6px]">
          <span className="font-medium">得分：</span>
          最终的得分,必须输出,必须输出一个数字,表示满足Prompt中评分标准的程度。得分范围从0.0到1.0,1.0表示完全满足评分标准,0.0表示完全不满足评分标准。
        </div>
        <div className="text-sm text-gray-600 leading-5">
          <span className="font-medium">原因：</span>
          对得分的可读解释。最后,必须用一句话结束理由,该句话为:因此,应该给出的分数是你的评分。
        </div>
      </div>

      {/* 操作按钮 */}
      <Form.Item>
        <Space>
          <Button type="primary" onClick={handleSubmit} loading={loading}>
            创建
          </Button>
          <Button onClick={() => navigate('/evaluators')}>取消</Button>
        </Space>
        </Form.Item>
    </div>
  )
}
