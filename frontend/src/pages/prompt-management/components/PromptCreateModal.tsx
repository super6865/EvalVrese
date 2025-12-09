import { useEffect, useRef } from 'react'
import { Modal, Form, Input, message } from 'antd'
import { promptService } from '../../../services/promptService'
import type { Prompt, PromptCreateRequest, PromptUpdateRequest, PromptCloneRequest } from '../../../types/prompt'

interface PromptCreateModalProps {
  visible: boolean
  mode: 'create' | 'edit' | 'copy'
  data: Prompt | null
  onCancel: () => void
  onOk: () => void
}

export function PromptCreateModal({
  visible,
  mode,
  data,
  onCancel,
  onOk,
}: PromptCreateModalProps) {
  const [form] = Form.useForm()

  useEffect(() => {
    if (visible) {
      if (mode === 'create') {
        form.resetFields()
      } else if (mode === 'edit' && data) {
        form.setFieldsValue({
          prompt_key: data.prompt_key,
          prompt_name: data.prompt_basic.display_name,
          prompt_description: data.prompt_basic.description,
        })
      } else if (mode === 'copy' && data) {
        const promptKey = data.prompt_key.length < 95 ? `${data.prompt_key}_copy` : data.prompt_key
        const promptName =
          data.prompt_basic.display_name.length < 95
            ? `${data.prompt_basic.display_name}_copy`
            : data.prompt_basic.display_name
        form.setFieldsValue({
          prompt_key: promptKey,
          prompt_name: promptName,
          prompt_description: data.prompt_basic.description,
        })
      }
    }
  }, [visible, mode, data, form])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      
      if (mode === 'create') {
        const request: PromptCreateRequest = {
          prompt_key: values.prompt_key,
          prompt_name: values.prompt_name,
          prompt_description: values.prompt_description,
        }
        const response = await promptService.create(request)
        message.success('Prompt 创建成功')
        // TODO: Navigate to prompt detail page when implemented
        // navigate(`/prompt-management/${response.prompt_id}`)
      } else if (mode === 'edit' && data) {
        const request: PromptUpdateRequest = {
          prompt_name: values.prompt_name,
          prompt_description: values.prompt_description,
        }
        await promptService.update(data.id, request)
        message.success('Prompt 更新成功')
      } else if (mode === 'copy' && data) {
        const request: PromptCloneRequest = {
          prompt_id: data.id,
          cloned_prompt_key: values.prompt_key,
          cloned_prompt_name: values.prompt_name,
          cloned_prompt_description: values.prompt_description,
          commit_version: data.prompt_commit?.commit_info?.version,
        }
        const response = await promptService.clone(request)
        message.success('Prompt 复制成功')
        // TODO: Navigate to prompt detail page when implemented
        // navigate(`/prompt-management/${response.cloned_prompt_id}`)
      }
      
      onOk()
    } catch (error: any) {
      if (error.errorFields) {
        // Form validation errors
        return
      }
      message.error(error.message || '操作失败')
    }
  }

  const modalTitle =
    mode === 'edit' ? '编辑 Prompt' : mode === 'copy' ? '创建副本' : '创建 Prompt'

  return (
    <Modal
      title={modalTitle}
      open={visible}
      onCancel={onCancel}
      onOk={handleOk}
      cancelText="取消"
      okText="确定"
      width={900}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        preserve={false}
      >
        <Form.Item
          label="Prompt Key"
          name="prompt_key"
          rules={[
            { required: true, message: '请输入 Prompt Key' },
            {
              validator: (_rule, value) => {
                if (value && !/^[a-zA-Z][a-zA-Z0-9_.]*$/.test(value)) {
                  return Promise.reject(
                    new Error('仅支持英文字母、数字、"_"、"."，且仅支持英文字母开头')
                  )
                }
                return Promise.resolve()
              },
            },
          ]}
        >
          <Input
            placeholder="请输入 Prompt key"
            maxLength={100}
            disabled={mode === 'edit'}
          />
        </Form.Item>

        <Form.Item
          label="Prompt 名称"
          name="prompt_name"
          rules={[
            { required: true, message: '请输入 Prompt 名称' },
            {
              validator: (_rule, value) => {
                if (value && !/^[\u4e00-\u9fa5a-zA-Z0-9_.-]+$/.test(value)) {
                  return Promise.reject(
                    new Error('仅支持英文字母、数字、中文，"-"，"_"，"."，且仅支持英文字母、数字、中文开头')
                  )
                }
                if (value && /^[_.-]/.test(value)) {
                  return Promise.reject(
                    new Error('仅支持英文字母、数字、中文，"-"，"_"，"."，且仅支持英文字母、数字、中文开头')
                  )
                }
                return Promise.resolve()
              },
            },
          ]}
        >
          <Input placeholder="请输入 Prompt 名称" maxLength={100} />
        </Form.Item>

        <Form.Item
          label="Prompt 描述"
          name="prompt_description"
        >
          <Input.TextArea
            placeholder="请输入 Prompt 描述"
            maxLength={500}
            showCount
            rows={4}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}

