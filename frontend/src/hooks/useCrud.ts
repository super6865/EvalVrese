import { useState, useCallback } from 'react'
import { message } from 'antd'

export interface UseCrudOptions<T> {
  listFn: (skip: number, limit: number, search?: string) => Promise<{ items: T[]; total: number }>
  deleteFn?: (id: number) => Promise<void>
  onDeleteSuccess?: () => void
  errorMessage?: string
}

export function useCrud<T extends { id: number }>(options: UseCrudOptions<T>) {
  const { listFn, deleteFn, onDeleteSuccess, errorMessage = '操作失败' } = options
  const [items, setItems] = useState<T[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)

  const loadItems = useCallback(async (skip: number, limit: number, search?: string) => {
    setLoading(true)
    try {
      const response = await listFn(skip, limit, search)
      setItems(response.items || [])
      setTotal(response.total || 0)
    } catch (error: any) {
      message.error(errorMessage + ': ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [listFn, errorMessage])

  const handleDelete = useCallback(async (id: number, itemName?: string) => {
    if (!deleteFn) return
    
    if (window.confirm(itemName ? `确定要删除 "${itemName}" 吗？` : '确定要删除吗？')) {
      try {
        await deleteFn(id)
        message.success('删除成功')
        onDeleteSuccess?.()
      } catch (error: any) {
        message.error('删除失败: ' + (error.message || '未知错误'))
      }
    }
  }, [deleteFn, onDeleteSuccess])

  return {
    items,
    setItems,
    loading,
    setLoading,
    total,
    setTotal,
    loadItems,
    handleDelete,
  }
}

export interface UseListDataOptions<T> {
  fetchFn: (params: any) => Promise<{ items?: T[]; total?: number; [key: string]: any }>
  itemsKey?: string
  totalKey?: string
  errorMessage?: string
}

export function useListData<T>(options: UseListDataOptions<T>) {
  const { fetchFn, itemsKey = 'items', totalKey = 'total', errorMessage = '加载失败' } = options
  const [items, setItems] = useState<T[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)

  const loadData = useCallback(async (params: any) => {
    setLoading(true)
    try {
      const response = await fetchFn(params)
      const items = response[itemsKey] || []
      const total = response[totalKey] || 0
      setItems(items)
      setTotal(total)
    } catch (error: any) {
      message.error(errorMessage + ': ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [fetchFn, itemsKey, totalKey, errorMessage])

  return {
    items,
    setItems,
    loading,
    setLoading,
    total,
    setTotal,
    loadData,
  }
}

