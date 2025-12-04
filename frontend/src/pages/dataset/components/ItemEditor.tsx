import { useState, useEffect } from 'react'
import { Form, Input, Button, Modal, Space, Card, Select, message, Tabs, Tag } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import { DatasetItem, FieldSchema, Turn, FieldData, Content } from '../../../services/datasetService'

const { Option } = Select
const { TextArea } = Input
const { TabPane } = Tabs

interface ItemEditorProps {
  visible: boolean
  item?: DatasetItem | null
  fieldSchemas?: FieldSchema[]
  onSave: (item: { data_content: DatasetItem['data_content']; item_key?: string }) => Promise<void>
  onCancel: () => void
}

export default function ItemEditor({ visible, item, fieldSchemas = [], onSave, onCancel }: ItemEditorProps) {
  const [form] = Form.useForm()
  const [turns, setTurns] = useState<Turn[]>([])
  const [itemKey, setItemKey] = useState<string>('')

  useEffect(() => {
    if (visible) {
      if (fieldSchemas && fieldSchemas.length > 0) {
        // 基于 schema 生成字段结构
        const firstTurn = item?.data_content?.turns?.[0]
        const fieldDataList = fieldSchemas.map(schema => {
          // 从 item 中查找匹配的字段
          const existingField = firstTurn?.field_data_list?.find(
            fd => fd.key === schema.key
          )
          
          if (existingField) {
            // 使用现有值，但确保结构符合 schema
            return {
              key: schema.key,
              name: schema.name,
              content: {
                content_type: schema.content_type || existingField.content?.content_type || 'Text',
                format: schema.default_display_format || existingField.content?.format || 'PlainText',
                ...existingField.content, // 保留现有内容值
              }
            }
          } else {
            // 使用 schema 默认值
            return {
              key: schema.key,
              name: schema.name,
              content: {
                content_type: schema.content_type || 'Text',
                format: schema.default_display_format || 'PlainText',
                text: '',
              }
            }
          }
        })
        setTurns([{ field_data_list: fieldDataList }])
      } else if (item?.data_content?.turns && item.data_content.turns.length > 0) {
        // 没有 schema 时，使用现有 item 数据
        setTurns(item.data_content.turns)
      } else {
        // Initialize with empty turn
        setTurns([{ field_data_list: [] }])
      }
      setItemKey(item?.item_key || '')
      form.resetFields()
    }
  }, [visible, item, fieldSchemas, form])

  const addTurn = () => {
    if (fieldSchemas && fieldSchemas.length > 0) {
      // 基于 schema 生成字段结构
      const fieldDataList = fieldSchemas.map(schema => ({
        key: schema.key,
        name: schema.name,
        content: {
          content_type: schema.content_type || 'Text',
          format: schema.default_display_format || 'PlainText',
          text: '',
        }
      }))
      setTurns([...turns, { field_data_list: fieldDataList }])
    } else {
      setTurns([...turns, { field_data_list: [] }])
    }
  }

  const removeTurn = (turnIndex: number) => {
    if (turns.length === 1) {
      message.warning('至少保留一个 Turn')
      return
    }
    setTurns(turns.filter((_, i) => i !== turnIndex))
  }

  const addFieldData = (turnIndex: number) => {
    const newTurns = [...turns]
    if (!newTurns[turnIndex].field_data_list) {
      newTurns[turnIndex].field_data_list = []
    }
    newTurns[turnIndex].field_data_list.push({
      key: '',
      name: '',
      content: {
        content_type: 'Text',
        format: 'PlainText',
        text: '',
      }
    })
    setTurns(newTurns)
  }

  const removeFieldData = (turnIndex: number, fieldIndex: number) => {
    const newTurns = [...turns]
    newTurns[turnIndex].field_data_list = newTurns[turnIndex].field_data_list.filter(
      (_, i) => i !== fieldIndex
    )
    setTurns(newTurns)
  }

  const updateFieldData = (turnIndex: number, fieldIndex: number, field: Partial<FieldData>) => {
    const newTurns = [...turns]
    newTurns[turnIndex].field_data_list[fieldIndex] = {
      ...newTurns[turnIndex].field_data_list[fieldIndex],
      ...field
    }
    setTurns(newTurns)
  }

  const updateContent = (turnIndex: number, fieldIndex: number, content: Partial<Content>) => {
    const newTurns = [...turns]
    const fieldData = newTurns[turnIndex].field_data_list[fieldIndex]
    fieldData.content = {
      ...fieldData.content,
      ...content
    }
    setTurns(newTurns)
  }

  const handleSave = async () => {
    // Validate turns
    for (let i = 0; i < turns.length; i++) {
      const turn = turns[i]
      if (!turn.field_data_list || turn.field_data_list.length === 0) {
        message.warning(`Turn ${i + 1} 至少需要一个字段`)
        return
      }
      for (let j = 0; j < turn.field_data_list.length; j++) {
        const field = turn.field_data_list[j]
        if (!field.key) {
          message.warning(`Turn ${i + 1} 的字段 ${j + 1} 缺少键值`)
          return
        }
        if (!field.content) {
          message.warning(`Turn ${i + 1} 的字段 ${j + 1} 缺少内容`)
          return
        }
      }
    }

    try {
      await onSave({
        data_content: { turns },
        item_key: itemKey || undefined,
      })
      message.success('保存成功')
      onCancel()
    } catch (error: any) {
      message.error('保存失败: ' + (error.message || '未知错误'))
    }
  }

  return (
      <Modal
        title={item ? '编辑数据项' : '添加数据项'}
        open={visible}
        onOk={handleSave}
        onCancel={onCancel}
        width={1000}
        okText="保存"
        cancelText="取消"
        style={{ top: 20 }}
        bodyStyle={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}
      >
      <div className="space-y-4">
        <Form.Item label="Item Key (可选，用于幂等性)">
          <Input
            value={itemKey}
            onChange={(e) => setItemKey(e.target.value)}
            placeholder="留空将自动生成"
          />
        </Form.Item>

        <div>
          <div className="flex justify-between items-center mb-2">
            <h4 className="font-semibold">Turns (多轮对话)</h4>
            <Button
              type="primary"
              size="small"
              icon={<PlusOutlined />}
              onClick={addTurn}
            >
              添加 Turn
            </Button>
          </div>

          <Tabs>
            {turns.map((turn, turnIndex) => (
              <TabPane
                key={turnIndex}
                tab={
                  <span>
                    Turn {turnIndex + 1}
                    {turns.length > 1 && (
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={(e) => {
                          e.stopPropagation()
                          removeTurn(turnIndex)
                        }}
                        className="ml-2"
                      />
                    )}
                  </span>
                }
              >
                <Card size="small" className="mt-2">
                  <div className="space-y-4">
                    {turn.field_data_list?.map((fieldData, fieldIndex) => {
                      const schema = fieldSchemas.find(s => s.key === fieldData.key)
                      
                      return (
                        <Card
                          key={fieldIndex}
                          size="small"
                          title={
                            <div className="flex items-center gap-2">
                              <span>{fieldData.name || schema?.name || `字段 ${fieldIndex + 1}`}</span>
                              {schema?.is_required && <Tag color="red" size="small">必填</Tag>}
                              {fieldSchemas.length > 0 && (
                                <>
                                  <Tag color="blue" size="small">{fieldData.content?.content_type || 'Text'}</Tag>
                                  {fieldData.content?.content_type === 'Text' && (
                                    <Tag size="small">{fieldData.content?.format || 'PlainText'}</Tag>
                                  )}
                                </>
                              )}
                            </div>
                          }
                          className="mb-2"
                        >
                          <div className="space-y-3">
                            {fieldSchemas.length === 0 && (
                              <>
                                <div className="grid grid-cols-2 gap-3">
                                  <div>
                                    <label className="block text-sm font-medium mb-1">字段键 (Key)</label>
                                    <Input
                                      value={fieldData.key}
                                      onChange={(e) => updateFieldData(turnIndex, fieldIndex, { key: e.target.value })}
                                      placeholder="字段键"
                                    />
                                  </div>
                                  <div>
                                    <label className="block text-sm font-medium mb-1">字段名称</label>
                                    <Input
                                      value={fieldData.name}
                                      onChange={(e) => updateFieldData(turnIndex, fieldIndex, { name: e.target.value })}
                                      placeholder="字段名称"
                                    />
                                  </div>
                                </div>

                                <div>
                                  <label className="block text-sm font-medium mb-1">内容类型</label>
                                  <Select
                                    value={fieldData.content?.content_type || 'Text'}
                                    onChange={(value) => updateContent(turnIndex, fieldIndex, { content_type: value })}
                                    style={{ width: '100%' }}
                                  >
                                    <Option value="Text">Text</Option>
                                    <Option value="Image">Image</Option>
                                    <Option value="Audio">Audio</Option>
                                    <Option value="MultiPart">MultiPart</Option>
                                  </Select>
                                </div>

                                <div>
                                  <label className="block text-sm font-medium mb-1">显示格式</label>
                                  <Select
                                    value={fieldData.content?.format || 'PlainText'}
                                    onChange={(value) => updateContent(turnIndex, fieldIndex, { format: value })}
                                    style={{ width: '100%' }}
                                  >
                                    <Option value="PlainText">PlainText</Option>
                                    <Option value="Markdown">Markdown</Option>
                                    <Option value="JSON">JSON</Option>
                                    <Option value="YAML">YAML</Option>
                                    <Option value="Code">Code</Option>
                                  </Select>
                                </div>
                              </>
                            )}

                            {fieldData.content?.content_type === 'Text' && (
                              <div>
                                <label className="block text-sm font-medium mb-1">
                                  文本内容
                                  {schema?.is_required && <span className="text-red-500 ml-1">*</span>}
                                </label>
                                <TextArea
                                  value={fieldData.content?.text || ''}
                                  onChange={(e) => updateContent(turnIndex, fieldIndex, { text: e.target.value })}
                                  rows={4}
                                  placeholder={`请输入${fieldData.name || schema?.name || '文本内容'}`}
                                />
                              </div>
                            )}

                            {fieldData.content?.content_type === 'Image' && (
                              <div className="space-y-2">
                                <div>
                                  <label className="block text-sm font-medium mb-1">
                                    图片 URL
                                    {schema?.is_required && <span className="text-red-500 ml-1">*</span>}
                                  </label>
                                  <Input
                                    value={fieldData.content?.image?.url || ''}
                                    onChange={(e) => updateContent(turnIndex, fieldIndex, {
                                      image: {
                                        ...fieldData.content?.image,
                                        url: e.target.value
                                      }
                                    })}
                                    placeholder="图片 URL"
                                  />
                                </div>
                                <div>
                                  <label className="block text-sm font-medium mb-1">图片名称</label>
                                  <Input
                                    value={fieldData.content?.image?.name || ''}
                                    onChange={(e) => updateContent(turnIndex, fieldIndex, {
                                      image: {
                                        ...fieldData.content?.image,
                                        name: e.target.value
                                      }
                                    })}
                                    placeholder="图片名称（可选）"
                                  />
                                </div>
                              </div>
                            )}

                            {fieldData.content?.content_type === 'Audio' && (
                              <div>
                                <label className="block text-sm font-medium mb-1">
                                  音频 URL
                                  {schema?.is_required && <span className="text-red-500 ml-1">*</span>}
                                </label>
                                <Input
                                  value={fieldData.content?.audio?.url || ''}
                                  onChange={(e) => updateContent(turnIndex, fieldIndex, {
                                    audio: {
                                      ...fieldData.content?.audio,
                                      url: e.target.value
                                    }
                                  })}
                                  placeholder="音频 URL"
                                />
                              </div>
                            )}
                          </div>
                        </Card>
                      )
                    })}

                    {fieldSchemas.length === 0 && (
                      <Button
                        type="dashed"
                        block
                        icon={<PlusOutlined />}
                        onClick={() => addFieldData(turnIndex)}
                      >
                        添加字段
                      </Button>
                    )}
                  </div>
                </Card>
              </TabPane>
            ))}
          </Tabs>
        </div>
      </div>
    </Modal>
  )
}

