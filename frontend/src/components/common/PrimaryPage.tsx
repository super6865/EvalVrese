import classNames from 'classnames'
import { ReactNode } from 'react'

interface PrimaryPageProps {
  pageTitle?: string
  filterSlot?: ReactNode
  titleSlot?: ReactNode
  children?: ReactNode
  className?: string
  contentClassName?: string
}

export function PrimaryPage({
  pageTitle,
  filterSlot,
  titleSlot,
  children,
  className,
  contentClassName,
}: PrimaryPageProps) {
  return (
    <div
      className={classNames(
        'pt-2 pb-3 h-full max-h-full flex flex-col',
        className,
      )}
    >
      {(pageTitle || titleSlot) && (
        <div className="flex items-center justify-between py-4 px-6">
          {pageTitle && (
            <div className="text-[20px] font-medium leading-6 coz-fg-plus">
              {pageTitle}
            </div>
          )}
          {titleSlot && <div>{titleSlot}</div>}
        </div>
      )}
      {filterSlot && (
        <div className="box-border coz-fg-secondary pt-1 pb-3 px-6">
          {filterSlot}
        </div>
      )}
      <div
        className={classNames(
          'flex-1 h-full max-h-full overflow-hidden px-6',
          contentClassName,
        )}
      >
        {children}
      </div>
    </div>
  )
}

