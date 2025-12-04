import { Space } from 'antd'
import { ReactNode } from 'react'
import classNames from 'classnames'

interface TableHeaderProps {
  actions?: ReactNode
  filters?: ReactNode
  className?: string
}

export function TableHeader({ actions, filters, className }: TableHeaderProps) {
  return (
    <div className={classNames('flex items-center justify-between gap-4', className)}>
      {filters && <Space size="middle">{filters}</Space>}
      {actions && <Space size="middle">{actions}</Space>}
    </div>
  )
}

