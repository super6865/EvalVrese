import { useNavigate } from 'react-router-dom'
import { Button, Input, Space, Tag, Dropdown, message, Popconfirm } from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  RobotOutlined,
  CodeOutlined,
  EyeOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'
import { CrudListPage } from '../../components/crud'
import { evaluatorService } from '../../services/evaluatorService'
import type { Evaluator, EvaluatorType } from '../../types/evaluator'
import { formatTimestamp } from '../../utils/dateUtils'
import type { ColumnsType } from 'antd/es/table'

export default function EvaluatorListPage() {
  const navigate = useNavigate()

  const handleCreate = (type: EvaluatorType) => {
    navigate(`/evaluators/create/${type}`)
  }

  const handleDelete = async (id: number, name: string, loadData: () => void) => {
    try {
      await evaluatorService.delete(id)
      message.success(`评估器 "${name}" 删除成功`)
      loadData()
    } catch (error: any) {
      message.error('删除失败: ' + (error.message || '未知错误'))
    }
  }

  const columns: ColumnsType<Evaluator> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Evaluator) => (
        <Button
          type="link"
          onClick={() => navigate(`/evaluators/${record.id}`)}
          className="p-0"
        >
          {text}
        </Button>
      ),
    },
    {
      title: '类型',
      dataIndex: 'evaluator_type',
      key: 'evaluator_type',
      width: 120,
      render: (type: string) => (
        <Tag color={type === 'prompt' ? 'blue' : 'green'} icon={type === 'prompt' ? <RobotOutlined /> : <CodeOutlined />}>
          {type === 'prompt' ? 'Prompt' : 'Code'}
        </Tag>
      ),
    },
    {
      title: '最新版本',
      dataIndex: 'latest_version',
      key: 'latest_version',
      width: 120,
      render: (version: string) => version ? <Tag color="blue">{version}</Tag> : '-',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '内置',
      dataIndex: 'builtin',
      key: 'builtin',
      width: 80,
      render: (builtin: boolean) => builtin ? <Tag color="purple">内置</Tag> : '-',
    },
    {
      title: '类型',
      dataIndex: 'box_type',
      key: 'box_type',
      width: 100,
      render: (boxType: string) => {
        if (!boxType) return '-'
        return <Tag color={boxType === 'white' ? 'cyan' : 'default'}>
          {boxType === 'white' ? '白盒' : '黑盒'}
        </Tag>
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
    {
      title: '操作',
      key: 'action',
      width: 180,
    },
  ]

  const createMenuItems: MenuProps['items'] = [
    {
      key: 'prompt',
      label: 'Prompt评估器',
      icon: <RobotOutlined />,
    },
    {
      key: 'code',
      label: 'Code评估器',
      icon: <CodeOutlined />,
    },
  ]

  const handleCreateMenuClick = ({ key }: { key: string }) => {
    handleCreate(key as EvaluatorType)
  }

  return (
    <CrudListPage<Evaluator>
      pageTitle="评估器管理"
      pageSizeStorageKey="evaluator_list_page_size"
      columns={columns}
      loadData={async (params) => {
        const skip = (params.page_number - 1) * params.page_size
        const response = await evaluatorService.list(skip, params.page_size, params.name)
        // 按更新时间降序排序
        const sortedEvaluators = [...(response.evaluators || [])].sort((a, b) => {
          const timeA = new Date(a.updated_at || 0).getTime()
          const timeB = new Date(b.updated_at || 0).getTime()
          return timeB - timeA // 降序
        })
        return {
          items: sortedEvaluators,
          total: response.total || 0,
        }
      }}
      itemsKey="items"
      totalKey="total"
      viewPath={(id) => `/evaluators/${id}`}
      searchPlaceholder="搜索评估器名称"
      customActions={(record: Evaluator, loadData: () => void) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/evaluators/${record.id}`)}
          >
            查看
          </Button>
          {!record.builtin && (
            <Popconfirm
              title={`确定要删除评估器 "${record.name}" 吗？`}
              onConfirm={() => handleDelete(record.id, record.name, loadData)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
              >
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      )}
      filters={(searchText, setSearchText) => (
        <Input
          placeholder="搜索评估器名称"
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
          style={{ width: 250 }}
        />
      )}
      actions={(loadData) => (
        <>
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
          <Dropdown menu={{ items: createMenuItems, onClick: handleCreateMenuClick }}>
            <Button type="primary" icon={<PlusOutlined />}>
              创建评估器
            </Button>
          </Dropdown>
        </>
      )}
    />
  )
}

