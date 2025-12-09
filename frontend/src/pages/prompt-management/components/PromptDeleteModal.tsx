import { Modal, message } from 'antd'
import { ExclamationCircleOutlined } from '@ant-design/icons'
import { promptService } from '../../../services/promptService'
import type { Prompt } from '../../../types/prompt'

interface PromptDeleteModalProps {
  visible: boolean
  data: Prompt | null
  onCancel: () => void
  onOk: () => void
}

export function PromptDeleteModal({
  visible,
  data,
  onCancel,
  onOk,
}: PromptDeleteModalProps) {
  const handleOk = async () => {
    if (!data) return

    try {
      await promptService.delete(data.id)
      message.success(`Prompt "${data.prompt_basic.display_name}" 删除成功`)
      onOk()
    } catch (error: any) {
      message.error('删除失败: ' + (error.message || '未知错误'))
    }
  }

  return (
    <Modal
      title="删除 Prompt"
      open={visible}
      onCancel={onCancel}
      onOk={handleOk}
      cancelText="取消"
      okText="确定"
      okButtonProps={{ danger: true }}
      destroyOnClose
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <ExclamationCircleOutlined style={{ color: '#ff4d4f', fontSize: 22, marginTop: 2 }} />
        <div>
          <p style={{ marginBottom: 8, fontWeight: 500 }}>
            确定要删除 Prompt "{data?.prompt_basic.display_name}" 吗？
          </p>
          <p style={{ color: '#666', margin: 0 }}>
            此操作不可恢复，删除后该 Prompt 的所有数据将被永久删除。
          </p>
        </div>
      </div>
    </Modal>
  )
}

