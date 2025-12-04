import { Routes, Route, Navigate } from 'react-router-dom'
import { TemplateLayout } from './components/layout/TemplateLayout'
import DatasetListPage from './pages/dataset/DatasetListPage'
import DatasetCreatePage from './pages/dataset/DatasetCreatePage'
import DatasetDetailPage from './pages/dataset/DatasetDetailPage'
import EvaluatorListPage from './pages/evaluator/EvaluatorListPage'
import EvaluatorCreatePage from './pages/evaluator/EvaluatorCreatePage'
import EvaluatorDetailPage from './pages/evaluator/EvaluatorDetailPage'
import ExperimentListPage from './pages/experiment/ExperimentListPage'
import ExperimentCreatePage from './pages/experiment/ExperimentCreatePage'
import ExperimentDetailPage from './pages/experiment/ExperimentDetailPage'
import ExperimentComparisonPage from './pages/experiment/ExperimentComparisonPage'
import ObservabilityListPage from './pages/observability/ObservabilityListPage'
import TraceDetailPage from './pages/observability/TraceDetailPage'
import TraceAnalysisPage from './pages/trace-analysis/TraceAnalysisPage'
import EvaluatorRecordListPage from './pages/evaluator/EvaluatorRecordListPage'
import EvaluatorRecordDetailPage from './pages/evaluator/EvaluatorRecordDetailPage'
import ModelConfigPage from './pages/model-config/ModelConfigPage'
import ModelSetPage from './pages/model-set/ModelSetPage'

function App() {
  return (
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
  )
}

export default App

