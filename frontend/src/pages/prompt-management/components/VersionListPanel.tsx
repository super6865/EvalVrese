import { Drawer, List, Tag, Typography, Button, Space, message } from 'antd'
import { CheckOutlined } from '@ant-design/icons'
import { promptService } from '../../../services/promptService'
import type { PromptVersion } from '../../../types/prompt'
import { useState, useEffect } from 'react'
import { formatTimestamp } from '../../../utils/dateUtils'

const { Text } = Typography

interface VersionListPanelProps {
  promptId: number
  visible: boolean
  onClose: () => void
  onVersionSelect: (version: PromptVersion) => void
  currentVersion: string | null
  latestVersion: string | null
}

export function VersionListPanel({
  promptId,
  visible,
  onClose,
  onVersionSelect,
  currentVersion,
  latestVersion,
}: VersionListPanelProps) {
  const [versions, setVersions] = useState<PromptVersion[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null)

  useEffect(() => {
    if (visible && promptId) {
      loadVersions()
      // Set selected version to current version when panel opens
      setSelectedVersion(currentVersion)
    }
  }, [visible, promptId, currentVersion])

  const loadVersions = async () => {
    setLoading(true)
    try {
      const data = await promptService.listVersions(promptId)
      setVersions(data)
    } catch (error: any) {
      message.error('加载版本列表失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const handleVersionSelect = (version: PromptVersion) => {
    setSelectedVersion(version.version)
    onVersionSelect(version)
  }

  return (
    <Drawer
      title="版本记录"
      placement="right"
      onClose={onClose}
      open={visible}
      width={360}
    >
      <List
        loading={loading}
        dataSource={versions}
        renderItem={(version) => (
          <List.Item
            style={{
              cursor: 'pointer',
              backgroundColor: selectedVersion === version.version ? '#f0f5ff' : undefined,
            }}
            onClick={() => handleVersionSelect(version)}
          >
            <List.Item.Meta
              title={
                <Space>
                  <Text strong>{version.version}</Text>
                  {latestVersion === version.version && (
                    <Tag color="blue">
                      最新
                    </Tag>
                  )}
                  {currentVersion === version.version && (
                    <Tag color="success" icon={<CheckOutlined />}>
                      当前
                    </Tag>
                  )}
                </Space>
              }
              description={
                <div>
                  {version.description && (
                    <div style={{ marginBottom: 4 }}>
                      <Text type="secondary">{version.description}</Text>
                    </div>
                  )}
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {formatTimestamp(version.created_at || '')}
                  </Text>
                </div>
              }
            />
          </List.Item>
        )}
      />
    </Drawer>
  )
}

