import { Modal, Form, Input, message } from 'antd'
import { useState, useEffect } from 'react'
import type { PromptVersion } from '../../../types/prompt'

interface PromptSubmitModalProps {
  visible: boolean
  onCancel: () => void
  onOk: (version: string, description?: string) => void
  currentVersion?: string
  versions?: PromptVersion[]
}

export function PromptSubmitModal({
  visible,
  onCancel,
  onOk,
  currentVersion,
  versions = [],
}: PromptSubmitModalProps) {
  const [form] = Form.useForm()

  useEffect(() => {
    if (visible) {
      // Generate next version based on all existing versions
      const nextVersion = generateNextVersion(versions)
      form.setFieldsValue({ version: nextVersion })
    }
  }, [visible, versions, form])

  const generateNextVersion = (existingVersions: PromptVersion[]): string => {
    if (existingVersions.length === 0) {
      return 'v1.0'
    }
    
    // Parse all existing versions and find the maximum
    let maxMajor = 0
    let maxMinor = 0
    
    existingVersions.forEach((v) => {
      const versionStr = v.version.trim()
      // Remove 'v' prefix if present
      let cleanVersion = versionStr.toLowerCase().startsWith('v') 
        ? versionStr.substring(1) 
        : versionStr
      
      // Try to parse version number (e.g., "1.0", "1.1", "2.0")
      const parts = cleanVersion.split('.')
      if (parts.length >= 2) {
        const major = parseInt(parts[0]) || 0
        const minor = parseInt(parts[1]) || 0
        if (major > maxMajor || (major === maxMajor && minor > maxMinor)) {
          maxMajor = major
          maxMinor = minor
        }
      } else if (parts.length === 1) {
        const major = parseInt(parts[0]) || 0
        if (major > maxMajor) {
          maxMajor = major
          maxMinor = 0
        }
      }
    })
    
    // Generate next version based on maximum found
    if (maxMajor === 0 && maxMinor === 0) {
      return 'v1.0'
    }
    
    return `v${maxMajor}.${maxMinor + 1}`
  }

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      onOk(values.version, values.description)
      form.resetFields()
    } catch (error) {
      // Validation failed
    }
  }

  const handleCancel = () => {
    form.resetFields()
    onCancel()
  }

  return (
    <Modal
      title="提交新版本"
      open={visible}
      onOk={handleOk}
      onCancel={handleCancel}
      okText="提交"
      cancelText="取消"
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="version"
          label="版本号"
          rules={[
            { required: true, message: '请输入版本号' },
            { pattern: /^v?\d+\.\d+(\.\d+)?$/, message: '版本号格式不正确，例如：v1.0.0' },
          ]}
        >
          <Input placeholder="v1.0.0" />
        </Form.Item>
        <Form.Item
          name="description"
          label="版本描述（可选）"
        >
          <Input.TextArea
            rows={3}
            placeholder="描述本次版本的主要变更..."
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}

