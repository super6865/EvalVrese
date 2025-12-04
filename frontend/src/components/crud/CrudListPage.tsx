import { useState, useEffect, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Input, Space, message } from 'antd'
import { SearchOutlined, ReloadOutlined, PlusOutlined } from '@ant-design/icons'
import { PrimaryPage, TableWithPagination, TableHeader } from '../common'
import { usePagination } from '../../hooks/usePagination'
import type { ColumnsType } from 'antd/es/table'

export interface CrudListPageConfig<T extends { id: number }> {
  pageTitle: string
  pageSizeStorageKey: string
  rowKey?: string | ((record: T) => string)
  columns: ColumnsType<T>
  loadData: (params: {
    page_number: number
    page_size: number
    name?: string
    [key: string]: any
  }) => Promise<{ items: T[]; total: number; [key: string]: any }>
  itemsKey?: string
  totalKey?: string
  deleteFn?: (id: number) => Promise<void>
  createPath?: string
  viewPath?: (id: number) => string
  editPath?: (id: number) => string
  filters?: ReactNode | ((searchText: string, setSearchText: (text: string) => void) => ReactNode)
  actions?: ReactNode | ((loadData: () => void) => ReactNode)
  searchPlaceholder?: string
  errorMessage?: string
  onLoadSuccess?: (data: T[]) => void
  additionalFilters?: Record<string, any>
  onFilterChange?: (filters: Record<string, any>) => void
  rowSelection?: {
    selectedRowKeys: React.Key[]
    onChange: (keys: React.Key[]) => void
  }
  autoRefresh?: number
  customActions?: (record: T, loadData: () => void) => ReactNode
  batchActions?: (selectedRowKeys: React.Key[], loadData: () => void) => ReactNode
}

export function CrudListPage<T extends { id: number }>({
  pageTitle,
  pageSizeStorageKey,
  rowKey = 'id',
  columns,
  loadData,
  itemsKey = 'items',
  totalKey = 'total',
  deleteFn,
  createPath,
  viewPath,
  editPath,
  filters,
  actions,
  searchPlaceholder = '搜索',
  errorMessage = '加载数据失败',
  onLoadSuccess,
  additionalFilters = {},
  onFilterChange,
  rowSelection,
  autoRefresh,
  customActions,
  batchActions,
}: CrudListPageConfig<T>) {
  const navigate = useNavigate()
  const [items, setItems] = useState<T[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [filtersState, setFiltersState] = useState(additionalFilters)
  const { current, pageSize, handlePageChange, setCurrent } = usePagination({
    pageSizeStorageKey,
  })
  const [total, setTotal] = useState(0)

  const loadItems = async () => {
    setLoading(true)
    try {
      const params: any = {
        page_number: current,
        page_size: pageSize,
        ...filtersState,
      }
      if (searchText) {
        params.name = searchText
      }
      const response = await loadData(params)
      const loadedItems = response[itemsKey] || []
      const loadedTotal = response[totalKey] || 0
      setItems(loadedItems)
      setTotal(loadedTotal)
      onLoadSuccess?.(loadedItems)
    } catch (error: any) {
      message.error(errorMessage + ': ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadItems()
    let interval: NodeJS.Timeout | undefined
    if (autoRefresh && autoRefresh > 0) {
      interval = setInterval(loadItems, autoRefresh)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current, pageSize, searchText, filtersState])

  const handleSearch = () => {
    setCurrent(1)
  }

  const handleDelete = async (id: number, itemName?: string) => {
    if (!deleteFn) return
    if (window.confirm(itemName ? `确定要删除 "${itemName}" 吗？` : '确定要删除吗？')) {
      try {
        await deleteFn(id)
        message.success('删除成功')
        loadItems()
      } catch (error: any) {
        message.error('删除失败: ' + (error.message || '未知错误'))
      }
    }
  }

  const handleFilterChange = (newFilters: Record<string, any>) => {
    const updatedFilters = { ...filtersState, ...newFilters }
    setFiltersState(updatedFilters)
    onFilterChange?.(updatedFilters)
    setCurrent(1)
  }

  const defaultFilters = (
    <Input
      placeholder={searchPlaceholder}
      prefix={<SearchOutlined />}
      value={searchText}
      onChange={(e) => setSearchText(e.target.value)}
      onPressEnter={handleSearch}
      allowClear
      style={{ width: 300 }}
    />
  )

  const defaultActions = (
    <>
      <Button icon={<ReloadOutlined />} onClick={loadItems}>
        刷新
      </Button>
      {createPath && (
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate(createPath)}
        >
          创建
        </Button>
      )}
    </>
  )

  const renderFilters = () => {
    if (typeof filters === 'function') {
      return filters(searchText, setSearchText)
    }
    return filters || defaultFilters
  }

  const renderActions = () => {
    const baseActions = typeof actions === 'function' ? actions(loadItems) : (actions || defaultActions)
    const batchActionsNode = batchActions && rowSelection ? batchActions(rowSelection.selectedRowKeys, loadItems) : null
    return (
      <>
        {batchActionsNode}
        {baseActions}
      </>
    )
  }

  // Check if there's already an action column
  const hasActionColumn = columns.some(col => col.key === 'action' || col.title === '操作')
  
  const enhancedColumns: ColumnsType<T> = columns.map((col) => {
    if (col.key === 'action' || col.title === '操作') {
      return {
        ...col,
        render: (_: any, record: T) => {
          // If customActions is provided, use it
          if (customActions) {
            return customActions(record, loadItems)
          }
          // If original render exists, use it
          const originalRender = col.render
          if (originalRender) {
            const rendered = originalRender(_, record, 0)
            if (rendered) return rendered
          }
          // Default actions
          return (
            <Space>
              {viewPath && (
                <Button
                  type="link"
                  size="small"
                  onClick={() => navigate(viewPath(record.id))}
                >
                  查看
                </Button>
              )}
              {editPath && (
                <Button
                  type="link"
                  size="small"
                  onClick={() => navigate(editPath(record.id))}
                >
                  编辑
                </Button>
              )}
              {deleteFn && (
                <Button
                  type="link"
                  size="small"
                  danger
                  onClick={() => handleDelete(record.id, (record as any).name)}
                >
                  删除
                </Button>
              )}
            </Space>
          )
        },
      }
    }
    return col
  })
  
  // If no action column exists and we have actions to show, add one
  if (!hasActionColumn && (viewPath || editPath || deleteFn || customActions)) {
    enhancedColumns.push({
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: T) => {
        if (customActions) {
          return customActions(record, loadItems)
        }
        return (
          <Space>
            {viewPath && (
              <Button
                type="link"
                size="small"
                onClick={() => navigate(viewPath(record.id))}
              >
                查看
              </Button>
            )}
            {editPath && (
              <Button
                type="link"
                size="small"
                onClick={() => navigate(editPath(record.id))}
              >
                编辑
              </Button>
            )}
            {deleteFn && (
              <Button
                type="link"
                size="small"
                danger
                onClick={() => handleDelete(record.id, (record as any).name)}
              >
                删除
              </Button>
            )}
          </Space>
        )
      },
    })
  }

  return (
    <PrimaryPage
      pageTitle={pageTitle}
      filterSlot={<TableHeader filters={renderFilters()} actions={renderActions()} />}
    >
      <TableWithPagination
        columns={enhancedColumns}
        dataSource={items}
        rowKey={rowKey}
        loading={loading}
        total={total}
        current={current}
        pageSize={pageSize}
        onPageChange={handlePageChange}
        pageSizeStorageKey={pageSizeStorageKey}
        heightFull
        rowSelection={rowSelection}
      />
    </PrimaryPage>
  )
}

