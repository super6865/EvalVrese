import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Layout, 
  Tree, 
  Button, 
  Input, 
  Tag, 
  message, 
  Progress, 
  Popconfirm,
  Modal,
  Form,
  Empty,
  Spin,
  TreeSelect,
  Tooltip
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  FolderOutlined,
} from '@ant-design/icons'
import type { DataNode } from 'antd/es/tree'
import { CrudListPage } from '../../components/crud'
import { experimentService, Experiment } from '../../services/experimentService'
import { experimentGroupService, ExperimentGroup } from '../../services/experimentGroupService'
import { formatTimestamp } from '../../utils/dateUtils'
import type { ColumnsType } from 'antd/es/table'

const { Sider, Content } = Layout

export default function ExperimentManagementPage() {
  const navigate = useNavigate()
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null)
  const [treeData, setTreeData] = useState<DataNode[]>([])
  const [loading, setLoading] = useState(false)
  const [groupLoading, setGroupLoading] = useState(false)
  const [groupModalVisible, setGroupModalVisible] = useState(false)
  const [editingGroup, setEditingGroup] = useState<ExperimentGroup | null>(null)
  const [form] = Form.useForm()
  const [groupTreeSelectData, setGroupTreeSelectData] = useState<any[]>([])

  useEffect(() => {
    loadGroups()
  }, [])

  const loadGroups = async () => {
    setGroupLoading(true)
    try {
      const response = await experimentGroupService.getTree()
      const groups = response.groups || []
      const treeNodes = convertGroupsToTreeNodes(groups)
      // 添加根节点"全部实验"
      const rootNode: DataNode = {
        title: '全部实验',
        key: 'root',
        icon: <FolderOutlined />,
        children: treeNodes,
      }
      setTreeData([rootNode])
      
      // 转换分组数据为 TreeSelect 格式
      const treeSelectData = convertGroupsToTreeSelectData(groups)
      setGroupTreeSelectData(treeSelectData)
      
      // 查找并默认选中"通用实验"分组
      const findDefaultGroup = (groups: ExperimentGroup[]): number | null => {
        for (const group of groups) {
          if (group.name === '通用实验' && !group.parent_id) {
            return group.id
          }
          if (group.children) {
            const found = findDefaultGroup(group.children)
            if (found) return found
          }
        }
        return null
      }
      
      const defaultGroupId = findDefaultGroup(groups)
      if (defaultGroupId && selectedGroupId === null) {
        setSelectedGroupId(defaultGroupId)
      }
    } catch (error) {
      message.error('加载分组失败')
    } finally {
      setGroupLoading(false)
    }
  }

  const convertGroupsToTreeNodes = (groups: ExperimentGroup[]): DataNode[] => {
    return groups.map(group => ({
      title: group.name,
      key: `group-${group.id}`,
      icon: <FolderOutlined />,
      children: group.children ? convertGroupsToTreeNodes(group.children) : undefined,
      data: group,
    }))
  }

  const convertGroupsToTreeSelectData = (groups: ExperimentGroup[], excludeId?: number, maxDepth: number = 5, currentDepth: number = 0): any[] => {
    if (currentDepth >= maxDepth) {
      return []
    }
    return groups
      .filter(group => {
        // 排除自己（编辑时）
        if (group.id === excludeId) {
          return false
        }
        // 排除"通用实验"分组（不能作为父分组）
        if (group.name === '通用实验' && !group.parent_id) {
          return false
        }
        return true
      })
      .map(group => ({
        title: group.name,
        value: group.id,
        key: group.id,
        children: group.children ? convertGroupsToTreeSelectData(group.children, excludeId, maxDepth, currentDepth + 1) : undefined,
      }))
  }

  const handleTreeSelect = (selectedKeys: React.Key[]) => {
    if (selectedKeys.length === 0) {
      setSelectedGroupId(null)
      return
    }
    
    const key = selectedKeys[0] as string
    if (key === 'root') {
      setSelectedGroupId(null)
    } else if (key.startsWith('group-')) {
      const groupId = parseInt(key.replace('group-', ''))
      setSelectedGroupId(groupId)
    }
  }

  const handleAddGroup = (parentId?: number) => {
    setEditingGroup(null)
    // 重新加载分组树数据
    experimentGroupService.getTree().then(response => {
      const groups = response.groups || []
      const treeSelectData = convertGroupsToTreeSelectData(groups)
      setGroupTreeSelectData(treeSelectData)
    })
    form.setFieldsValue({
      name: '',
      description: '',
      parent_id: parentId,
    })
    setGroupModalVisible(true)
  }

  const handleEditGroup = (group: ExperimentGroup) => {
    setEditingGroup(group)
    // 重新加载分组树数据，排除当前编辑的分组（避免选择自己作为父分组）
    experimentGroupService.getTree().then(response => {
      const groups = response.groups || []
      const treeSelectData = convertGroupsToTreeSelectData(groups, group.id)
      setGroupTreeSelectData(treeSelectData)
    })
    form.setFieldsValue({
      name: group.name,
      description: group.description || '',
      parent_id: group.parent_id,
    })
    setGroupModalVisible(true)
  }

  const handleDeleteGroup = async (groupId: number) => {
    try {
      await experimentGroupService.delete(groupId)
      message.success('分组已删除')
      loadGroups()
      if (selectedGroupId === groupId) {
        setSelectedGroupId(null)
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除分组失败')
    }
  }

  const handleGroupSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingGroup) {
        await experimentGroupService.update(editingGroup.id, {
          name: values.name,
          description: values.description,
          parent_id: values.parent_id,
        })
        message.success('分组已更新')
      } else {
        await experimentGroupService.create({
          name: values.name,
          description: values.description,
          parent_id: values.parent_id,
        })
        message.success('分组已创建')
      }
      setGroupModalVisible(false)
      form.resetFields()
      loadGroups()
    } catch (error: any) {
      if (error.errorFields) {
        // Form validation error
        return
      }
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'default',
      running: 'processing',
      completed: 'success',
      failed: 'error',
      stopped: 'warning',
    }
    return colors[status] || 'default'
  }

  const columns: ColumnsType<Experiment> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Experiment) => (
        <Button
          type="link"
          onClick={() => navigate(`/experiments/${record.id}`)}
          className="p-0"
        >
          {text}
        </Button>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 150,
      render: (progress: number) => (
        <Progress percent={progress} size="small" />
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => {
        if (!text) {
          return '-'
        }
        return (
          <Tooltip title={text} placement="topLeft">
            <span style={{ cursor: 'pointer' }}>{text}</span>
          </Tooltip>
        )
      },
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      sorter: (a, b) =>
        new Date(a.updated_at || 0).getTime() - new Date(b.updated_at || 0).getTime(),
      render: (text: string) => formatTimestamp(text),
    },
  ]

  const titleNode = useMemo(() => {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        padding: '8px 0',
        borderBottom: '1px solid #f0f0f0',
        marginBottom: '8px',
        paddingRight: '0'
      }}>
        <span style={{ fontWeight: 'bold' }}>分组</span>
        <Button
          type="primary"
          size="small"
          icon={<PlusOutlined />}
          onClick={() => handleAddGroup()}
          style={{ flexShrink: 0 }}
        >
          新建分组
        </Button>
      </div>
    )
  }, [])

  return (
    <Layout style={{ height: '100%' }}>
      <Sider width={300} style={{ background: '#fff', borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: '16px' }}>
          {titleNode}
          <style>{`
            /* 树容器宽度约束 */
            .experiment-group-tree {
              max-width: 100% !important;
              overflow: hidden !important;
            }
            /* 紧凑的树形结构样式 */
            .experiment-group-tree .ant-tree-treenode {
              padding: 2px 0 !important;
              max-width: 100% !important;
              box-sizing: border-box !important;
            }
            .experiment-group-tree .ant-tree-switcher {
              width: 16px !important;
              height: 24px !important;
              line-height: 24px !important;
            }
            .experiment-group-tree .ant-tree-iconEle {
              width: 16px !important;
              margin-right: 4px !important;
            }
            .experiment-group-tree .ant-tree-node-content-wrapper {
              display: flex !important;
              align-items: center !important;
              flex: 1 !important;
              min-width: 0 !important;
              max-width: 100% !important;
              padding: 0 4px !important;
              overflow: hidden !important;
            }
            .experiment-group-tree .ant-tree-title {
              flex: 1 !important;
              min-width: 0 !important;
              max-width: 100% !important;
              overflow: hidden !important;
            }
            .experiment-group-tree .ant-tree-indent-unit {
              width: 16px !important;
            }
            /* 分组标题容器 - 使用 flex 布局 */
            .group-title-wrapper {
              display: flex !important;
              align-items: center !important;
              justify-content: space-between !important;
              width: 100% !important;
              min-width: 0 !important;
              max-width: 100% !important;
              gap: 8px !important;
            }
            /* 分组名称样式 */
            .group-name {
              flex: 1 !important;
              min-width: 0 !important;
              max-width: 100% !important;
              overflow: hidden !important;
              text-overflow: ellipsis !important;
              white-space: nowrap !important;
              line-height: 24px !important;
            }
            /* 操作按钮固定在右边 */
            .group-action-buttons {
              flex-shrink: 0 !important;
              display: flex !important;
              align-items: center !important;
              gap: 2px !important;
            }
            .group-action-buttons .ant-btn {
              padding: 2px 4px !important;
              height: 22px !important;
              width: 22px !important;
              min-width: 22px !important;
            }
          `}</style>
          <Spin spinning={groupLoading}>
            {treeData.length > 0 ? (
              <Tree
                showIcon
                defaultExpandAll
                selectedKeys={selectedGroupId === null ? ['root'] : [`group-${selectedGroupId}`]}
                onSelect={handleTreeSelect}
                treeData={treeData}
                className="experiment-group-tree"
                style={{
                  fontSize: '14px',
                  width: '100%'
                }}
                titleRender={((node: DataNode) => {
                  if (node.key === 'root') {
                    return (
                      <Tooltip title={String(node.title)} placement="right">
                        <span className="group-name">{node.title}</span>
                      </Tooltip>
                    )
                  }
                  const group = (node as any).data as ExperimentGroup
                  const isDefaultGroup = group.name === '通用实验' && !group.parent_id
                  return (
                    <div className="group-title-wrapper">
                      <Tooltip title={String(node.title)} placement="right">
                        <span className="group-name">{node.title}</span>
                      </Tooltip>
                      {!isDefaultGroup && (
                        <div 
                          onClick={(e) => e.stopPropagation()} 
                          className="group-action-buttons"
                        >
                          <Button
                            type="text"
                            size="small"
                            icon={<EditOutlined />}
                            onClick={() => handleEditGroup(group)}
                          />
                          <Popconfirm
                            title="确认删除"
                            description="确定要删除这个分组吗？如果分组下有实验或子分组，将无法删除。"
                            onConfirm={() => handleDeleteGroup(group.id)}
                            okText="删除"
                            okType="danger"
                            cancelText="取消"
                          >
                            <Button
                              type="text"
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                            />
                          </Popconfirm>
                        </div>
                      )}
                    </div>
                  )
                }) as any}
              />
            ) : (
              <Empty description="暂无分组" />
            )}
          </Spin>
        </div>
      </Sider>
      <Content style={{ padding: '16px', overflow: 'auto' }}>
        <CrudListPage<Experiment>
          pageTitle="实验管理"
          pageSizeStorageKey="experiment_management_page_size"
          columns={columns}
          loadData={async (params) => {
            setLoading(true)
            try {
              const skip = (params.page_number - 1) * params.page_size
              // 从 params 中获取 group_id（由 additionalFilters 传入）
              // 当 selectedGroupId 为 null 时，group_id 应该是 undefined，显示所有实验
              // 当 selectedGroupId 有值时，group_id 应该是该值，只显示该分组的实验
              const groupId = params.group_id !== undefined && params.group_id !== null ? params.group_id : undefined
              const response = await experimentService.list(
                skip, 
                params.page_size, 
                params.name,
                groupId
              )
              const sortedExperiments = [...(response.experiments || [])].sort((a, b) => {
                const timeA = new Date(a.updated_at || 0).getTime()
                const timeB = new Date(b.updated_at || 0).getTime()
                return timeB - timeA
              })
              return {
                items: sortedExperiments,
                total: response.total || 0,
              }
            } finally {
              setLoading(false)
            }
          }}
          additionalFilters={useMemo(() => ({ group_id: selectedGroupId ?? undefined }), [selectedGroupId])}
          itemsKey="items"
          totalKey="total"
          viewPath={(id) => `/experiments/${id}`}
          searchPlaceholder="搜索实验名称"
          autoRefresh={5000}
        />
      </Content>

      <Modal
        title={editingGroup ? '编辑分组' : '新建分组'}
        open={groupModalVisible}
        onOk={handleGroupSubmit}
        onCancel={() => {
          setGroupModalVisible(false)
          form.resetFields()
        }}
        okText="确定"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="分组名称"
            rules={[{ required: true, message: '请输入分组名称' }]}
          >
            <Input placeholder="请输入分组名称" />
          </Form.Item>
          <Form.Item
            name="parent_id"
            label="父分组"
          >
            <TreeSelect
              placeholder="选择父分组（可选）"
              treeData={groupTreeSelectData}
              allowClear
              showSearch
              treeDefaultExpandAll
              disabled={!!editingGroup}
              filterTreeNode={(inputValue, node) => {
                return node.title?.toString().toLowerCase().includes(inputValue.toLowerCase()) || false
              }}
            />
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea placeholder="请输入分组描述（可选）" rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  )
}

