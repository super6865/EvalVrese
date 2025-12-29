import { useState, useEffect } from 'react'
import { Form, Input, Select, Switch, Button, Card, Space, Collapse, message, Popconfirm, Tag } from 'antd'
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

// 必需字段定义
const REQUIRED_FIELDS = [
  { key: 'input', name: 'input', description: '评测输入字段（系统必需）' },
  { key: 'reference_output', name: 'reference_output', description: '评测标准输出字段（系统必需）' }
]

const REQUIRED_FIELD_KEYS = REQUIRED_FIELDS.map(f => f.key)

// 检查字段是否为必需字段
const isRequiredField = (key: string): boolean => {
  return REQUIRED_FIELD_KEYS.includes(key)
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

// 创建默认必需字段列表
const createDefaultRequiredFields = (): FieldSchema[] => {
  return REQUIRED_FIELDS.map(field => ({
    ...DEFAULT_FIELD_SCHEMA,
    key: field.key,
    name: field.name,
    description: field.description,
    is_required: true,
  }))
}

// 确保必需字段存在，如果不存在则添加
const ensureRequiredFields = (schemas: FieldSchema[]): FieldSchema[] => {
  const existingKeys = new Set(schemas.map(s => s.key))
  const requiredFieldsToAdd: FieldSchema[] = []
  
  REQUIRED_FIELDS.forEach(field => {
    if (!existingKeys.has(field.key)) {
      requiredFieldsToAdd.push({
        ...DEFAULT_FIELD_SCHEMA,
        key: field.key,
        name: field.name,
        description: field.description,
        is_required: true,
      })
    }
  })
  
  // 将必需字段放在最前面
  return [...requiredFieldsToAdd, ...schemas]
}

export default function SchemaEditor({ value = [], onChange, form }: SchemaEditorProps) {
  // 初始化：如果value为空，使用默认必需字段；否则确保必需字段存在
  const initialSchemas = value.length > 0 
    ? ensureRequiredFields(value)
    : createDefaultRequiredFields()
  
  const [activeKeys, setActiveKeys] = useState<string[]>(initialSchemas.map((_, i) => `${i}`))
  const [schemas, setSchemas] = useState<FieldSchema[]>(initialSchemas)

  // Sync with external value changes
  useEffect(() => {
    if (value.length > 0) {
      const schemasWithRequired = ensureRequiredFields(value)
      setSchemas(schemasWithRequired)
      setActiveKeys(schemasWithRequired.map((_, i) => `${i}`))
    } else {
      const defaultSchemas = createDefaultRequiredFields()
      setSchemas(defaultSchemas)
      setActiveKeys(defaultSchemas.map((_, i) => `${i}`))
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
    const fieldToRemove = schemas[index]
    
    // 检查是否为必需字段
    if (fieldToRemove && isRequiredField(fieldToRemove.key)) {
      message.warning(`无法删除系统必需字段 "${fieldToRemove.name}" (${fieldToRemove.key})`)
      return
    }
    
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
    const currentField = schemas[index]
    const isRequired = currentField && isRequiredField(currentField.key)
    
    // 禁止修改必需字段的key
    if (isRequired && field.key !== undefined && field.key !== currentField.key) {
      message.warning(`无法修改系统必需字段的键名 "${currentField.name}" (${currentField.key})`)
      return
    }
    
    // 禁止修改必需字段的name（但允许修改其他属性如description）
    if (isRequired && field.name !== undefined && field.name !== currentField.name) {
      message.warning(`无法修改系统必需字段的名称 "${currentField.name}" (${currentField.key})`)
      return
    }
    
    const newSchemas = [...schemas]
    newSchemas[index] = { ...newSchemas[index], ...field }
    // Auto-generate key from name if key is empty (only for non-required fields)
    if (!isRequired && !newSchemas[index].key && field.name) {
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
        {schemas.map((schema, index) => {
          const isRequired = isRequiredField(schema.key)
          return (
            <Panel
              key={index}
              header={
                <div className="flex items-center justify-between w-full pr-4">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">
                      {schema.name || `字段 ${index + 1}`}
                    </span>
                    {isRequired && (
                      <Tag color="blue" className="text-xs">系统必需</Tag>
                    )}
                    {schema.is_required && !isRequired && (
                      <span className="text-red-500 text-xs">必填</span>
                    )}
                  </div>
                  <Space onClick={(e) => e.stopPropagation()}>
                    {!isRequired && (
                      <Button
                        type="text"
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => copyField(index)}
                        title="复制"
                      />
                    )}
                    {!isRequired ? (
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
                    ) : (
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        disabled
                        title="系统必需字段，无法删除"
                      />
                    )}
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
                  disabled={isRequired}
                  title={isRequired ? '系统必需字段，无法修改名称' : ''}
                />
              </Form.Item>

              <Form.Item label="字段键 (Key)">
                <Input
                  value={schema.key}
                  onChange={(e) => updateField(index, { key: e.target.value })}
                  placeholder="自动生成，也可手动输入"
                  disabled={isRequired}
                  title={isRequired ? '系统必需字段，无法修改键名' : ''}
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
          )
        })}
      </Collapse>
    </div>
  )
}

