import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, Card, message, Space, InputNumber, Checkbox, Divider } from 'antd'
import { datasetService, FieldSchema } from '../../services/datasetService'
import SchemaEditor from './components/SchemaEditor'

export default function DatasetCreatePage() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [fieldSchemas, setFieldSchemas] = useState<FieldSchema[]>([])

  const handleSubmit = async (values: any) => {
    if (fieldSchemas.length === 0) {
      message.warning('请至少添加一个字段')
      return
    }

    const errors: string[] = []
    fieldSchemas.forEach((schema, index) => {
      if (!schema.name) {
        errors.push(`字段 ${index + 1} 缺少名称`)
      }
      if (!schema.key) {
        errors.push(`字段 ${index + 1} 缺少键值`)
      }
    })

    if (errors.length > 0) {
      message.error(errors[0])
      return
    }

    setLoading(true)
    try {
      const createdDataset = await datasetService.create({
        name: values.name,
        description: values.description,
        field_schemas: fieldSchemas,
        spec: {
          max_item_count: values.max_item_count,
          max_field_count: values.max_field_count,
          max_item_size: values.max_item_size,
          max_item_data_nested_depth: values.max_item_data_nested_depth,
        },
        features: {
          editSchema: values.editSchema ?? true,
          repeatedData: values.repeatedData ?? false,
          multiModal: values.multiModal ?? false,
        }
      })
      if (createdDataset && createdDataset.id) {
        message.success('创建成功，请先创建版本')
        navigate(`/datasets/${createdDataset.id}`)
      } else {
        message.error('创建成功，但无法获取数据集ID，请手动刷新列表')
        navigate('/datasets')
      }
    } catch (error: any) {
      message.error('创建失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6">
        <Card title="创建数据集" className="mb-4">
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            autoComplete="off"
            initialValues={{
              editSchema: true,
              repeatedData: false,
              multiModal: false,
            }}
          >
          <Form.Item
            name="name"
            label="数据集名称"
            rules={[{ required: true, message: '请输入数据集名称' }]}
          >
            <Input placeholder="请输入数据集名称" maxLength={50} />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea
              rows={4}
              placeholder="请输入数据集描述（可选）"
              maxLength={200}
              showCount
            />
          </Form.Item>

          <Divider orientation="left">字段配置</Divider>
          
          <Form.Item label=" ">
            <SchemaEditor
              value={fieldSchemas}
              onChange={setFieldSchemas}
              form={form}
            />
          </Form.Item>

          <Divider orientation="left">容量限制（可选）</Divider>

          <div className="grid grid-cols-2 gap-4">
            <Form.Item name="max_item_count" label="最大数据项数量">
              <InputNumber
                min={1}
                placeholder="不限制"
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item name="max_field_count" label="最大字段数量">
              <InputNumber
                min={1}
                max={50}
                placeholder="默认50"
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item name="max_item_size" label="最大数据项大小 (bytes)">
              <InputNumber
                min={1}
                placeholder="不限制"
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item name="max_item_data_nested_depth" label="最大嵌套深度">
              <InputNumber
                min={1}
                max={10}
                placeholder="默认10"
                style={{ width: '100%' }}
              />
            </Form.Item>
          </div>

          <Divider orientation="left">特性配置</Divider>

          <Form.Item name="editSchema" valuePropName="checked">
            <Checkbox>允许编辑 Schema</Checkbox>
          </Form.Item>

          <Form.Item name="repeatedData" valuePropName="checked">
            <Checkbox>支持重复数据</Checkbox>
          </Form.Item>

          <Form.Item name="multiModal" valuePropName="checked">
            <Checkbox>支持多模态内容</Checkbox>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                创建
              </Button>
              <Button onClick={() => navigate('/datasets')}>取消</Button>
            </Space>
          </Form.Item>
          </Form>
        </Card>
      </div>
    </div>
  )
}
