import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, Card, message, Space, Select, Steps, Spin } from 'antd'
import type { FormInstance } from 'antd/es/form'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { datasetService } from '../../services/datasetService'
import { evaluatorService } from '../../services/evaluatorService'
import { experimentService } from '../../services/experimentService'
import { modelSetService } from '../../services/modelSetService'

const { TextArea } = Input
const { Option } = Select

const STEPS = [
  { title: '基础信息' },
  { title: '配置评测集' },
  { title: '配置评测对象' },
  { title: '配置评估器' },
  { title: '确认配置' },
]

export default function ExperimentCreatePage() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [currentStep, setCurrentStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [datasets, setDatasets] = useState<any[]>([])
  const [datasetVersions, setDatasetVersions] = useState<any[]>([])
  const [evaluators, setEvaluators] = useState<any[]>([])
  const [evaluatorVersions, setEvaluatorVersions] = useState<Record<number, any[]>>({})
  const [modelSets, setModelSets] = useState<any[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | undefined>()
  const [selectedEvaluators, setSelectedEvaluators] = useState<number[]>([])
  const [formValues, setFormValues] = useState<any>({})

  useEffect(() => {
    loadDatasets()
    loadEvaluators()
    loadModelSets()
  }, [])

  useEffect(() => {
    if (selectedDatasetId) {
      loadDatasetVersions(selectedDatasetId)
    }
  }, [selectedDatasetId])


  const loadDatasets = async () => {
    try {
      const response = await datasetService.list()
      setDatasets(response.datasets || [])
    } catch (error) {
      message.error('加载数据集失败')
    }
  }

  const loadDatasetVersions = async (datasetId: number) => {
    try {
      const response = await datasetService.listVersions(datasetId)
      setDatasetVersions(response.versions || [])
    } catch (error) {
      message.error('加载数据集版本失败')
    }
  }

  const loadEvaluators = async () => {
    try {
      const response = await evaluatorService.list()
      setEvaluators(response.evaluators || [])
    } catch (error) {
      message.error('加载评估器失败')
    }
  }

  const loadModelSets = async () => {
    try {
      const response = await modelSetService.list()
      setModelSets(response.modelSets || [])
    } catch (error) {
      message.error('加载模型集失败')
      setModelSets([]) // Ensure it's always an array even on error
    }
  }

  const loadEvaluatorVersions = useCallback(async (evaluatorId: number) => {
    try {
      const response = await evaluatorService.listVersions(evaluatorId)
      setEvaluatorVersions((prev) => ({
        ...prev,
        [evaluatorId]: response.versions || [],
      }))
    } catch (error) {
      message.error(`加载评估器版本失败`)
    }
  }, [])
  
  // Load all evaluator versions when entering step 3
  useEffect(() => {
    if (currentStep === 3) {
      evaluators.forEach((evaluator) => {
        if (!evaluatorVersions[evaluator.id]) {
          loadEvaluatorVersions(evaluator.id)
        }
      })
    }
  }, [currentStep, evaluators, evaluatorVersions, loadEvaluatorVersions])

  const handleNext = async () => {
    try {
      // Validate current step
      const fields = getStepFields(currentStep)
      await form.validateFields(fields)
      
      // Save current step values
      const values = form.getFieldsValue()
      
      if (currentStep === 0) {
        // Step 1: Basic info - check name
        const nameCheck = await experimentService.checkName(values.name)
        if (!nameCheck.available) {
          message.error(nameCheck.message || '实验名称已存在')
          return
        }
      } else if (currentStep === 1) {
        // Step 2: Dataset - set selected dataset
        setSelectedDatasetId(values.dataset_id)
      } else if (currentStep === 2) {
        // Step 3: Evaluation target - optional, can skip
        // Only validate if target_type is explicitly set and not empty
        if (values.target_type && values.target_type.trim() !== '') {
          if (values.target_type === 'model_set' && !values.model_set_id) {
            message.error('请选择模型集')
            return
          }
        }
        // If no target_type or empty, user is skipping this step - no validation needed
      } else if (currentStep === 3) {
        // Step 4: Evaluators - validate at least one selected
        if (!values.evaluator_version_ids || values.evaluator_version_ids.length === 0) {
          message.error('请至少选择一个评估器')
          return
        }
        setSelectedEvaluators(values.evaluator_version_ids)
      }
      
      // Save form values before moving to next step
      const currentValues = form.getFieldsValue()
      setFormValues((prev: any) => ({ ...prev, ...currentValues }))
      
      if (currentStep < STEPS.length - 1) {
        setCurrentStep(currentStep + 1)
      }
    } catch (error) {
      // Validation failed
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSkip = () => {
    // Skip current step without validation
    // Clear the target_type if skipping step 2 (evaluation target)
    if (currentStep === 2) {
      form.setFieldsValue({ target_type: undefined })
    }
    
    // Save current form values
    const currentValues = form.getFieldsValue()
    setFormValues((prev: any) => ({ ...prev, ...currentValues }))
    
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handleSubmit = async () => {
    setLoading(true)
    try {
      // Get all form values including saved ones
      const values = { ...formValues, ...form.getFieldsValue() }
      
      // Validate evaluator_version_ids
      if (!values.evaluator_version_ids || values.evaluator_version_ids.length === 0) {
        message.error('请至少选择一个评估器版本')
        setLoading(false)
        return
      }
      
      // Build evaluation target config (optional)
      let evaluationTargetConfig: any = undefined
      if (values.target_type === 'model_set') {
        evaluationTargetConfig = {
          type: 'model_set',
          model_set_id: values.model_set_id,
        }
      }
      // If no target_type, evaluationTargetConfig will be undefined (optional)

      await experimentService.create({
        name: values.name,
        dataset_version_id: values.dataset_version_id,
        evaluation_target_config: evaluationTargetConfig,
        evaluator_version_ids: values.evaluator_version_ids || [],
        description: values.description,
      })
      message.success('创建成功')
      navigate('/experiments')
    } catch (error: any) {
      message.error(error.message || '创建失败')
    } finally {
      setLoading(false)
    }
  }

  const getStepFields = (step: number): string[] => {
    switch (step) {
      case 0:
        return ['name']
      case 1:
        return ['dataset_id', 'dataset_version_id']
      case 2:
        return []  // Optional step, no validation required
      case 3:
        return ['evaluator_version_ids']
      default:
        return []
    }
  }

  const renderStepContent = () => {
    const values = form.getFieldsValue()
    
    switch (currentStep) {
      case 0:
  return (
          <Card title="步骤1：基础信息" className="mb-6">
        <Form.Item
          name="name"
          label="实验名称"
              rules={[
                { required: true, message: '请输入实验名称' },
                { max: 100, message: '名称不能超过100个字符' },
              ]}
        >
              <Input placeholder="如：问答机器人实验测试" />
        </Form.Item>
            <Form.Item
              name="description"
              label="实验描述"
              rules={[{ max: 500, message: '描述不能超过500个字符' }]}
            >
              <TextArea
                placeholder="描述实验目的和内容"
                rows={4}
                showCount
                maxLength={500}
              />
        </Form.Item>
          </Card>
        )

      case 1:
        return (
          <Card title="步骤2：配置评测集" className="mb-6">
        <Form.Item
          name="dataset_id"
          label="数据集"
          rules={[{ required: true, message: '请选择数据集' }]}
        >
          <Select
            placeholder="选择数据集"
                onChange={(value) => {
                  setSelectedDatasetId(value)
                  form.setFieldsValue({ dataset_version_id: undefined })
                }}
                showSearch
                filterOption={(input, option) =>
                  (option?.children as unknown as string)
                    ?.toLowerCase()
                    .includes(input.toLowerCase())
                }
          >
            {datasets.map((ds) => (
                  <Option key={ds.id} value={ds.id}>
                {ds.name}
                  </Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item
          name="dataset_version_id"
          label="数据集版本"
          rules={[{ required: true, message: '请选择数据集版本' }]}
        >
              <Select
                placeholder="选择数据集版本"
                disabled={!selectedDatasetId}
                showSearch
                filterOption={(input, option) =>
                  (option?.children as unknown as string)
                    ?.toLowerCase()
                    .includes(input.toLowerCase())
                }
              >
            {datasetVersions.map((v) => (
                  <Option key={v.id} value={v.id}>
                    {v.version} {v.description ? `- ${v.description}` : ''}
                  </Option>
            ))}
          </Select>
        </Form.Item>
          </Card>
        )
      
      case 2:
        return (
          <Card title="步骤3：配置评测对象（可选）" className="mb-6">
            <div className="text-gray-500 text-sm mb-4">
              提示：评测对象是可选的，可以跳过此步骤。如果跳过，将直接使用数据集中的数据作为评测输入。
            </div>
        <Form.Item
          name="target_type"
              label="评测对象类型"
            >
              <Select 
                placeholder="选择评测对象类型（可选）" 
                allowClear
                onChange={(value) => {
                  // Clear related fields when target_type is cleared
                  if (!value) {
                    form.setFieldsValue({
                      model_set_id: undefined,
                    })
                  }
                }}
              >
                <Option value="model_set">模型集</Option>
          </Select>
        </Form.Item>

            <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.target_type !== currentValues.target_type}>
              {({ getFieldValue }) => {
                const targetType = getFieldValue('target_type')
                return (
                  <>
                    {targetType === 'model_set' && (
                      <Form.Item
                        name="model_set_id"
                        label="模型集"
                        rules={[{ required: true, message: '请选择模型集' }]}
                      >
                        <Select
                          placeholder="选择模型集"
                          showSearch
                          filterOption={(input, option) =>
                            (option?.children as unknown as string)
                              ?.toLowerCase()
                              .includes(input.toLowerCase())
                          }
                        >
                          {modelSets.map((ms) => (
                            <Option key={ms.id} value={ms.id}>
                              {ms.name} ({ms.type === 'agent_api' ? '智能体API' : 'LLM模型'})
                            </Option>
                          ))}
                        </Select>
                      </Form.Item>
                    )}
                  </>
                )
              }}
            </Form.Item>
          </Card>
        )
      
      case 3:
        return (
          <Card title="步骤4：配置评估器" className="mb-6">
            <Form.Item
              name="evaluator_version_ids"
              label="评估器版本"
              rules={[{ required: true, message: '请至少选择一个评估器版本' }]}
            >
              <Select
                mode="multiple"
                placeholder="选择评估器版本"
                showSearch
                filterOption={(input, option) =>
                  (option?.children as unknown as string)
                    ?.toLowerCase()
                    .includes(input.toLowerCase())
                }
                loading={Object.keys(evaluatorVersions).length < evaluators.length}
              >
                {evaluators.map((evaluator) => {
                  const versions = evaluatorVersions[evaluator.id] || []
                  if (versions.length === 0) {
                    return (
                      <Option key={evaluator.id} value={evaluator.id} disabled>
                        {evaluator.name} (加载中...)
                      </Option>
                    )
                  }
                  return versions.map((version: any) => (
                    <Option
                      key={`${evaluator.id}-${version.id}`}
                      value={version.id}
                    >
                      {evaluator.name} - {version.version}
                    </Option>
                  ))
                })}
              </Select>
            </Form.Item>
            <div className="text-gray-500 text-sm mt-2">
              提示：请选择至少一个评估器版本
            </div>
          </Card>
        )
      
      case 4:
        // Get form values - use saved values or current form values
        const currentFormValues = { ...formValues, ...form.getFieldsValue() }
        const selectedDataset = datasets.find((d) => d.id === currentFormValues?.dataset_id)
        const selectedDatasetVersion = datasetVersions.find(
          (v) => v.id === currentFormValues?.dataset_version_id
        )
        
        return (
          <Card title="步骤5：确认配置" className="mb-6">
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">基础信息</h4>
                <div className="pl-4 space-y-1 text-sm">
                  <div><strong>实验名称：</strong>{currentFormValues.name || '-'}</div>
                  <div><strong>描述：</strong>{currentFormValues.description || '-'}</div>
                </div>
              </div>
              
              <div>
                <h4 className="font-semibold mb-2">评测集</h4>
                <div className="pl-4 space-y-1 text-sm">
                  <div><strong>数据集：</strong>{selectedDataset?.name || '-'}</div>
                  <div><strong>版本：</strong>{selectedDatasetVersion?.version || '-'}</div>
                </div>
              </div>
              
              <div>
                <h4 className="font-semibold mb-2">评测对象</h4>
                <div className="pl-4 space-y-1 text-sm">
                  {currentFormValues.target_type === 'model_set' ? (
                    <>
                      <div><strong>类型：</strong>模型集</div>
                      <div><strong>模型集：</strong>
                        {(() => {
                          const selectedModelSet = modelSets.find((ms) => ms.id === currentFormValues.model_set_id)
                          return selectedModelSet ? `${selectedModelSet.name} (${selectedModelSet.type === 'agent_api' ? '智能体API' : 'LLM模型'})` : '-'
                        })()}
                      </div>
                    </>
                  ) : (
                    <div className="text-gray-500">未配置（将直接使用数据集数据）</div>
                  )}
                </div>
              </div>
              
              <div>
                <h4 className="font-semibold mb-2">评估器</h4>
                <div className="pl-4 space-y-1 text-sm">
                  {currentFormValues.evaluator_version_ids?.length > 0 ? (
                    currentFormValues.evaluator_version_ids.map((evId: number) => {
                    // Find evaluator and version
                    let evaluatorName = '未知'
                    let versionName = '未知'
                    for (const evaluator of evaluators) {
                      const versions = evaluatorVersions[evaluator.id] || []
                      const version = versions.find((v: any) => v.id === evId)
                      if (version) {
                        evaluatorName = evaluator.name
                        versionName = version.version
                        break
                      }
                    }
                    return (
                      <div key={evId}>
                        {evaluatorName} - {versionName}
                      </div>
                    )
                  })
                  ) : (
                    <div className="text-gray-500">未选择评估器</div>
                  )}
                </div>
              </div>
            </div>
          </Card>
        )
      
      default:
        return null
    }
  }

  return (
    <div className="h-full flex flex-col p-6">
      <div className="mb-6">
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/experiments')}
          className="mb-4"
        >
          返回
        </Button>
        <h1 className="text-2xl font-semibold mb-0">新建实验</h1>
      </div>

      <Steps current={currentStep} items={STEPS} className="mb-6" />

      <Form
        form={form}
        layout="vertical"
        className="flex-1 overflow-auto"
        initialValues={{}}
      >
        {renderStepContent()}

        <div className="flex justify-between mt-6">
          <Space>
            {currentStep > 0 && (
              <Button onClick={handlePrevious}>上一步</Button>
            )}
          </Space>
          <Space>
            <Button onClick={() => navigate('/experiments')}>取消</Button>
            {currentStep === 2 && (
              <Button onClick={handleSkip}>
                跳过
              </Button>
            )}
            {currentStep < STEPS.length - 1 ? (
              <Button type="primary" onClick={handleNext}>
                下一步
              </Button>
            ) : (
              <Button type="primary" onClick={handleSubmit} loading={loading}>
                创建实验
              </Button>
            )}
          </Space>
        </div>
      </Form>
    </div>
  )
}
