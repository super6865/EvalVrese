import { Card, Form, InputNumber, Select, Slider, Switch, Button, Space, Input, Tooltip } from 'antd'
import { PlusOutlined, InfoCircleOutlined, DeleteOutlined } from '@ant-design/icons'
import { modelConfigService } from '../../../services/modelConfigService'
import { useState, useEffect } from 'react'

interface CommonConfigPanelProps {
  modelConfig: any
  onModelConfigChange: (config: any) => void
  variables: Array<{ name: string; value: any; type?: string }>
  onVariablesChange: (variables: Array<{ name: string; value: any; type?: string }>) => void
  tools: any[]
  onToolsChange: (tools: any[]) => void
  stepDebug: boolean
  onStepDebugChange: (enabled: boolean) => void
}

export function CommonConfigPanel({
  modelConfig,
  onModelConfigChange,
  variables,
  onVariablesChange,
  tools,
  onToolsChange,
  stepDebug,
  onStepDebugChange,
}: CommonConfigPanelProps) {
  const [modelConfigs, setModelConfigs] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadModelConfigs()
  }, [])

  const loadModelConfigs = async () => {
    try {
      setLoading(true)
      const response = await modelConfigService.list(false, 0, 100)
      setModelConfigs(response.configs.filter((c) => c.is_enabled))
    } catch (error) {
      console.error('Failed to load model configs:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleModelConfigChange = (field: string, value: any) => {
    onModelConfigChange({ ...modelConfig, [field]: value })
  }

  const handleVariableChange = (index: number, field: string, value: any) => {
    const newVariables = [...variables]
    newVariables[index] = { ...newVariables[index], [field]: value }
    onVariablesChange(newVariables)
  }

  const handleAddVariable = () => {
    onVariablesChange([...variables, { name: '', value: '', type: 'string' }])
  }

  const handleRemoveVariable = (index: number) => {
    onVariablesChange(variables.filter((_, i) => i !== index))
  }

  return (
    <div style={{ padding: '16px', height: '100%', overflow: 'auto' }}>
      {/* Model Configuration */}
      <Card title="模型配置" size="small" style={{ marginBottom: 16 }}>
        <Form layout="vertical" size="small">
          <Form.Item label="模型配置">
            <Select
              value={modelConfig.model_config_id}
              onChange={(value) => {
                const selected = modelConfigs.find((c) => c.id === value)
                if (selected) {
                  onModelConfigChange({
                    ...modelConfig, // Preserve all existing fields
                    model_config_id: selected.id,
                    model: `${selected.model_type}:${selected.model_version}`,
                    provider: selected.model_type,
                    temperature: selected.temperature ?? modelConfig.temperature ?? 0.7,
                    max_tokens: selected.max_tokens ?? modelConfig.max_tokens ?? 4096,
                    top_p: modelConfig.top_p ?? 1,
                    frequency_penalty: modelConfig.frequency_penalty ?? 0,
                    presence_penalty: modelConfig.presence_penalty ?? 0,
                  })
                } else {
                  handleModelConfigChange('model_config_id', undefined)
                }
              }}
              placeholder="选择模型配置"
              loading={loading}
              allowClear
              style={{ width: '100%' }}
            >
              {modelConfigs.map((mc) => (
                <Select.Option key={mc.id} value={mc.id}>
                  {mc.config_name} ({mc.model_type}:{mc.model_version})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Card>

      {/* Parameter Configuration */}
      <Card title="参数配置" size="small" style={{ marginBottom: 16 }}>
        <Form layout="vertical" size="small">
          <Form.Item
            label={
              <span>
                最大回复长度
                <Tooltip title="模型生成的最大 token 数量">
                  <InfoCircleOutlined style={{ marginLeft: 4, color: '#999' }} />
                </Tooltip>
              </span>
            }
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%' }}>
              <Slider
                min={1}
                max={8192}
                value={modelConfig.max_tokens || 4096}
                onChange={(value) => handleModelConfigChange('max_tokens', value)}
                style={{ flex: 1, margin: 0 }}
              />
              <InputNumber
                min={1}
                max={8192}
                value={modelConfig.max_tokens || 4096}
                onChange={(value) => handleModelConfigChange('max_tokens', value || 4096)}
                style={{ width: 80 }}
              />
            </div>
          </Form.Item>

          <Form.Item
            label={
              <span>
                生成随机性
                <Tooltip title="控制输出的随机性，值越大越随机">
                  <InfoCircleOutlined style={{ marginLeft: 4, color: '#999' }} />
                </Tooltip>
              </span>
            }
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%' }}>
              <Slider
                min={0}
                max={2}
                step={0.1}
                value={modelConfig.temperature || 0.8}
                onChange={(value) => handleModelConfigChange('temperature', value)}
                style={{ flex: 1, margin: 0 }}
              />
              <InputNumber
                min={0}
                max={2}
                step={0.1}
                value={modelConfig.temperature || 0.8}
                onChange={(value) => handleModelConfigChange('temperature', value || 0.8)}
                style={{ width: 80 }}
              />
            </div>
          </Form.Item>
        </Form>
      </Card>

      {/* Prompt Variables */}
      <Card title="Prompt 变量" size="small" style={{ marginBottom: 16 }}>
        {variables.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px 0', color: '#999' }}>
            暂无变量
          </div>
        ) : (
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            {variables.map((variable, index) => (
              <div
                key={variable.name}
                style={{
                  border: '1px solid #f0f0f0',
                  padding: 12,
                  borderRadius: 4,
                }}
              >
                <div style={{ marginBottom: 8, fontSize: 12, color: '#666', fontWeight: 500 }}>
                  {variable.name}
                </div>
                <Input
                  value={variable.value || ''}
                  onChange={(e) => handleVariableChange(index, 'value', e.target.value)}
                  placeholder="请输入变量值"
                  size="small"
                />
              </div>
            ))}
          </Space>
        )}
      </Card>

    </div>
  )
}

