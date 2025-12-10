import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, Card, message, Space, Select, Steps, Spin, Table, Tag } from 'antd'
import type { FormInstance } from 'antd/es/form'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { datasetService } from '../../services/datasetService'
import { evaluatorService } from '../../services/evaluatorService'
import { experimentService } from '../../services/experimentService'
import { modelSetService } from '../../services/modelSetService'
import { promptService } from '../../services/promptService'

const { TextArea } = Input
const { Option } = Select

// Variable Mapping Editor Component
interface VariableMappingEditorProps {
  variables: string[]
  datasetFields: any[]
  value: Record<string, string>
  onChange: (mapping: Record<string, string>) => void
  userInputValue?: string
  onUserInputChange?: (fieldKey: string) => void
}

function VariableMappingEditor({ 
  variables, 
  datasetFields, 
  value, 
  onChange,
  userInputValue,
  onUserInputChange
}: VariableMappingEditorProps) {
  const handleMappingChange = (variable: string, fieldKey: string) => {
    const newMapping = { ...(value || {}) }
    if (fieldKey) {
      newMapping[variable] = fieldKey
    } else {
      delete newMapping[variable]
    }
    onChange(newMapping)
  }

  // Ensure datasetFields is an array
  const safeDatasetFields = Array.isArray(datasetFields) ? datasetFields : []
  // Ensure value is an object
  const safeValue = value || {}

  return (
    <div className="space-y-3">
      {/* 用户输入字段 - 必填 */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium">用户输入 <span className="text-red-500">*</span></span>
        </div>
        <div className="flex items-center gap-2 p-2 border rounded">
          <div className="flex items-center gap-2" style={{ minWidth: '200px', flexShrink: 0 }}>
            <div 
              style={{ 
                padding: '4px 11px',
                background: '#f5f5f5',
                border: '1px solid #d9d9d9',
                borderRadius: '6px',
                fontSize: '14px',
                lineHeight: '1.5715',
                color: 'rgba(0, 0, 0, 0.88)',
                flex: 1,
                minWidth: '120px'
              }}
            >
              用户输入
            </div>
            <Tag>String</Tag>
          </div>
          <div className="flex-1">
            <Select
              placeholder="评测集 请选择"
              value={userInputValue}
              onChange={(val) => onUserInputChange?.(val)}
              style={{ width: '100%' }}
            >
              {safeDatasetFields.map((field) => {
                if (!field || !field.key) return null
                return (
                  <Option key={field.key} value={field.key}>
                    评测集 {field.name || field.key} ({field.key})
                  </Option>
                )
              })}
            </Select>
          </div>
        </div>
      </div>

      {/* Prompt变量映射 - 可选 */}
      {Array.isArray(variables) && variables.length > 0 && (
        <div>
          <div className="text-sm text-gray-500 mb-2">
            Prompt变量映射（可选）：为每个Prompt变量选择对应的数据集字段。
          </div>
          {variables.map((variable) => {
            const currentMapping = safeValue[variable]

            return (
              <div key={variable} className="flex items-center gap-2 p-2 border rounded mb-2">
                <div className="flex items-center gap-2" style={{ minWidth: '200px', flexShrink: 0 }}>
                  <div 
                    style={{ 
                      padding: '4px 11px',
                      background: '#f5f5f5',
                      border: '1px solid #d9d9d9',
                      borderRadius: '6px',
                      fontSize: '14px',
                      lineHeight: '1.5715',
                      color: 'rgba(0, 0, 0, 0.88)',
                      flex: 1,
                      minWidth: '120px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}
                    title={variable}
                  >
                    {variable}
                  </div>
                  <Tag>String</Tag>
                </div>
                <div className="flex-1">
                  <Select
                    placeholder="评测集 请选择"
                    value={currentMapping}
                    onChange={(val) => handleMappingChange(variable, val)}
                    allowClear
                    style={{ width: '100%' }}
                  >
                    {safeDatasetFields.map((field) => {
                      if (!field || !field.key) return null
                      return (
                        <Option key={field.key} value={field.key}>
                          评测集 {field.name || field.key} ({field.key})
                        </Option>
                      )
                    })}
                  </Select>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

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
  const [prompts, setPrompts] = useState<any[]>([])
  const [promptVersions, setPromptVersions] = useState<any[]>([])
  const [promptVariables, setPromptVariables] = useState<string[]>([])
  const [datasetFields, setDatasetFields] = useState<any[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | undefined>()
  const [selectedEvaluators, setSelectedEvaluators] = useState<number[]>([])
  const [selectedPromptId, setSelectedPromptId] = useState<number | undefined>()
  const [formValues, setFormValues] = useState<any>({})

  useEffect(() => {
    loadDatasets()
    loadEvaluators()
    loadModelSets()
    loadPrompts()
  }, [])

  useEffect(() => {
    if (selectedDatasetId) {
      loadDatasetVersions(selectedDatasetId)
    }
  }, [selectedDatasetId])

  useEffect(() => {
    if (selectedPromptId) {
      loadPromptVersions(selectedPromptId)
    }
  }, [selectedPromptId])

  useEffect(() => {
    const selectedVersion = form.getFieldValue('prompt_version')
    if (selectedPromptId && selectedVersion) {
      loadPromptVariables(selectedPromptId, selectedVersion)
    } else {
      setPromptVariables([])
    }
  }, [selectedPromptId, form.getFieldValue('prompt_version')])

  useEffect(() => {
    const selectedVersionId = form.getFieldValue('dataset_version_id')
    if (selectedVersionId && selectedDatasetId) {
      loadDatasetFields(selectedVersionId)
    } else {
      setDatasetFields([])
    }
  }, [form.getFieldValue('dataset_version_id'), selectedDatasetId])


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

  const loadPrompts = async () => {
    try {
      // Fetch all prompts with pagination (max page_size is 100)
      let allPrompts: any[] = []
      let pageNumber = 1
      const pageSize = 100
      let hasMore = true

      while (hasMore) {
        const response = await promptService.list({ 
          page_number: pageNumber, 
          page_size: pageSize 
        })
        const prompts = response.prompts || []
        allPrompts = [...allPrompts, ...prompts]
        
        // Check if there are more pages
        const total = response.total || 0
        hasMore = allPrompts.length < total
        pageNumber++
      }

      setPrompts(allPrompts)
    } catch (error) {
      message.error('加载Prompt失败')
      setPrompts([])
    }
  }

  const loadPromptVersions = async (promptId: number) => {
    try {
      const versions = await promptService.listVersions(promptId)
      setPromptVersions(versions || [])
    } catch (error) {
      message.error('加载Prompt版本失败')
      setPromptVersions([])
    }
  }

  const loadPromptVariables = async (promptId: number, version: string | null) => {
    try {
      const versionParam = version === 'draft' || !version ? null : version
      const variables = await promptService.getVariables(promptId, versionParam)
      setPromptVariables(variables || [])
    } catch (error) {
      console.error('加载Prompt变量失败', error)
      setPromptVariables([])
    }
  }

  const loadDatasetFields = async (versionId: number) => {
    try {
      if (!selectedDatasetId) return
      
      const dataset = datasets.find(d => d.id === selectedDatasetId)
      if (!dataset) return
      
      const version = datasetVersions.find(v => v.id === versionId)
      if (!version) return

      // Get dataset schema to access field definitions
      const schema = await datasetService.getSchema(dataset.id)
      if (schema?.field_definitions) {
        setDatasetFields(schema.field_definitions || [])
      } else {
        setDatasetFields([])
      }
    } catch (error) {
      console.error('加载数据集字段失败', error)
      setDatasetFields([])
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
          if (values.target_type === 'prompt') {
            if (!values.prompt_id) {
              message.error('请选择Prompt')
              return
            }
            if (!values.prompt_version) {
              message.error('请选择Prompt版本')
              return
            }
            if (!values.user_input_mapping) {
              message.error('请配置用户输入字段映射')
              return
            }
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
      } else if (values.target_type === 'prompt') {
        evaluationTargetConfig = {
          type: 'prompt',
          prompt_id: values.prompt_id,
          prompt_version: values.prompt_version === 'draft' ? null : values.prompt_version,
          user_input_mapping: values.user_input_mapping, // 用户输入字段映射（必填）
          variable_mapping: values.variable_mapping || {}, // Prompt变量映射（可选）
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
                  // Clear related fields when target_type is cleared or changed
                  if (!value) {
                    form.setFieldsValue({
                      model_set_id: undefined,
                      prompt_id: undefined,
                      prompt_version: undefined,
                      variable_mapping: undefined,
                    })
                    setSelectedPromptId(undefined)
                    setPromptVersions([])
                    setPromptVariables([])
                  } else if (value === 'model_set') {
                    form.setFieldsValue({
                      prompt_id: undefined,
                      prompt_version: undefined,
                      variable_mapping: undefined,
                      user_input_mapping: undefined,
                    })
                    setSelectedPromptId(undefined)
                    setPromptVersions([])
                    setPromptVariables([])
                  } else if (value === 'prompt') {
                    form.setFieldsValue({
                      model_set_id: undefined,
                    })
                  }
                }}
              >
                <Option value="model_set">模型集</Option>
                <Option value="prompt">Prompt</Option>
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
                    {targetType === 'prompt' && (
                      <>
                        <Form.Item
                          name="prompt_id"
                          label="Prompt"
                          rules={[{ required: true, message: '请选择Prompt' }]}
                        >
                          <Select
                            placeholder="选择Prompt"
                            showSearch
                            filterOption={(input, option) =>
                              (option?.children as unknown as string)
                                ?.toLowerCase()
                                .includes(input.toLowerCase())
                            }
                            onChange={(value) => {
                              setSelectedPromptId(value)
                              form.setFieldsValue({
                                prompt_version: undefined,
                                variable_mapping: undefined,
                                user_input_mapping: undefined,
                              })
                              setPromptVersions([])
                              setPromptVariables([])
                            }}
                          >
                            {prompts.map((p) => (
                              <Option key={p.id} value={p.id}>
                                {p.prompt_basic?.display_name || p.prompt_key}
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                        <Form.Item
                          name="prompt_version"
                          label="Prompt版本"
                          rules={[{ required: true, message: '请选择Prompt版本' }]}
                        >
                          <Select
                            placeholder="选择Prompt版本"
                            disabled={!selectedPromptId}
                            onChange={(value) => {
                              if (selectedPromptId) {
                                loadPromptVariables(selectedPromptId, value)
                              }
                              form.setFieldsValue({ 
                                variable_mapping: undefined,
                                user_input_mapping: undefined
                              })
                            }}
                          >
                            <Option value="draft">使用Draft（草稿）</Option>
                            {promptVersions.map((v) => (
                              <Option key={v.id} value={v.version}>
                                {v.version} {v.description ? `- ${v.description}` : ''}
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                        <Form.Item
                          name="user_input_mapping"
                          label="字段映射"
                          rules={[{ required: true, message: '请配置用户输入字段映射' }]}
                          tooltip="用户输入字段必须映射到数据集中的字段。Prompt变量映射是可选的。"
                        >
                          <VariableMappingEditor
                            variables={promptVariables}
                            datasetFields={datasetFields}
                            value={form.getFieldValue('variable_mapping') || {}}
                            onChange={(mapping) => {
                              form.setFieldsValue({ variable_mapping: mapping })
                            }}
                            userInputValue={form.getFieldValue('user_input_mapping')}
                            onUserInputChange={(fieldKey) => {
                              form.setFieldsValue({ user_input_mapping: fieldKey })
                            }}
                          />
                        </Form.Item>
                      </>
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
                  ) : currentFormValues.target_type === 'prompt' ? (
                    <>
                      <div><strong>类型：</strong>Prompt</div>
                      <div><strong>Prompt：</strong>
                        {(() => {
                          const selectedPrompt = prompts.find((p) => p.id === currentFormValues.prompt_id)
                          return selectedPrompt ? (selectedPrompt.prompt_basic?.display_name || selectedPrompt.prompt_key) : '-'
                        })()}
                      </div>
                      <div><strong>版本：</strong>
                        {currentFormValues.prompt_version === 'draft' ? 'Draft（草稿）' : currentFormValues.prompt_version || '-'}
                      </div>
                      {currentFormValues.user_input_mapping && (
                        <div>
                          <strong>用户输入映射：</strong>
                          <div className="mt-1 text-xs">
                            {(() => {
                              const field = Array.isArray(datasetFields) ? datasetFields.find(f => f && f.key === currentFormValues.user_input_mapping) : undefined
                              return field && field.name ? `${field.name} (${currentFormValues.user_input_mapping})` : String(currentFormValues.user_input_mapping)
                            })()}
                          </div>
                        </div>
                      )}
                      {currentFormValues.variable_mapping && Object.keys(currentFormValues.variable_mapping).length > 0 && (
                        <div>
                          <strong>变量映射：</strong>
                          <div className="mt-1 space-y-1">
                            {Object.entries(currentFormValues.variable_mapping).map(([varName, fieldKey]) => {
                              const field = Array.isArray(datasetFields) ? datasetFields.find(f => f && f.key === fieldKey) : undefined
                              return (
                                <div key={varName} className="text-xs">
                                  {varName} → {field && field.name ? `${field.name} (${fieldKey})` : String(fieldKey)}
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}
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
