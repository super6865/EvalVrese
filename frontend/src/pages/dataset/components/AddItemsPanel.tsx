import { useState, useEffect } from 'react'
import { Drawer, Button, Collapse, message, Space } from 'antd'
import { CopyOutlined, DeleteOutlined, PlusOutlined, DownOutlined, RightOutlined } from '@ant-design/icons'
import { FieldSchema, Dataset } from '../../../services/datasetService'
import SimpleItemForm from './SimpleItemForm'
import { datasetService } from '../../../services/datasetService'

const { Panel } = Collapse

interface AddItemsPanelProps {
  visible: boolean
  dataset: Dataset | null
  fieldSchemas: FieldSchema[]
  versionId?: number | null
  onClose: () => void
  onSuccess: () => void
}

interface ItemData {
  key: string
  fieldDataList: any[]
}

export default function AddItemsPanel({
  visible,
  dataset,
  fieldSchemas,
  versionId,
  onClose,
  onSuccess
}: AddItemsPanelProps) {
  const [items, setItems] = useState<ItemData[]>([])
  const [activeKeys, setActiveKeys] = useState<string[]>(['0'])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (visible && fieldSchemas.length > 0) {
      // Initialize with one empty item
      const initialItem: ItemData = {
        key: '0',
        fieldDataList: fieldSchemas.map(schema => ({
          key: schema.key,
          name: schema.name,
          content: {
            content_type: schema.content_type || 'Text',
            format: schema.default_display_format || 'PlainText',
            text: '',
          }
        }))
      }
      setItems([initialItem])
      setActiveKeys(['0'])
    }
  }, [visible, fieldSchemas])

  const handleAddItem = () => {
    if (items.length >= 10) {
      message.warning('最多只能添加10个数据项')
      return
    }
    const newKey = `${items.length}`
    const newItem: ItemData = {
      key: newKey,
      fieldDataList: fieldSchemas.map(schema => ({
        key: schema.key,
        name: schema.name,
        content: {
          content_type: schema.content_type || 'Text',
          format: schema.default_display_format || 'PlainText',
          text: '',
        }
      }))
    }
    setItems([...items, newItem])
    setActiveKeys([...activeKeys, newKey])
  }

  const handleCopyItem = (index: number) => {
    if (items.length >= 10) {
      message.warning('最多只能添加10个数据项')
      return
    }
    const copiedItem = {
      ...items[index],
      key: `${items.length}`
    }
    const newItems = [...items]
    newItems.splice(index + 1, 0, copiedItem)
    setItems(newItems)
    setActiveKeys([...activeKeys, copiedItem.key])
  }

  const handleDeleteItem = (index: number) => {
    if (items.length === 1) {
      message.warning('至少保留一个数据项')
      return
    }
    const newItems = items.filter((_, i) => i !== index)
    setItems(newItems)
    setActiveKeys(activeKeys.filter(key => key !== `${index}`))
  }

  const handleItemChange = (index: number, fieldDataList: any[]) => {
    const newItems = [...items]
    newItems[index].fieldDataList = fieldDataList
    setItems(newItems)
  }

  const handleSubmit = async () => {
    if (!dataset) return

    // Validate items
    for (let i = 0; i < items.length; i++) {
      const item = items[i]
      for (const fieldData of item.fieldDataList) {
        const schema = fieldSchemas.find(s => s.key === fieldData.key)
        if (schema?.is_required) {
          if (fieldData.content?.content_type === 'Text' && !fieldData.content?.text) {
            message.error(`数据项 ${i + 1} 的字段 "${schema.name}" 是必填项`)
            return
          }
          if (fieldData.content?.content_type === 'Image' && !fieldData.content?.image?.url) {
            message.error(`数据项 ${i + 1} 的字段 "${schema.name}" 是必填项`)
            return
          }
          if (fieldData.content?.content_type === 'Audio' && !fieldData.content?.audio?.url) {
            message.error(`数据项 ${i + 1} 的字段 "${schema.name}" 是必填项`)
            return
          }
        }
      }
    }

    setLoading(true)
    try {
      // Convert to backend format
      const itemsToCreate = items.map(item => ({
        data_content: {
          turns: [{
            field_data_list: item.fieldDataList
          }]
        }
      }))

      const response = await datasetService.batchCreateItems(dataset.id, versionId, {
        items: itemsToCreate,
        skip_invalid_items: false,
        allow_partial_add: false,
      })

      if (response.errors && response.errors.length > 0) {
        message.error('创建失败: ' + response.errors[0].summary)
        return
      }

      const successCount = items.length
      message.success(`成功添加 ${successCount} 个数据项`)
      onSuccess()
      onClose()
    } catch (error: any) {
      message.error('创建失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Drawer
      title="添加数据"
      placement="right"
      width={880}
      open={visible}
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" loading={loading} onClick={handleSubmit}>
            添加
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <Collapse
          activeKey={activeKeys}
          onChange={setActiveKeys}
          className="mb-4"
        >
          {items.map((item, index) => (
            <Panel
              key={item.key}
              header={
                <div className="flex items-center justify-between w-full pr-4">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">数据项 {index + 1}</span>
                    {activeKeys.includes(item.key) ? (
                      <DownOutlined className="text-xs" />
                    ) : (
                      <RightOutlined className="text-xs" />
                    )}
                  </div>
                  <Space onClick={(e) => e.stopPropagation()}>
                    <Button
                      type="text"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() => handleCopyItem(index)}
                    />
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => handleDeleteItem(index)}
                    />
                  </Space>
                </div>
              }
            >
              <SimpleItemForm
                fieldSchemas={fieldSchemas}
                value={item.fieldDataList}
                onChange={(fieldDataList) => handleItemChange(index, fieldDataList)}
              />
            </Panel>
          ))}
        </Collapse>

        <Button
          type="dashed"
          block
          icon={<PlusOutlined />}
          onClick={handleAddItem}
          disabled={items.length >= 10}
        >
          添加数据项 {items.length}/10
        </Button>
      </div>
    </Drawer>
  )
}

