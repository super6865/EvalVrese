import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Space, Tag, Typography, Input, message, Tooltip } from 'antd'
import {
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  EyeOutlined,
  DeleteOutlined,
  CopyOutlined,
  HistoryOutlined,
  CopyOutlined as CopyIcon,
} from '@ant-design/icons'
import { CrudListPage } from '../../components/crud'
import { promptService } from '../../services/promptService'
import type { Prompt } from '../../types/prompt'
import { formatTimestamp } from '../../utils/dateUtils'
import type { ColumnsType } from 'antd/es/table'
import { PromptCreateModal } from './components/PromptCreateModal'
import { PromptDeleteModal } from './components/PromptDeleteModal'

const { Text } = Typography

export default function PromptManagementPage() {
  const navigate = useNavigate()
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [createModalMode, setCreateModalMode] = useState<'create' | 'edit' | 'copy'>('create')
  const [createModalData, setCreateModalData] = useState<Prompt | null>(null)
  const [deleteModalVisible, setDeleteModalVisible] = useState(false)
  const [deleteModalData, setDeleteModalData] = useState<Prompt | null>(null)
  const loadDataRef = useRef<(() => void) | null>(null)

  const handleCreate = () => {
    setCreateModalMode('create')
    setCreateModalData(null)
    setCreateModalVisible(true)
  }

  const handleEdit = (prompt: Prompt) => {
    setCreateModalMode('edit')
    setCreateModalData(prompt)
    setCreateModalVisible(true)
  }

  const handleCopy = (prompt: Prompt) => {
    setCreateModalMode('copy')
    setCreateModalData(prompt)
    setCreateModalVisible(true)
  }

  const handleDelete = (prompt: Prompt) => {
    setDeleteModalData(prompt)
    setDeleteModalVisible(true)
  }

  const handleViewHistory = (prompt: Prompt) => {
    message.info('调用记录功能暂未开发')
  }

  const handleCreateModalOk = () => {
    setCreateModalVisible(false)
    loadDataRef.current?.()
  }

  const handleDeleteModalOk = () => {
    setDeleteModalVisible(false)
    setDeleteModalData(null)
    loadDataRef.current?.()
  }

  const columns: ColumnsType<Prompt> = [
    {
      title: 'Prompt Key',
      dataIndex: 'prompt_key',
      key: 'prompt_key',
      width: 260,
      render: (key: string, record: Prompt) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Text
            copyable={{
              text: key,
              tooltips: ['复制 Prompt Key', '已复制'],
            }}
            style={{ fontSize: 13, flex: 1, overflow: 'hidden' }}
            ellipsis={{ tooltip: key }}
          >
            {key}
          </Text>
          {record.prompt_draft?.draft_info?.is_modified && (
            <Tag color="warning" size="small">
              修改未提交
            </Tag>
          )}
        </div>
      ),
    },
    {
      title: 'Prompt 名称',
      dataIndex: ['prompt_basic', 'display_name'],
      key: 'display_name',
      width: 200,
      render: (text: string) => (
        <Text ellipsis={{ tooltip: text }} style={{ fontSize: 'inherit' }}>
          {text}
        </Text>
      ),
    },
    {
      title: 'Prompt 描述',
      dataIndex: ['prompt_basic', 'description'],
      key: 'description',
      width: 220,
      render: (text: string) => (
        <Text
          ellipsis={{
            tooltip: {
              title: text || '-',
              overlayStyle: { maxWidth: 400 },
            },
          }}
          style={{ fontSize: 'inherit' }}
        >
          {text || '-'}
        </Text>
      ),
    },
    {
      title: '最新版本',
      dataIndex: ['prompt_basic', 'latest_version'],
      key: 'latest_version',
      width: 140,
      render: (version: string) => (version ? <Tag color="blue">{version}</Tag> : '-'),
    },
    {
      title: '创建人',
      dataIndex: 'user',
      key: 'user',
      width: 140,
      render: (user: Prompt['user']) => {
        if (!user) return '-'
        return (
          <Space>
            {user.avatar_url && (
              <img
                src={user.avatar_url}
                alt={user.nick_name || ''}
                style={{ width: 20, height: 20, borderRadius: '50%' }}
              />
            )}
            <span>{user.nick_name || user.user_id || '-'}</span>
          </Space>
        )
      },
    },
    {
      title: '更新时间',
      dataIndex: ['prompt_basic', 'updated_at'],
      key: 'updated_at',
      width: 180,
      sorter: (a, b) =>
        new Date(a.prompt_basic.updated_at || 0).getTime() - new Date(b.prompt_basic.updated_at || 0).getTime(),
      render: (text: string) => formatTimestamp(text),
    },
    {
      title: '操作',
      key: 'action',
      width: 350,
      fixed: 'right',
    },
  ]

  return (
    <>
      <CrudListPage<Prompt>
        pageTitle="Prompt 管理"
        pageSizeStorageKey="prompt_list_page_size"
        columns={columns}
        loadData={async (params) => {
          const response = await promptService.list({
            page_number: params.page_number,
            page_size: params.page_size,
            key_word: params.name,
            order_by: params.order_by as 'created_at' | 'committed_at' | undefined,
            asc: params.asc,
          })
          return {
            items: response.prompts || [],
            total: response.total || 0,
          }
        }}
        itemsKey="items"
        totalKey="total"
        searchPlaceholder="搜索 Prompt Key 或 Prompt 名称"
        customActions={(record: Prompt, loadData: () => void) => {
          // Store loadData ref for modal callbacks
          if (!loadDataRef.current) {
            loadDataRef.current = loadData
          }
          return (
            <Space size="small">
              <Button
                type="link"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => {
                  navigate(`/prompt-management/${record.id}`)
                }}
              >
                详情
              </Button>
              <Button
                type="link"
                size="small"
                icon={<HistoryOutlined />}
                onClick={() => handleViewHistory(record)}
              >
                调用记录
              </Button>
              <Button
                type="link"
                size="small"
                icon={<CopyIcon />}
                onClick={() => handleCopy(record)}
              >
                复制
              </Button>
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(record)}
              >
                删除
              </Button>
            </Space>
          )
        }}
        filters={(searchText, setSearchText) => (
          <Input
            placeholder="搜索 Prompt Key 或 Prompt 名称"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            allowClear
            style={{ width: 360 }}
          />
        )}
        actions={(loadData) => {
          // Store loadData ref
          loadDataRef.current = loadData
          return (
            <>
              <Button icon={<ReloadOutlined />} onClick={loadData}>
                刷新
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                创建 Prompt
              </Button>
            </>
          )
        }}
        onRow={(record) => ({
          onClick: () => {
            // TODO: Navigate to prompt detail page when implemented
            // navigate(`/prompt-management/${record.id}`)
          },
          style: { cursor: 'pointer' },
        })}
        onChange={({ sorter }) => {
          // Handle sorting if needed
          if (sorter && 'field' in sorter) {
            const field = sorter.field as string
            if (field === 'updated_at') {
              // Sorting is handled by the API
            }
          }
        }}
      />
      <PromptCreateModal
        visible={createModalVisible}
        mode={createModalMode}
        data={createModalData}
        onCancel={() => {
          setCreateModalVisible(false)
          setCreateModalData(null)
        }}
        onOk={handleCreateModalOk}
      />
      <PromptDeleteModal
        visible={deleteModalVisible}
        data={deleteModalData}
        onCancel={() => {
          setDeleteModalVisible(false)
          setDeleteModalData(null)
        }}
        onOk={handleDeleteModalOk}
      />
    </>
  )
}
