import { useState } from 'react'
import { Tabs, Input, Button, Space, Card } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'

const { TextArea } = Input

interface PromptTemplateEditorProps {
  messages: Array<{ role: string; content: string }>
  onChange: (messages: Array<{ role: string; content: string }>) => void
}

export function PromptTemplateEditor({ messages, onChange }: PromptTemplateEditorProps) {
  const handleMessageChange = (index: number, content: string) => {
    const newMessages = [...messages]
    newMessages[index] = { ...newMessages[index], content }
    onChange(newMessages)
  }

  const handleAddMessage = () => {
    // Only allow adding one user message (system + 1 user = 2 messages total)
    if (messages.length < 2) {
      onChange([...messages, { role: 'user', content: '' }])
    }
  }

  const handleRemoveMessage = (index: number) => {
    if (messages.length > 1) {
      onChange(messages.filter((_, i) => i !== index))
    }
  }

  return (
    <div style={{ padding: '16px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: '16px' }}>
        <Tabs
          defaultActiveKey="orchestration"
          items={[
            {
              key: 'orchestration',
              label: '编排',
            },
          ]}
        />
      </div>
      
      <div style={{ flex: 1, overflow: 'auto', paddingTop: '16px' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {messages.map((message, index) => (
            <Card
              key={index}
              size="small"
              title={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{message.role === 'system' ? 'System' : 'User'}</span>
                  {messages.length > 1 && (
                    <Button
                      type="text"
                      danger
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={() => handleRemoveMessage(index)}
                    />
                  )}
                </div>
              }
            >
              <TextArea
                value={message.content}
                onChange={(e) => handleMessageChange(index, e.target.value)}
                placeholder={message.role === 'system' ? '输入 System 消息...' : '输入 User 消息...'}
                rows={6}
                style={{ fontFamily: 'monospace' }}
              />
            </Card>
          ))}
        </Space>
      </div>
      
      <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #f0f0f0' }}>
        <Button
          type="dashed"
          block
          icon={<PlusOutlined />}
          onClick={handleAddMessage}
          disabled={messages.length >= 2} // Only allow system + 1 user message
        >
          添加消息
        </Button>
      </div>
    </div>
  )
}

