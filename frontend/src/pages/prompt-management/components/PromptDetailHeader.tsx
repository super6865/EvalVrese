import { useState } from 'react'
import { Button, Space, Tag, Typography, Dropdown, Modal, message } from 'antd'
import {
  ArrowLeftOutlined,
  HistoryOutlined,
  DeleteOutlined,
  MoreOutlined,
  CheckCircleOutlined,
  EditOutlined,
} from '@ant-design/icons'
import type { Prompt, PromptVersion } from '../../../types/prompt'
import { PromptSubmitModal } from './PromptSubmitModal'
import { formatTimestamp } from '../../../utils/dateUtils'

const { Text } = Typography

interface PromptDetailHeaderProps {
  prompt: Prompt
  onBack: () => void
  onVersionListToggle: () => void
  onSubmitVersion: (version: string, description?: string) => void
  onDelete: () => void
  versions?: PromptVersion[]
}

export function PromptDetailHeader({
  prompt,
  onBack,
  onVersionListToggle,
  onSubmitVersion,
  onDelete,
  versions = [],
}: PromptDetailHeaderProps) {
  const [submitModalVisible, setSubmitModalVisible] = useState(false)
  const [deleteModalVisible, setDeleteModalVisible] = useState(false)

  const isDraftModified = prompt.prompt_draft?.draft_info?.is_modified
  const hasDraft = !!prompt.prompt_draft
  const currentVersion = prompt.prompt_commit?.commit_info?.version || 
                        prompt.prompt_draft?.draft_info?.base_version ||
                        prompt.prompt_basic.latest_version

  const handleDelete = () => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除 Prompt "${prompt.prompt_basic.display_name}" 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        onDelete()
        setDeleteModalVisible(false)
      },
    })
  }

  const menuItems = [
    {
      key: 'delete',
      label: <Text type="danger">删除</Text>,
      icon: <DeleteOutlined />,
      onClick: handleDelete,
    },
  ]

  return (
    <div
      style={{
        padding: '12px 24px',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: '#fff',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={onBack}
        >
          返回
        </Button>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Text strong style={{ fontSize: 16 }}>
              {prompt.prompt_basic.display_name}
            </Text>
            {isDraftModified ? (
              <Tag color="warning" icon={<EditOutlined />}>
                修改未提交
              </Tag>
            ) : hasDraft ? (
              <Tag color="success" icon={<CheckCircleOutlined />}>
                已提交 {currentVersion}
              </Tag>
            ) : null}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {prompt.prompt_key}
            </Text>
            {prompt.prompt_draft?.draft_info?.updated_at && (
              <>
                <Text type="secondary" style={{ fontSize: 12 }}>•</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  草稿保存于 {formatTimestamp(prompt.prompt_draft.draft_info.updated_at)}
                </Text>
              </>
            )}
          </div>
        </div>
      </div>

      <Space>
        <Button onClick={onVersionListToggle}>
          版本记录
        </Button>
        {hasDraft && (
          <Button
            type="primary"
            onClick={() => setSubmitModalVisible(true)}
            disabled={!isDraftModified}
          >
            提交新版
          </Button>
        )}
        <Dropdown
          menu={{ items: menuItems }}
          trigger={['click']}
        >
          <Button icon={<MoreOutlined />} />
        </Dropdown>
      </Space>

      <PromptSubmitModal
        visible={submitModalVisible}
        onCancel={() => setSubmitModalVisible(false)}
        onOk={(version, description) => {
          onSubmitVersion(version, description)
          setSubmitModalVisible(false)
        }}
        currentVersion={currentVersion}
        versions={versions}
      />
    </div>
  )
}

