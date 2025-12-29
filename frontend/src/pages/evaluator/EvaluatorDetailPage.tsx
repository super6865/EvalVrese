import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Descriptions, Tag, Button, Space, message, Spin, Tabs } from 'antd'
import { ArrowLeftOutlined, ReloadOutlined } from '@ant-design/icons'
import { evaluatorService } from '../../services/evaluatorService'
import type { Evaluator } from '../../types/evaluator'
import EvaluatorDebugPanel from './components/EvaluatorDebugPanel'
import EvaluatorContentPanel from './components/EvaluatorContentPanel'
import './EvaluatorDetailPage.css'

const { TabPane } = Tabs

export default function EvaluatorDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [evaluator, setEvaluator] = useState<Evaluator | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      loadEvaluator()
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
          defaultActiveKey="content"
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
          <TabPane tab="内容" key="content">
            <div style={{ padding: '24px', maxHeight: 'calc(100vh - 400px)', overflowY: 'auto' }}>
              <EvaluatorContentPanel
                evaluator={evaluator}
                onUpdate={loadEvaluator}
              />
            </div>
          </TabPane>
          <TabPane tab="调试" key="debug">
            <div style={{ padding: '24px', maxHeight: 'calc(100vh - 400px)', overflowY: 'auto' }}>
              <EvaluatorDebugPanel
                evaluatorId={evaluator.id}
                evaluatorType={evaluator.evaluator_type}
              />
            </div>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

