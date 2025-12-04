import { Form, Input, Select, Button, Space, Card, message } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import { useState } from 'react'
import type { ArgsSchema, ContentType } from '../../../types/evaluator'

const { TextArea } = Input

interface SchemaEditorProps {
  form: any
  fieldName: 'input_schemas' | 'output_schemas' | string[]  // Support nested paths
  title: string
  initialValues?: ArgsSchema[]
}

export default function SchemaEditor({ form, fieldName, title, initialValues }: SchemaEditorProps) {
  const [schemas, setSchemas] = useState<ArgsSchema[]>(
    initialValues || []
  )

  const addSchema = () => {
    const newSchema: ArgsSchema = {
      key: '',
      support_content_types: ['Text'],
      json_schema: '{"type": "string"}',
    }
    setSchemas([...schemas, newSchema])
  }

  const removeSchema = (index: number) => {
    setSchemas(schemas.filter((_, i) => i !== index))
  }

  const updateSchema = (index: number, field: keyof ArgsSchema, value: any) => {
    const newSchemas = [...schemas]
    ;(newSchemas[index] as any)[field] = value
    setSchemas(newSchemas)
    
    // Support both string and array field names
    if (Array.isArray(fieldName)) {
      const fieldObj: any = {}
      let current = fieldObj
      for (let i = 0; i < fieldName.length - 1; i++) {
        current[fieldName[i]] = {}
        current = current[fieldName[i]]
      }
      current[fieldName[fieldName.length - 1]] = newSchemas
      form.setFieldsValue(fieldObj)
    } else {
      form.setFieldsValue({ [fieldName]: newSchemas })
    }
  }

  return (
    <Card title={title} size="small">
      {schemas.map((schema, index) => (
        <Card key={index} size="small" className="mb-2">
          <Space direction="vertical" className="w-full">
            <Space>
              <Input
                placeholder="字段键名"
                value={schema.key}
                onChange={(e) => updateSchema(index, 'key', e.target.value)}
                style={{ width: 200 }}
              />
              <Select
                mode="multiple"
                placeholder="支持的内容类型"
                value={schema.support_content_types}
                onChange={(value) => updateSchema(index, 'support_content_types', value)}
                style={{ width: 200 }}
              >
                <Select.Option value="Text">Text</Select.Option>
                <Select.Option value="Image">Image</Select.Option>
                <Select.Option value="Audio">Audio</Select.Option>
              </Select>
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                onClick={() => removeSchema(index)}
              />
            </Space>
            <TextArea
              rows={3}
              placeholder='JSON Schema，例如: {"type": "string"}'
              value={schema.json_schema}
              onChange={(e) => updateSchema(index, 'json_schema', e.target.value)}
            />
          </Space>
        </Card>
      ))}
      <Button type="dashed" icon={<PlusOutlined />} onClick={addSchema} block>
        添加 Schema
      </Button>
    </Card>
  )
}

