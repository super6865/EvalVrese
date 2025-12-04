import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Descriptions, Tag, Button, Space, Tabs, message, Spin } from 'antd'
import { ArrowLeftOutlined, ReloadOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { evaluatorService } from '../../services/evaluatorService'
import type { Evaluator, EvaluatorVersion, EvaluatorVersionStatus } from '../../types/evaluator'
import EvaluatorDebugPanel from './components/EvaluatorDebugPanel'
import VersionManagement from './components/VersionManagement'
import dayjs from 'dayjs'
import './EvaluatorDetailPage.css'

const { TabPane } = Tabs

export default function EvaluatorDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [evaluator, setEvaluator] = useState<Evaluator | null>(null)
  const [versions, setVersions] = useState<EvaluatorVersion[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('versions')

  useEffect(() => {
    if (id) {
      loadEvaluator()
      loadVersions()
    }
  }, [id])

  const loadEvaluator = async () => {
    if (!id) return
    setLoading(true)
    try {
      const data = await evaluatorService.get(Number(id))
      setEvaluator(data)
    } catch (error) {
      message.error('加载评估器失败')
    } finally {
      setLoading(false)
    }
  }

  const loadVersions = async () => {
    if (!id) return
    try {
      const response = await evaluatorService.listVersions(Number(id))
      setVersions(response.versions || [])
    } catch (error) {
      message.error('加载版本失败')
    }
  }

  if (loading && !evaluator) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  if (!evaluator) {
    return <div>评估器不存在</div>
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Card className="mb-4" style={{ flexShrink: 0 }}>
        <div className="flex items-center justify-between mb-4">
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/evaluators')}>
              返回
            </Button>
            <h2 className="text-xl font-semibold m-0">{evaluator.name}</h2>
            <Tag color={evaluator.evaluator_type === 'prompt' ? 'blue' : 'green'}>
              {evaluator.evaluator_type === 'prompt' ? 'Prompt' : 'Code'}
            </Tag>
            {evaluator.builtin && <Tag color="purple">内置</Tag>}
            {evaluator.box_type && (
              <Tag color={evaluator.box_type === 'white' ? 'cyan' : 'default'}>
                {evaluator.box_type === 'white' ? '白盒' : '黑盒'}
              </Tag>
            )}
          </Space>
          <Button icon={<ReloadOutlined />} onClick={loadEvaluator}>
            刷新
          </Button>
        </div>
        <Descriptions column={3} bordered>
          <Descriptions.Item label="ID">{evaluator.id}</Descriptions.Item>
          <Descriptions.Item label="名称">{evaluator.name}</Descriptions.Item>
          <Descriptions.Item label="类型">
            {evaluator.evaluator_type === 'prompt' ? 'Prompt' : 'Code'}
          </Descriptions.Item>
          {evaluator.builtin && (
            <Descriptions.Item label="内置">
              <Tag color="purple">是</Tag>
            </Descriptions.Item>
          )}
          {evaluator.box_type && (
            <Descriptions.Item label="黑白盒类型">
              <Tag color={evaluator.box_type === 'white' ? 'cyan' : 'default'}>
                {evaluator.box_type === 'white' ? '白盒' : '黑盒'}
              </Tag>
            </Descriptions.Item>
          )}
          <Descriptions.Item label="最新版本">
            {evaluator.latest_version || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            {evaluator.description || '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card 
        style={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column', 
          overflow: 'hidden',
          minHeight: 0
        }}
        bodyStyle={{ 
          display: 'flex', 
          flexDirection: 'column', 
          flex: 1, 
          padding: 0, 
          overflow: 'hidden',
          minHeight: 0,
          height: '100%'
        }}
      >
        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab}
          className="evaluator-detail-tabs"
          style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            flex: 1, 
            overflow: 'hidden',
            minHeight: 0,
            height: '100%'
          }}
          tabBarStyle={{ margin: 0, padding: '0 24px', flexShrink: 0 }}
        >
          <TabPane tab="版本" key="versions">
            <div style={{ padding: '24px', maxHeight: 'calc(100vh - 400px)', overflowY: 'auto' }}>
              <VersionManagement 
                evaluatorId={evaluator.id} 
                evaluatorType={evaluator.evaluator_type}
                onVersionChange={loadVersions} 
              />
            </div>
          </TabPane>
          <TabPane tab="调试" key="debug">
            <div style={{ padding: '24px', maxHeight: 'calc(100vh - 400px)', overflowY: 'auto' }}>
              {versions.length > 0 ? (
                <EvaluatorDebugPanel
                  evaluatorId={evaluator.id}
                  versionId={versions[0].id}
                  evaluatorType={evaluator.evaluator_type}
                />
              ) : (
                <div className="text-center text-gray-500 py-8">暂无版本，请先创建版本</div>
              )}
            </div>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

