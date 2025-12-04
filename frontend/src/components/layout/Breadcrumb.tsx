import { useState, useEffect, useMemo, useRef } from 'react'
import { Breadcrumb as AntBreadcrumb } from 'antd'
import { useLocation, Link } from 'react-router-dom'
import { datasetService } from '../../services/datasetService'
import { evaluatorService } from '../../services/evaluatorService'
import { experimentService } from '../../services/experimentService'

const breadcrumbNameMap: Record<string, string> = {
  '/datasets': '数据集',
  '/datasets/create': '创建数据集',
  '/evaluators': '评估器',
  '/evaluators/create': '创建评估器',
  '/evaluator-records': '评估器记录',
  '/experiments': '实验',
  '/experiments/create': '创建实验',
  '/experiments/compare': '实验对比',
  '/model-sets': '模型集',
  '/model-configs': '模型配置',
  '/observability': '链路追踪',
  '/trace-analysis': '链路分析',
}

export function Breadcrumb() {
  const location = useLocation()
  const pathSnippets = location.pathname.split('/').filter((i) => i)
  const [detailNames, setDetailNames] = useState<Record<string, string>>({})
  const detailNamesRef = useRef<Record<string, string>>({})
  const loadingPathsRef = useRef<Set<string>>(new Set())

  // 同步ref和state
  useEffect(() => {
    detailNamesRef.current = detailNames
  }, [detailNames])

  // 检测详情页路径并加载名称
  useEffect(() => {
    const loadDetailName = async (path: string, type: 'dataset' | 'evaluator' | 'experiment', id: string) => {
      // 如果正在加载或已加载，跳过
      if (loadingPathsRef.current.has(path) || detailNamesRef.current[path]) {
        return
      }

      // 检查ID是否为有效数字
      const numericId = Number(id)
      if (isNaN(numericId)) {
        return
      }

      // 标记为正在加载
      loadingPathsRef.current.add(path)

      try {
        let name: string
        switch (type) {
          case 'dataset':
            const dataset = await datasetService.get(numericId)
            name = dataset.name
            break
          case 'evaluator':
            const evaluator = await evaluatorService.get(numericId)
            name = evaluator.name
            break
          case 'experiment':
            const experiment = await experimentService.get(numericId)
            name = experiment.name
            break
          default:
            loadingPathsRef.current.delete(path)
            return
        }
        setDetailNames(prev => {
          // 避免重复设置
          if (prev[path]) {
            return prev
          }
          return { ...prev, [path]: name }
        })
      } catch (error) {
        // 加载失败时，保持显示ID
        console.error(`Failed to load ${type} name:`, error)
      } finally {
        loadingPathsRef.current.delete(path)
      }
    }

    // 检测详情页路径
    if (pathSnippets.length >= 2) {
      const [type, id] = pathSnippets
      const path = `/${type}/${id}`

      // 如果已加载名称或正在加载，跳过
      if (detailNamesRef.current[path] || loadingPathsRef.current.has(path)) {
        return
      }

      if (type === 'datasets' && id) {
        loadDetailName(path, 'dataset', id)
      } else if (type === 'evaluators' && id) {
        loadDetailName(path, 'evaluator', id)
      } else if (type === 'experiments' && id) {
        loadDetailName(path, 'experiment', id)
      }
    }
  }, [location.pathname])

  const breadcrumbItems = useMemo(() => {
    const items = [
      {
        title: <Link to="/" className="coz-fg-secondary">首页</Link>,
      },
    ]

    // 检测是否是 observability/traces/:traceId 路径，如果是则过滤掉 "traces"
    const filteredSnippets = [...pathSnippets]
    const isObservabilityTracePath = 
      pathSnippets.length >= 3 && 
      pathSnippets[0] === 'observability' && 
      pathSnippets[1] === 'traces'
    
    if (isObservabilityTracePath) {
      // 移除 "traces" 片段
      filteredSnippets.splice(1, 1)
    }

    filteredSnippets.forEach((_, index) => {
      // 构建URL：对于 observability/traces/:traceId，需要特殊处理
      let url: string
      if (isObservabilityTracePath && index === 1) {
        // traceId 的完整URL应该是 /observability/traces/:traceId
        url = `/observability/traces/${pathSnippets[2]}`
      } else {
        url = `/${filteredSnippets.slice(0, index + 1).join('/')}`
      }
      
      const isLast = index === filteredSnippets.length - 1
      const snippet = filteredSnippets[index]
      
      // 检查是否是详情页路径
      let title: string = breadcrumbNameMap[url] || snippet
      
      // 如果是详情页路径且已加载名称，使用名称
      if (isLast && detailNames[url]) {
        title = detailNames[url]
      }

      items.push({
        title: isLast ? (
          <span className="coz-fg-primary">{title}</span>
        ) : (
          <Link to={url} className="coz-fg-secondary hover:coz-fg-primary transition-colors">
            {title}
          </Link>
        ),
      })
    })

    return items
  }, [pathSnippets, detailNames])

  return (
    <div className="h-[56px] flex items-center justify-between px-6 border-0 border-b border-solid coz-stroke-primary">
      <AntBreadcrumb
        separator={
          <div className="rotate-[22deg] coz-fg-dim inline-block mx-2">/</div>
        }
        items={breadcrumbItems}
        className="[&_.ant-breadcrumb-link]:!text-[13px]"
      />
    </div>
  )
}

