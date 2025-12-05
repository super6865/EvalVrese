import { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { TemplateLayout } from './components/layout/TemplateLayout'
import { Spin } from 'antd'

// 懒加载所有页面组件
const DatasetListPage = lazy(() => import('./pages/dataset/DatasetListPage'))
const DatasetCreatePage = lazy(() => import('./pages/dataset/DatasetCreatePage'))
const DatasetDetailPage = lazy(() => import('./pages/dataset/DatasetDetailPage'))
const EvaluatorListPage = lazy(() => import('./pages/evaluator/EvaluatorListPage'))
const EvaluatorCreatePage = lazy(() => import('./pages/evaluator/EvaluatorCreatePage'))
const EvaluatorDetailPage = lazy(() => import('./pages/evaluator/EvaluatorDetailPage'))
const ExperimentListPage = lazy(() => import('./pages/experiment/ExperimentListPage'))
const ExperimentCreatePage = lazy(() => import('./pages/experiment/ExperimentCreatePage'))
const ExperimentDetailPage = lazy(() => import('./pages/experiment/ExperimentDetailPage'))
const ExperimentComparisonPage = lazy(() => import('./pages/experiment/ExperimentComparisonPage'))
const ObservabilityListPage = lazy(() => import('./pages/observability/ObservabilityListPage'))
const TraceDetailPage = lazy(() => import('./pages/observability/TraceDetailPage'))
const TraceAnalysisPage = lazy(() => import('./pages/trace-analysis/TraceAnalysisPage'))
const EvaluatorRecordListPage = lazy(() => import('./pages/evaluator/EvaluatorRecordListPage'))
const EvaluatorRecordDetailPage = lazy(() => import('./pages/evaluator/EvaluatorRecordDetailPage'))
const ModelConfigPage = lazy(() => import('./pages/model-config/ModelConfigPage'))
const ModelSetPage = lazy(() => import('./pages/model-set/ModelSetPage'))

// 加载中的占位组件
const LoadingFallback = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
    <Spin size="large" />
  </div>
)

function App() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route path="/" element={<TemplateLayout />}>
          <Route index element={<Navigate to="/datasets" replace />} />
          {/* 数据集路由 */}
          <Route path="datasets" element={<DatasetListPage />} />
          <Route path="datasets/create" element={<DatasetCreatePage />} />
          <Route path="datasets/:id" element={<DatasetDetailPage />} />
          {/* 模型集路由 */}
          <Route path="model-sets" element={<ModelSetPage />} />
          {/* 评估器路由 */}
          <Route path="evaluators" element={<EvaluatorListPage />} />
          <Route path="evaluators/create/:type" element={<EvaluatorCreatePage />} />
          <Route path="evaluators/create/:type/:id" element={<EvaluatorCreatePage />} />
          <Route path="evaluators/:id" element={<EvaluatorDetailPage />} />
          {/* 实验路由 */}
          <Route path="experiments" element={<ExperimentListPage />} />
          <Route path="experiments/create" element={<ExperimentCreatePage />} />
          <Route path="experiments/:id" element={<ExperimentDetailPage />} />
          <Route path="experiments/compare" element={<ExperimentComparisonPage />} />
          {/* 可观测性路由 */}
          <Route path="observability" element={<ObservabilityListPage />} />
          <Route path="observability/traces/:traceId" element={<TraceDetailPage />} />
          {/* 链路分析路由 */}
          <Route path="trace-analysis" element={<TraceAnalysisPage />} />
          {/* 评估器记录路由 */}
          <Route path="evaluator-records" element={<EvaluatorRecordListPage />} />
          <Route path="evaluator-records/:id" element={<EvaluatorRecordDetailPage />} />
          {/* 模型配置路由 */}
          <Route path="model-configs" element={<ModelConfigPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

export default App

