import { useState, useCallback } from 'react'
import { Form } from 'antd'

export function useModal<T = any>() {
  const [visible, setVisible] = useState(false)
  const [editingItem, setEditingItem] = useState<T | null>(null)
  const [form] = Form.useForm()

  const openModal = useCallback((item?: T) => {
    setEditingItem(item || null)
    if (item) {
      form.setFieldsValue(item)
    } else {
      form.resetFields()
    }
    setVisible(true)
  }, [form])

  const closeModal = useCallback(() => {
    setVisible(false)
    setEditingItem(null)
    form.resetFields()
  }, [form])

  return {
    visible,
    editingItem,
    form,
    openModal,
    closeModal,
    setVisible,
  }
}

