import { useState, useEffect } from 'react'

export interface UsePaginationOptions {
  defaultPageSize?: number
  pageSizeStorageKey?: string
}

export function usePagination(options: UsePaginationOptions = {}) {
  const { defaultPageSize = 20, pageSizeStorageKey } = options
  
  const [current, setCurrent] = useState(1)
  const [pageSize, setPageSize] = useState(() => {
    if (pageSizeStorageKey) {
      const stored = localStorage.getItem(pageSizeStorageKey)
      if (stored) {
        const size = parseInt(stored, 10)
        if ([10, 20, 50, 100].includes(size)) {
          return size
        }
      }
    }
    return defaultPageSize
  })

  useEffect(() => {
    if (pageSizeStorageKey) {
      localStorage.setItem(pageSizeStorageKey, String(pageSize))
    }
  }, [pageSize, pageSizeStorageKey])

  const handlePageChange = (page: number, size: number) => {
    setCurrent(page)
    setPageSize(size)
  }

  return {
    current,
    pageSize,
    setCurrent,
    setPageSize,
    handlePageChange,
  }
}

