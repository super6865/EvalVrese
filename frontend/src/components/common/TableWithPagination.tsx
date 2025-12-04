import { Table, Pagination, Empty } from 'antd'
import type { TableProps, PaginationProps } from 'antd'
import { useState, useEffect, useRef } from 'react'
import classNames from 'classnames'

export const DEFAULT_PAGE_SIZE = 20
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

interface TableWithPaginationProps<T> extends Omit<TableProps<T>, 'dataSource' | 'loading' | 'pagination'> {
  dataSource?: T[]
  loading?: boolean
  total?: number
  current?: number
  pageSize?: number
  onPageChange?: (page: number, pageSize: number) => void
  pageSizeStorageKey?: string
  heightFull?: boolean
  header?: React.ReactNode
  footerWithPagination?: React.ReactNode
  showSizeChanger?: boolean
  empty?: React.ReactNode
  footerClassName?: string
}

function getStoragePageSize(pageSizeStorageKey: string | undefined) {
  if (!pageSizeStorageKey) {
    return undefined
  }
  const pageSize = localStorage.getItem(pageSizeStorageKey)
  if (pageSize && !isNaN(Number(pageSize))) {
    return Number(pageSize)
  }
  return undefined
}

function normalizePageSize(size: number | undefined): number {
  if (!size || isNaN(size) || size <= 0) {
    return DEFAULT_PAGE_SIZE
  }
  if (!PAGE_SIZE_OPTIONS.includes(size)) {
    return DEFAULT_PAGE_SIZE
  }
  return size
}

export function TableWithPagination<T extends Record<string, any>>({
  dataSource = [],
  loading = false,
  total = 0,
  current = 1,
  pageSize = DEFAULT_PAGE_SIZE,
  onPageChange,
  pageSizeStorageKey,
  heightFull = false,
  header,
  footerWithPagination,
  showSizeChanger = true,
  empty,
  footerClassName,
  ...tableProps
}: TableWithPaginationProps<T>) {
  const [localPageSize, setLocalPageSize] = useState(pageSize)
  const tableContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (pageSizeStorageKey) {
      const stored = getStoragePageSize(pageSizeStorageKey)
      if (stored) {
        const normalized = normalizePageSize(stored)
        setLocalPageSize(normalized)
        if (normalized !== stored) {
          localStorage.setItem(pageSizeStorageKey, String(normalized))
        }
      }
    }
  }, [pageSizeStorageKey])

  useEffect(() => {
    if (current > 1 && dataSource.length === 0 && !loading) {
      onPageChange?.(1, localPageSize)
    }
  }, [current, dataSource.length, loading, localPageSize, onPageChange])

  const handlePageChange = (page: number, size: number) => {
    if (pageSizeStorageKey) {
      localStorage.setItem(pageSizeStorageKey, String(size))
    }
    setLocalPageSize(size)
    onPageChange?.(page, size)
  }

  const normalizedPageSize = normalizePageSize(
    getStoragePageSize(pageSizeStorageKey) || localPageSize
  )

  const pagination: PaginationProps = {
    current,
    pageSize: normalizedPageSize,
    total,
    showSizeChanger,
    pageSizeOptions: PAGE_SIZE_OPTIONS.map(String),
    showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
    onChange: handlePageChange,
    onShowSizeChange: handlePageChange,
    locale: {
      items_per_page: ' / 页',
    },
  }

  const tableHeight = heightFull && tableContainerRef.current
    ? tableContainerRef.current.offsetHeight - 56
    : undefined

  return (
    <div
      className={classNames(
        'flex flex-col gap-3',
        heightFull ? 'h-full flex overflow-hidden' : '',
      )}
    >
      {header && <div>{header}</div>}
      <div
        ref={tableContainerRef}
        className={heightFull ? 'flex-1 overflow-hidden' : ''}
      >
        <Table
          {...tableProps}
          dataSource={dataSource}
          loading={loading}
          pagination={false}
          scroll={
            heightFull && tableHeight
              ? {
                  y: tableHeight - 2,
                  ...tableProps.scroll,
                }
              : tableProps.scroll
          }
          locale={{
            emptyText: empty || <Empty description="暂无数据" />,
          }}
        />
      </div>
      {(total > 0 || current > 1) && (
        <div
          className={classNames(
            'shrink-0 flex flex-row-reverse justify-between items-center pt-4 border-t coz-stroke-primary',
            footerClassName,
          )}
        >
          <Pagination {...pagination} />
          {footerWithPagination && <div>{footerWithPagination}</div>}
        </div>
      )}
    </div>
  )
}

