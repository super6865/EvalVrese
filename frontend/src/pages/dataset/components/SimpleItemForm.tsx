import { useState, useEffect } from 'react'
import { Input, Select, Tag } from 'antd'
import { FieldSchema, FieldData, Content } from '../../../services/datasetService'

const { TextArea } = Input
const { Option } = Select

interface SimpleItemFormProps {
  fieldSchemas: FieldSchema[]
  value?: FieldData[]
  onChange?: (fieldDataList: FieldData[]) => void
}

export default function SimpleItemForm({ fieldSchemas, value, onChange }: SimpleItemFormProps) {
  const [fieldDataList, setFieldDataList] = useState<FieldData[]>([])

  useEffect(() => {
    if (value) {
      setFieldDataList(value)
    } else if (fieldSchemas && fieldSchemas.length > 0) {
      // Initialize with schema fields
      const initialData = fieldSchemas.map(schema => ({
        key: schema.key,
        name: schema.name,
        content: {
          content_type: schema.content_type || 'Text',
          format: schema.default_display_format || 'PlainText',
          text: '',
        }
      }))
      setFieldDataList(initialData)
      onChange?.(initialData)
    }
  }, [fieldSchemas, value, onChange])

  const updateFieldData = (index: number, updates: Partial<FieldData>) => {
    const newList = [...fieldDataList]
    newList[index] = {
      ...newList[index],
      ...updates
    }
    setFieldDataList(newList)
    onChange?.(newList)
  }

  const updateContent = (index: number, contentUpdates: Partial<Content>) => {
    const newList = [...fieldDataList]
    newList[index].content = {
      ...newList[index].content,
      ...contentUpdates
    }
    setFieldDataList(newList)
    onChange?.(newList)
  }

  const getDataTypeLabel = (contentType?: string) => {
    switch (contentType) {
      case 'Text':
        return 'String'
      case 'Image':
        return 'Image'
      case 'Audio':
        return 'Audio'
      case 'MultiPart':
        return 'MultiPart'
      default:
        return 'String'
    }
  }

  return (
    <div className="space-y-4">
      {fieldDataList.map((fieldData, index) => {
        const schema = fieldSchemas.find(s => s.key === fieldData.key)
        if (!schema) return null

        return (
          <div key={fieldData.key || index} className="space-y-2">
            {/* Field Header */}
            <div className="flex items-center gap-2 h-6">
              <span className="text-sm font-medium">
                {schema.name}
                {schema.is_required && <span className="text-red-500 ml-1">*</span>}
              </span>
              <Tag color="blue" size="small">
                {getDataTypeLabel(schema.content_type)}
              </Tag>
              {schema.content_type === 'Text' && (
                <Select
                  value={fieldData.content?.format || 'PlainText'}
                  onChange={(value) => updateContent(index, { format: value })}
                  size="small"
                  style={{ width: 100 }}
                >
                  <Option value="PlainText">PlainText</Option>
                  <Option value="Markdown">Markdown</Option>
                  <Option value="JSON">JSON</Option>
                  <Option value="YAML">YAML</Option>
                  <Option value="Code">Code</Option>
                </Select>
              )}
            </div>

            {/* Field Input */}
            {schema.content_type === 'Text' && (
              <TextArea
                value={fieldData.content?.text || ''}
                onChange={(e) => updateContent(index, { text: e.target.value })}
                rows={4}
                placeholder={`请输入${schema.name}`}
                className="w-full"
              />
            )}

            {schema.content_type === 'Image' && (
              <div className="space-y-2">
                <Input
                  value={fieldData.content?.image?.url || ''}
                  onChange={(e) => updateContent(index, {
                    image: {
                      ...fieldData.content?.image,
                      url: e.target.value
                    }
                  })}
                  placeholder="图片 URL"
                />
                <Input
                  value={fieldData.content?.image?.name || ''}
                  onChange={(e) => updateContent(index, {
                    image: {
                      ...fieldData.content?.image,
                      name: e.target.value
                    }
                  })}
                  placeholder="图片名称（可选）"
                />
              </div>
            )}

            {schema.content_type === 'Audio' && (
              <Input
                value={fieldData.content?.audio?.url || ''}
                onChange={(e) => updateContent(index, {
                  audio: {
                    ...fieldData.content?.audio,
                    url: e.target.value
                  }
                })}
                placeholder="音频 URL"
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

