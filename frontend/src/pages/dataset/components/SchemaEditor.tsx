import { useState, useEffect } from 'react'
import { Form, Input, Select, Switch, Button, Card, Space, Collapse, message, Popconfirm } from 'antd'
import { PlusOutlined, DeleteOutlined, CopyOutlined, DownOutlined, RightOutlined } from '@ant-design/icons'
import { FieldSchema } from '../../../services/datasetService'
import type { FormInstance } from 'antd/es/form'

const { Option } = Select
const { Panel } = Collapse
const { TextArea } = Input

interface SchemaEditorProps {
  value?: FieldSchema[]
  onChange?: (schemas: FieldSchema[]) => void
  form?: FormInstance
}

// Content types
const CONTENT_TYPES = [
  { label: 'Text', value: 'Text' },
  { label: 'Image', value: 'Image' },
  { label: 'Audio', value: 'Audio' },
  { label: 'MultiPart', value: 'MultiPart' },
]

// Display formats
const DISPLAY_FORMATS = [
  { label: 'PlainText', value: 'PlainText' },
  { label: 'Markdown', value: 'Markdown' },
  { label: 'JSON', value: 'JSON' },
  { label: 'YAML', value: 'YAML' },
  { label: 'Code', value: 'Code' },
]

const DEFAULT_FIELD_SCHEMA: FieldSchema = {
  key: '',
  name: '',
  description: '',
  content_type: 'Text',
  default_display_format: 'PlainText',
  status: 'Available',
  hidden: false,
  is_required: false,
}

export default function SchemaEditor({ value = [], onChange, form }: SchemaEditorProps) {
  const [activeKeys, setActiveKeys] = useState<string[]>(value.map((_, i) => `${i}`))
  const [schemas, setSchemas] = useState<FieldSchema[]>(value.length > 0 ? value : [DEFAULT_FIELD_SCHEMA])

  // Sync with external value changes
  useEffect(() => {
    if (value.length > 0) {
      setSchemas(value)
      setActiveKeys(value.map((_, i) => `${i}`))
    }
  }, [value])

  const updateSchemas = (newSchemas: FieldSchema[]) => {
    setSchemas(newSchemas)
    onChange?.(newSchemas)
  }

  const addField = () => {
    if (schemas.length >= 50) {
      message.warning('最多支持50个字段')
      return
    }
    const newField = { ...DEFAULT_FIELD_SCHEMA, key: `field_${schemas.length + 1}` }
    const newSchemas = [...schemas, newField]
    updateSchemas(newSchemas)
    setActiveKeys([...activeKeys, `${schemas.length}`])
  }

  const removeField = (index: number) => {
    if (schemas.length === 1) {
      message.warning('至少保留一个字段')
      return
    }
    const newSchemas = schemas.filter((_, i) => i !== index)
    updateSchemas(newSchemas)
    setActiveKeys(activeKeys.filter(key => key !== `${index}`).map(k => {
      const num = parseInt(k)
      return num > index ? `${num - 1}` : k
    }))
  }

  const copyField = (index: number) => {
    if (schemas.length >= 50) {
      message.warning('最多支持50个字段')
      return
    }
    const fieldToCopy = { ...schemas[index], key: `${schemas[index].key}_copy`, name: `${schemas[index].name}_copy` }
    const newSchemas = [...schemas.slice(0, index + 1), fieldToCopy, ...schemas.slice(index + 1)]
    updateSchemas(newSchemas)
    setActiveKeys([...activeKeys, `${index + 1}`])
  }

  const updateField = (index: number, field: Partial<FieldSchema>) => {
    const newSchemas = [...schemas]
    newSchemas[index] = { ...newSchemas[index], ...field }
    // Auto-generate key from name if key is empty
    if (!newSchemas[index].key && field.name) {
      newSchemas[index].key = field.name.toLowerCase().replace(/\s+/g, '_')
    }
    updateSchemas(newSchemas)
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold mb-1">字段配置</h3>
          <p className="text-sm text-gray-500">定义数据集的字段结构，创建后仍可修改</p>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={addField}
          disabled={schemas.length >= 50}
        >
          添加字段
        </Button>
      </div>

      <Collapse
        activeKey={activeKeys}
        onChange={(keys) => setActiveKeys(keys as string[])}
        className="bg-white"
      >
        {schemas.map((schema, index) => (
          <Panel
            key={index}
            header={
              <div className="flex items-center justify-between w-full pr-4">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">
                    {schema.name || `字段 ${index + 1}`}
                  </span>
                  {schema.is_required && (
                    <span className="text-red-500 text-xs">必填</span>
                  )}
                </div>
                <Space onClick={(e) => e.stopPropagation()}>
                  <Button
                    type="text"
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => copyField(index)}
                    title="复制"
                  />
                  <Popconfirm
                    title="确定要删除这个字段吗？"
                    onConfirm={() => removeField(index)}
                    okText="删除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                  >
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      title="删除"
                    />
                  </Popconfirm>
                </Space>
              </div>
            }
          >
            <div className="space-y-4 pt-4">
              <Form.Item label="字段名称" required>
                <Input
                  value={schema.name}
                  onChange={(e) => updateField(index, { name: e.target.value })}
                  placeholder="请输入字段名称"
                />
              </Form.Item>

              <Form.Item label="字段键 (Key)">
                <Input
                  value={schema.key}
                  onChange={(e) => updateField(index, { key: e.target.value })}
                  placeholder="自动生成，也可手动输入"
                />
              </Form.Item>

              <Form.Item label="描述">
                <TextArea
                  value={schema.description}
                  onChange={(e) => updateField(index, { description: e.target.value })}
                  rows={2}
                  placeholder="字段描述（可选）"
                />
              </Form.Item>

              <div className="grid grid-cols-2 gap-4">
                <Form.Item label="内容类型">
                  <Select
                    value={schema.content_type}
                    onChange={(value) => updateField(index, { content_type: value })}
                  >
                    {CONTENT_TYPES.map(type => (
                      <Option key={type.value} value={type.value}>{type.label}</Option>
                    ))}
                  </Select>
                </Form.Item>

                <Form.Item label="显示格式">
                  <Select
                    value={schema.default_display_format}
                    onChange={(value) => updateField(index, { default_display_format: value })}
                  >
                    {DISPLAY_FORMATS.map(format => (
                      <Option key={format.value} value={format.value}>{format.label}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </div>

              <div className="flex gap-4">
                <Form.Item label=" ">
                  <Space>
                    <Switch
                      checked={schema.is_required}
                      onChange={(checked) => updateField(index, { is_required: checked })}
                    />
                    <span>必填字段</span>
                  </Space>
                </Form.Item>

                <Form.Item label=" ">
                  <Space>
                    <Switch
                      checked={schema.hidden}
                      onChange={(checked) => updateField(index, { hidden: checked })}
                    />
                    <span>隐藏字段</span>
                  </Space>
                </Form.Item>
              </div>

              {schema.content_type === 'Image' && (
                <Card size="small" title="多模态配置" className="mt-2">
                  <div className="grid grid-cols-2 gap-4">
                    <Form.Item label="最大文件数量">
                      <Input
                        type="number"
                        value={schema.multi_model_spec?.max_file_count}
                        onChange={(e) => updateField(index, {
                          multi_model_spec: {
                            ...schema.multi_model_spec,
                            max_file_count: parseInt(e.target.value) || undefined
                          }
                        })}
                      />
                    </Form.Item>
                    <Form.Item label="最大文件大小 (bytes)">
                      <Input
                        type="number"
                        value={schema.multi_model_spec?.max_file_size}
                        onChange={(e) => updateField(index, {
                          multi_model_spec: {
                            ...schema.multi_model_spec,
                            max_file_size: parseInt(e.target.value) || undefined
                          }
                        })}
                      />
                    </Form.Item>
                  </div>
                </Card>
              )}
            </div>
          </Panel>
        ))}
      </Collapse>
    </div>
  )
}

