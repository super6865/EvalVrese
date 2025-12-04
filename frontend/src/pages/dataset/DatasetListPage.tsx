import { Button, Tag } from 'antd'
import { useNavigate } from 'react-router-dom'
import { CrudListPage } from '../../components/crud'
import { datasetService, Dataset } from '../../services/datasetService'
import type { ColumnsType } from 'antd/es/table'
import { formatTimestamp } from '../../utils/dateUtils'

export default function DatasetListPage() {
  const navigate = useNavigate()

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'Available':
        return 'green'
      case 'Importing':
      case 'Exporting':
      case 'Indexing':
        return 'blue'
      case 'Deleted':
        return 'red'
      case 'Expired':
        return 'orange'
      default:
        return 'default'
    }
  }

  const columns: ColumnsType<Dataset> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Dataset) => (
        <Button
          type="link"
          onClick={() => navigate(`/datasets/${record.id}`)}
          className="p-0"
        >
          {text}
        </Button>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{status || 'Available'}</Tag>
      ),
    },
    {
      title: '数据项数量',
      dataIndex: 'item_count',
      key: 'item_count',
      width: 120,
      render: (count: number) => count || 0,
    },
    {
      title: '最新版本',
      dataIndex: 'latest_version',
      key: 'latest_version',
      width: 120,
      render: (version: string) => version || '-',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      sorter: (a, b) =>
        new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime(),
      render: (text: string) => formatTimestamp(text),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
    },
  ]

  return (
    <CrudListPage<Dataset>
      pageTitle="数据集管理"
      pageSizeStorageKey="dataset_list_page_size"
      columns={columns}
      loadData={async (params) => {
        const response = await datasetService.list({
          ...params,
          order_by: 'updated_at',
          order_asc: false,
        })
        return {
          items: response.datasets || [],
          total: response.total || 0,
        }
      }}
      itemsKey="items"
      totalKey="total"
      deleteFn={datasetService.delete}
      createPath="/datasets/create"
      viewPath={(id) => `/datasets/${id}`}
      searchPlaceholder="搜索数据集名称或描述"
    />
  )
}

