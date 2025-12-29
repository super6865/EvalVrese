import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Button, message, Form, Input, Select, Space } from 'antd'
import { EditOutlined, SaveOutlined, CloseOutlined } from '@ant-design/icons'
import { evaluatorService } from '../../../services/evaluatorService'
import type { Evaluator, Message, ModelConfig } from '../../../types/evaluator'
import { modelConfigService, ModelConfig as ModelConfigType } from '../../../services/modelConfigService'
import Editor from '@monaco-editor/react'

const { TextArea } = Input

interface EvaluatorContentPanelProps {
  evaluator: Evaluator
  onUpdate?: () => void
}

// Helper function to normalize message_list format
// Handles both string (legacy) and array formats
const normalizeMessageList = (msgList: any): Message[] => {
  // If it's already a valid array, return it
  if (Array.isArray(msgList) && msgList.length > 0) {
    // Check if first element is a string (wrong format)
    if (typeof msgList[0] === 'string') {
      // Convert string array to proper format
      return [{
        role: 'system' as const,
        content: {
          text: msgList[0],
          content_type: 'Text' as const
        }
      }]
    }
    // Check if it's already in correct format
    if (msgList[0] && typeof msgList[0] === 'object' && msgList[0].role && msgList[0].content) {
      return msgList as Message[]
    }
  }
  // If it's a string, convert to array format
  if (typeof msgList === 'string' && msgList.length > 0) {
    return [{
      role: 'system' as const,
      content: {
        text: msgList,
        content_type: 'Text' as const
      }
    }]
  }
  return []
}

export default function EvaluatorContentPanel({ evaluator, onUpdate }: EvaluatorContentPanelProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [modelConfigs, setModelConfigs] = useState<ModelConfigType[]>([])
  const [loadingConfigs, setLoadingConfigs] = useState(false)
  const [messageList, setMessageList] = useState<Message[]>([])

  // Load model configurations for prompt evaluators
  useEffect(() => {
    if (evaluator.evaluator_type === 'prompt') {
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
    }
  }, [evaluator.evaluator_type])

  // Initialize form with evaluator content
  useEffect(() => {
    if (evaluator.evaluator_type === 'prompt' && evaluator.prompt_content) {
      // Normalize message_list format (handle both string and array)
      const messages = normalizeMessageList(evaluator.prompt_content.message_list)
      
      // Always update messageList when evaluator changes (unless we're actively editing)
      if (!isEditing) {
        setMessageList(messages)
      }
      
      // Create normalized prompt_content for form
      const normalizedPromptContent = {
        ...evaluator.prompt_content,
        message_list: messages
      }
      
      form.setFieldsValue({
        prompt_content: normalizedPromptContent,
      })
    } else if (evaluator.evaluator_type === 'code' && evaluator.code_content) {
      form.setFieldsValue({
        code_content: evaluator.code_content,
      })
    }
  }, [evaluator, form, isEditing])

  const handleSave = async () => {
    try {
      setLoading(true)
      const values = await form.validateFields()
      
      // For prompt evaluator, ensure message_list is included
      if (evaluator.evaluator_type === 'prompt') {
        // Always use messageList state which is the source of truth during editing
        // messageList is updated in real-time as user types
        const finalMessageList = Array.isArray(messageList) && messageList.length > 0 
          ? messageList 
          : (values.prompt_content?.message_list || [])
        
        if (finalMessageList.length === 0) {
          message.error('消息列表不能为空')
          return
        }
        
        // Merge with existing prompt_content to preserve all fields (parse_type, prompt_suffix, etc.)
        const promptContent = {
          ...(evaluator.prompt_content || {}), // Preserve all existing fields
          ...(values.prompt_content || {}),    // Override with form values
          message_list: finalMessageList,      // Use the current messageList state
        }
        
        await evaluatorService.updateContent(evaluator.id, {
          prompt_content: promptContent,
          input_schemas: evaluator.input_schemas,
          output_schemas: evaluator.output_schemas,
        })
      } else {
        await evaluatorService.updateContent(evaluator.id, {
          code_content: values.code_content,
          input_schemas: evaluator.input_schemas,
          output_schemas: evaluator.output_schemas,
        })
      }
      
      message.success('保存成功')
      setIsEditing(false)
      // Wait for onUpdate to complete before continuing
      if (onUpdate) {
        await onUpdate()
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || error.message || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    // Reset to original evaluator content
    if (evaluator.evaluator_type === 'prompt' && evaluator.prompt_content) {
      const messages = Array.isArray(evaluator.prompt_content.message_list) 
        ? evaluator.prompt_content.message_list 
        : []
      setMessageList(messages)
      form.setFieldsValue({
        prompt_content: evaluator.prompt_content,
      })
    }
    setIsEditing(false)
  }

  if (evaluator.evaluator_type === 'prompt') {
    // Always use evaluator.prompt_content directly, don't rely on local variables
    const promptContent = evaluator.prompt_content || {}
    const modelConfig = promptContent.model_config
    // Find the model config from the list if model_config_id is available
    const modelConfigId = modelConfig?.model_config_id
    const selectedModelConfig = modelConfigId 
      ? modelConfigs.find(c => c.id === modelConfigId)
      : null

    // Get message list - always use evaluator.prompt_content.message_list as source of truth
    // Direct access to ensure we get the latest data
    const displayMessages = (() => {
      // Direct access to evaluator.prompt_content.message_list
      const msgList = evaluator?.prompt_content?.message_list
      const normalized = normalizeMessageList(msgList)
      if (normalized.length > 0) {
        return normalized
      }
      // Fallback to state if evaluator data is not available
      const stateNormalized = normalizeMessageList(messageList)
      if (stateNormalized.length > 0) {
        return stateNormalized
      }
      return []
    })()

    return (
      <Card
        title={
          <div className="flex items-center justify-between">
            <span>Prompt 评估器内容</span>
            {!isEditing ? (
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={() => setIsEditing(true)}
              >
                编辑
              </Button>
            ) : (
              <Space>
                <Button onClick={handleCancel} icon={<CloseOutlined />}>
                  取消
                </Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSave}
                  loading={loading}
                >
                  保存
                </Button>
              </Space>
            )}
          </div>
        }
      >
        {!isEditing ? (
          <div className="space-y-4">
            <Descriptions column={1} bordered>
              <Descriptions.Item label="消息列表">
                <div className="space-y-2">
                  {displayMessages.length > 0 ? (
                    displayMessages.map((msg: Message, index: number) => (
                      <div key={index} className="border p-2 rounded">
                        <Tag color={msg.role === 'system' ? 'blue' : 'green'}>{msg.role}</Tag>
                        <div className="mt-1 whitespace-pre-wrap">{msg.content?.text || ''}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-gray-400">暂无消息</div>
                  )}
                </div>
              </Descriptions.Item>
              {(selectedModelConfig || modelConfig) && (
                <>
                  <Descriptions.Item label="模型配置">
                    <div className="space-y-1">
                      {selectedModelConfig ? (
                        <>
                          <div><strong>配置名称:</strong> {selectedModelConfig.config_name}</div>
                          <div><strong>模型类型:</strong> {selectedModelConfig.model_type}</div>
                          <div><strong>模型版本:</strong> {selectedModelConfig.model_version}</div>
                          {selectedModelConfig.temperature !== undefined && (
                            <div><strong>Temperature:</strong> {selectedModelConfig.temperature}</div>
                          )}
                          {selectedModelConfig.max_tokens !== undefined && (
                            <div><strong>Max Tokens:</strong> {selectedModelConfig.max_tokens}</div>
                          )}
                        </>
                      ) : (
                        <>
                          <div><strong>模型:</strong> {modelConfig?.model || '-'}</div>
                          {modelConfig?.provider && <div><strong>提供商:</strong> {modelConfig.provider}</div>}
                          {modelConfig?.temperature !== undefined && (
                            <div><strong>Temperature:</strong> {modelConfig.temperature}</div>
                          )}
                          {modelConfig?.max_tokens !== undefined && (
                            <div><strong>Max Tokens:</strong> {modelConfig.max_tokens}</div>
                          )}
                        </>
                      )}
                    </div>
                  </Descriptions.Item>
                  {promptContent?.parse_type && (
                    <Descriptions.Item label="解析类型">
                      {promptContent.parse_type}
                    </Descriptions.Item>
                  )}
                  {promptContent?.prompt_suffix && (
                    <Descriptions.Item label="Prompt 后缀">
                      <div className="whitespace-pre-wrap">{promptContent.prompt_suffix}</div>
                    </Descriptions.Item>
                  )}
                </>
              )}
            </Descriptions>
          </div>
        ) : (
          <Form form={form} layout="vertical">
            <Form.Item
              name={['prompt_content', 'message_list']}
              label="消息列表"
              rules={[{ required: true, message: '消息列表不能为空' }]}
            >
              <div className="space-y-2">
                {Array.isArray(messageList) && messageList.length > 0 ? (
                  messageList.map((msg: Message, index: number) => (
                    <div key={index} className="border p-2 rounded">
                      <Tag color={msg.role === 'system' ? 'blue' : 'green'}>{msg.role}</Tag>
                      <TextArea
                        rows={4}
                        value={msg.content?.text || ''}
                        onChange={(e) => {
                          const newList = [...messageList]
                          newList[index].content = { ...newList[index].content, text: e.target.value }
                          setMessageList(newList)
                          form.setFieldsValue({ 'prompt_content.message_list': newList })
                        }}
                        className="mt-2"
                      />
                    </div>
                  ))
                ) : (
                  <div className="text-gray-400">暂无消息</div>
                )}
              </div>
            </Form.Item>
            <Form.Item
              name={['prompt_content', 'model_config', 'model_config_id']}
              label="模型配置"
              initialValue={modelConfig?.model_config_id}
              rules={[{ required: true, message: '请选择模型配置' }]}
            >
              <Select
                loading={loadingConfigs}
                placeholder="选择模型配置"
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                onChange={(value) => {
                  const selectedConfig = modelConfigs.find(c => c.id === value)
                  if (selectedConfig) {
                    form.setFieldsValue({
                      'prompt_content.model_config': {
                        model_config_id: selectedConfig.id,
                        model: `${selectedConfig.model_type}/${selectedConfig.model_version}`,
                        provider: selectedConfig.model_type,
                        api_base: selectedConfig.api_base,
                        temperature: selectedConfig.temperature,
                        max_tokens: selectedConfig.max_tokens,
                      }
                    })
                  }
                }}
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
          </Form>
        )}
      </Card>
    )
  } else {
    // Code evaluator
    const codeContent = evaluator.code_content
    const code = codeContent?.code_content || ''
    const languageType = codeContent?.language_type || 'Python'

    return (
      <Card
        title={
          <div className="flex items-center justify-between">
            <span>Code 评估器内容</span>
            {!isEditing ? (
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={() => setIsEditing(true)}
              >
                编辑
              </Button>
            ) : (
              <Space>
                <Button onClick={handleCancel} icon={<CloseOutlined />}>
                  取消
                </Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSave}
                  loading={loading}
                >
                  保存
                </Button>
              </Space>
            )}
          </div>
        }
      >
        {!isEditing ? (
          <div className="space-y-4">
            <Descriptions column={1} bordered>
              <Descriptions.Item label="语言类型">
                <Tag color="blue">{languageType}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="代码内容">
                <div style={{ height: '400px', border: '1px solid #d9d9d9', borderRadius: '4px' }}>
                  <Editor
                    height="100%"
                    language={languageType.toLowerCase()}
                    value={code}
                    options={{
                      readOnly: true,
                      minimap: { enabled: false },
                      scrollBeyondLastLine: false,
                    }}
                  />
                </div>
              </Descriptions.Item>
            </Descriptions>
          </div>
        ) : (
          <Form form={form} layout="vertical">
            <Form.Item
              name={['code_content', 'language_type']}
              label="语言类型"
              rules={[{ required: true, message: '语言类型不能为空' }]}
            >
              <Select>
                <Select.Option value="Python">Python</Select.Option>
                <Select.Option value="JS">JavaScript</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item
              name={['code_content', 'code_content']}
              label="代码内容"
              rules={[{ required: true, message: '代码内容不能为空' }]}
            >
              <div style={{ height: '400px', border: '1px solid #d9d9d9', borderRadius: '4px' }}>
                <Editor
                  height="100%"
                  language={form.getFieldValue(['code_content', 'language_type'])?.toLowerCase() || 'python'}
                  value={code}
                  onChange={(value) => {
                    form.setFieldsValue({ 'code_content.code_content': value || '' })
                  }}
                  options={{
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                  }}
                />
              </div>
            </Form.Item>
          </Form>
        )}
      </Card>
    )
  }
}

