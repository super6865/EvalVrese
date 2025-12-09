import { Card, Input, Button, Space, Typography, Empty, Tag } from 'antd'
import { PlayCircleOutlined, CopyOutlined } from '@ant-design/icons'
import { message } from 'antd'

const { TextArea } = Input
const { Text, Title } = Typography

interface DebugPanelProps {
  input: string
  onInputChange: (value: string) => void
  result: any
  isExecuting: boolean
  onExecute: () => void
  executionHistory: any[]
  modelConfig?: any
}

export function DebugPanel({
  input,
  onInputChange,
  result,
  isExecuting,
  onExecute,
  executionHistory,
  modelConfig,
}: DebugPanelProps) {
  const hasModelConfig = modelConfig?.model_config_id !== undefined && modelConfig?.model_config_id !== null

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!isExecuting && input.trim() && hasModelConfig) {
        onExecute()
      }
    }
  }

  const handleCopy = () => {
    if (result?.content) {
      navigator.clipboard.writeText(result.content)
      message.success('已复制到剪贴板')
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={5} style={{ margin: 0 }}>预览与调试</Title>
      </div>

      {/* Preview Area */}
      <div style={{ flex: 1, padding: '16px', overflow: 'auto' }}>
        {result ? (
          <Card
            size="small"
            title={
              <Space>
                <span>执行结果</span>
                {result.error && <Tag color="error">错误</Tag>}
                {result.usage && (
                  <Tag color="blue">
                    {result.usage.input_tokens || 0} / {result.usage.output_tokens || 0} tokens
                  </Tag>
                )}
                {result.time_consuming_ms && (
                  <Tag color="default">{result.time_consuming_ms}ms</Tag>
                )}
              </Space>
            }
            extra={
              result.content && (
                <Button
                  type="text"
                  size="small"
                  icon={<CopyOutlined />}
                  onClick={handleCopy}
                >
                  复制
                </Button>
              )
            }
          >
            {result.error ? (
              <Text type="danger" style={{ whiteSpace: 'pre-wrap' }}>
                {result.error}
              </Text>
            ) : result.content ? (
              <Text style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                {result.content}
              </Text>
            ) : (
              <Empty description="无结果" />
            )}
          </Card>
        ) : (
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>🧭</div>
            <div>预览区域</div>
            <div style={{ fontSize: '12px', marginTop: '8px' }}>
              模型输出将显示在这里
            </div>
          </div>
        )}
      </div>

      {/* Single Run Input */}
      <div style={{ padding: '16px', borderTop: '1px solid #f0f0f0' }}>
        <TextArea
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="请输入问题测试大模型回复,回车发送,Shift+回车换行"
          rows={3}
          disabled={isExecuting}
        />
        <div style={{ marginTop: 8, marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            该模型不支持上传图片
          </Text>
        </div>
        <Button
          type="primary"
          block
          icon={<PlayCircleOutlined />}
          onClick={onExecute}
          loading={isExecuting}
          disabled={!input.trim() || !hasModelConfig}
          title={!hasModelConfig ? '请先选择模型配置' : undefined}
        >
          运行
        </Button>
        {!hasModelConfig && (
          <div style={{ marginTop: 8, textAlign: 'center' }}>
            <Text type="danger" style={{ fontSize: 12 }}>
              请先在左侧选择模型配置
            </Text>
          </div>
        )}
        <div style={{ marginTop: 12, textAlign: 'center' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            内容由AI生成,无法确保真实准确,仅供参考。
          </Text>
        </div>
      </div>
    </div>
  )
}

