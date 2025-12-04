import { Form, Input, Select, Button, Space, Divider, Tooltip, Modal, Collapse, Tag, Spin } from 'antd'
import { PlayCircleOutlined, ExpandOutlined, QuestionCircleOutlined, FullscreenExitOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import type { LanguageType } from '../../../types/evaluator'
import { evaluatorService } from '../../../services/evaluatorService'
import { message } from 'antd'

const { TextArea } = Input

interface CodeEvaluatorFormProps {
  form: any
  onSubmit?: (values: any) => void
  loading?: boolean
  initialValues?: {
    code_content?: string
    language_type?: LanguageType
  }
}

const defaultTestData = {
  evaluate_dataset_fields: {
    input: {
      content_type: "Text",
      text: "台湾省面积是多少?"
    },
    reference_output: {
      content_type: "Text",
      text: "台湾省由中国第一大岛台湾岛与兰屿、绿岛、钓鱼岛等附属岛屿和澎湖列岛等80多个岛屿组成,总面积约3.6万平方千米。其中台湾岛面积约3.58万平方千米。"
    }
  },
  evaluate_target_output_fields: {
    actual_output: {
      content_type: "Text",
      text: "台湾省由中国第一大岛台湾岛与兰屿、绿岛、钓鱼岛等附属岛屿和澎湖列岛等80多个岛屿组成,总面积约3.6万平方千米。其中台湾岛面积约3.58万平方千米。"
    }
  },
  ext: {}
}

const defaultPythonCode = `def exec_evaluation(turn):
    """
    执行自定义评估逻辑的主函数
    
    步骤说明：
    1. 从输入数据中提取actual_output和reference_output文本
    2. 对两个文本进行预处理（去除首尾空白字符）
    3. 执行文本相等性比较
    4. 根据比较结果生成score和reason
    5. 返回结构化的评估结果
    """
    try:
        # 步骤1: 从嵌套的数据结构中提取actual_output文本
        # 路径: turn["evaluate_target_output_fields"]["actual_output"]["text"]
        actual_text = turn["evaluate_target_output_fields"]["actual_output"]["text"]
        
        # 步骤2: 从嵌套的数据结构中提取reference_output文本
        # 路径: turn["evaluate_dataset_fields"]["reference_output"]["text"]
        reference_text = turn["evaluate_dataset_fields"]["reference_output"]["text"]
        
        # 步骤3: 对两个文本进行预处理，去除首尾空白字符后进行相等性比较
        # 使用 strip() 方法消除可能的空格、换行符等影响比较结果的字符
        is_equal = actual_text.strip() == reference_text.strip()
        
        # 步骤4: 根据比较结果计算score
        # 完全匹配得1.0分，不匹配得0.0分（二元评分机制）
        score = 1.0 if is_equal else 0.0
        
        # 步骤5: 生成详细的reason
        # 包含匹配状态、actual_output内容和reference_output内容
        reason = f"actual_output与reference_output{'匹配' if is_equal else '不匹配'}。actual_output: '{actual_text}', reference_output: '{reference_text}'"
        
        # 步骤6: 返回成功的评估结果对象
        return EvalOutput(score=score, reason=reason)
        
    except KeyError as e:
        # 异常处理1: 处理字段路径不存在的情况
        # 当访问的嵌套字段不存在时，返回0分并记录错误信息
        raise Exception(f"字段路径未找到: {e}")
    except Exception as e:
        # 异常处理2: 处理其他未预期的异常情况
        # 确保函数在任何情况下都能返回有效的评估结果
        raise Exception(f"评估失败: {e}")`

export default function CodeEvaluatorForm({ form, onSubmit, loading }: CodeEvaluatorFormProps) {
  const navigate = useNavigate()
  const [isRunning, setIsRunning] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [testData, setTestData] = useState<string>(JSON.stringify(defaultTestData, null, 2))
  const [codeContent, setCodeContent] = useState<string>(defaultPythonCode)
  const [fullscreenCodeContent, setFullscreenCodeContent] = useState<string>(defaultPythonCode)
  const [fullscreenTestData, setFullscreenTestData] = useState<string>(JSON.stringify(defaultTestData, null, 2))
  const [runResults, setRunResults] = useState<any[]>([])
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const codeEditorRef = useRef<HTMLDivElement>(null)
  const testDataEditorRef = useRef<HTMLDivElement>(null)
  const [editorHeight, setEditorHeight] = useState<number>(456) // 500 - 44 (header height)
  const [fullscreenEditorHeight, setFullscreenEditorHeight] = useState<number>(0)

  // 初始化表单默认值
  useEffect(() => {
    const currentValue = form.getFieldValue(['current_version', 'evaluator_content', 'code_evaluator', 'code_content'])
    if (!currentValue) {
      form.setFieldsValue({
        current_version: {
          evaluator_content: {
            code_evaluator: {
              code_content: defaultPythonCode
            }
          }
        }
      })
      setCodeContent(defaultPythonCode)
    } else {
      setCodeContent(currentValue)
    }
  }, [form])

  // 同步codeContent到表单
  useEffect(() => {
    form.setFieldsValue({
      current_version: {
        evaluator_content: {
          code_evaluator: {
            code_content: codeContent
          }
        }
      }
    })
  }, [codeContent, form])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (onSubmit) {
        onSubmit(values)
      } else {
        form.submit()
      }
    } catch (error) {
      // Validation failed
    }
  }

  const handleRun = async () => {
    try {
      const values = form.getFieldsValue()
      const code = values.current_version?.evaluator_content?.code_evaluator?.code_content || codeContent
      const language = values.current_version?.evaluator_content?.code_evaluator?.language_type || 'Python'

      if (!code?.trim()) {
        message.warning('请先编写函数体')
        return
      }

      let testDataObj
      try {
        testDataObj = JSON.parse(testData)
      } catch (e) {
        message.error('测试数据格式错误，请输入有效的JSON')
        return
      }

      if (!testDataObj) {
        message.warning('请先配置测试数据')
        return
      }

      setIsRunning(true)
      setRunResults([])
      
      try {
        // 调用批量调试API
        const res = await evaluatorService.batchDebug({
          evaluator_type: 'code',
          evaluator_content: {
            code_evaluator: {
              code_content: code,
              language_type: language as any,
            },
          },
          input_data: [testDataObj as any],
        })

        // 处理调试结果
        if (!res.evaluator_output_data || res.evaluator_output_data.length === 0) {
          message.error('试运行失败：未返回结果')
          return
        }

        // 保存结果
        const allResults = res.evaluator_output_data || []
        setRunResults(allResults)

        // 滚动到结果区域
        if (scrollContainerRef.current) {
          setTimeout(() => {
            scrollContainerRef.current?.scrollTo({
              top: scrollContainerRef.current?.scrollHeight,
              behavior: 'smooth',
            })
          }, 100)
        }

        // 显示成功消息
        const successCount = allResults.filter(r => !r.evaluator_run_error).length
        if (successCount > 0) {
          message.success(`试运行完成：${successCount}/${allResults.length} 成功`)
        } else {
          message.warning('试运行完成，但所有测试都失败了')
        }
      } catch (error: any) {
        // Test run failed
        message.error(error.response?.data?.detail || error.message || '试运行失败')
      } finally {
        setIsRunning(false)
      }
    } catch (error: any) {
      message.error(error.message || '试运行失败')
      setIsRunning(false)
    }
  }

  const handleFullscreen = () => {
    if (!isFullscreen) {
      // 打开全屏：同步当前数据到全屏状态
      setFullscreenCodeContent(codeContent)
      setFullscreenTestData(testData)
      // 计算全屏编辑器高度：100vh - Modal头部高度(78px) - padding(40px) - 其他间距
      setFullscreenEditorHeight(window.innerHeight - 200)
    }
    setIsFullscreen(!isFullscreen)
  }

  const handleFullscreenClose = () => {
    // 关闭全屏：同步全屏数据回主表单
    setCodeContent(fullscreenCodeContent)
    setTestData(fullscreenTestData)
    form.setFieldsValue({
      current_version: {
        evaluator_content: {
          code_evaluator: {
            code_content: fullscreenCodeContent
          }
        }
      }
    })
    setIsFullscreen(false)
  }

  const handleFullscreenRun = async () => {
    try {
      const language = form.getFieldValue(['current_version', 'evaluator_content', 'code_evaluator', 'language_type']) || 'Python'
      const code = fullscreenCodeContent

      if (!code?.trim()) {
        message.warning('请先编写函数体')
        return
      }

      let testDataObj
      try {
        testDataObj = JSON.parse(fullscreenTestData)
      } catch (e) {
        message.error('测试数据格式错误，请输入有效的JSON')
        return
      }

      if (!testDataObj) {
        message.warning('请先配置测试数据')
        return
      }

      setIsRunning(true)
      setRunResults([])
      
      try {
        // 调用批量调试API
        const res = await evaluatorService.batchDebug({
          evaluator_type: 'code',
          evaluator_content: {
            code_evaluator: {
              code_content: code,
              language_type: language as any,
            },
          },
          input_data: [testDataObj as any],
        })

        // 处理调试结果
        if (!res.evaluator_output_data || res.evaluator_output_data.length === 0) {
          message.error('试运行失败：未返回结果')
          return
        }

        // 保存结果
        const allResults = res.evaluator_output_data || []
        setRunResults(allResults)

        // 显示成功消息
        const successCount = allResults.filter(r => !r.evaluator_run_error).length
        if (successCount > 0) {
          message.success(`试运行完成：${successCount}/${allResults.length} 成功`)
        } else {
          message.warning('试运行完成，但所有测试都失败了')
        }
      } catch (error: any) {
        // Test run failed
        message.error(error.response?.data?.detail || error.message || '试运行失败')
      } finally {
        setIsRunning(false)
      }
    } catch (error: any) {
      message.error(error.message || '试运行失败')
      setIsRunning(false)
    }
  }

  // 计算编辑器高度
  useEffect(() => {
    // 容器高度500px，减去header 44px = 456px
    setEditorHeight(456)
    
    // 计算全屏编辑器高度
    const calculateFullscreenHeight = () => {
      // 100vh - Modal头部(78px) - padding(40px) - 结果区域预留(300px) = 编辑器高度
      const availableHeight = window.innerHeight - 78 - 40 - 300
      setFullscreenEditorHeight(Math.max(400, availableHeight))
    }
    
    calculateFullscreenHeight()
    window.addEventListener('resize', calculateFullscreenHeight)
    
    return () => {
      window.removeEventListener('resize', calculateFullscreenHeight)
    }
  }, [])


  return (
    <div className="space-y-6">
      {/* 基础信息 */}
      <div>
        <div className="h-[28px] mb-3 text-[16px] leading-7 font-medium text-gray-900">
          基础信息
        </div>
        <Form.Item
          name="name"
          label="名称"
          rules={[{ required: true, message: '请输入名称' }]}
        >
          <Input 
            placeholder="请输入名称" 
            maxLength={50}
            showCount
          />
        </Form.Item>
        <Form.Item 
          name="description" 
          label="描述"
        >
          <TextArea 
            rows={2} 
            placeholder="请输入描述" 
            maxLength={200}
            showCount
          />
        </Form.Item>
      </div>

      <Divider className="mb-6 mt-[14px]" />

      {/* 配置 */}
      <div>
        <div className="h-[28px] mb-3 text-[16px] leading-7 font-medium text-gray-900 flex items-center justify-between">
          <span>配置</span>
          <div className="flex items-center gap-2">
            <Button
              size="small"
              type="text"
              icon={<ExpandOutlined />}
              onClick={handleFullscreen}
            >
              全屏
            </Button>
          </div>
        </div>

        {/* 代码编辑器和测试数据编辑器 - 左右分栏 */}
        <div className="flex gap-4" style={{ height: '500px' }}>
          {/* 左侧：执行函数体 */}
          <div className="flex-1 flex flex-col border border-gray-200 rounded-lg overflow-hidden" ref={codeEditorRef}>
            <div className="flex items-center h-[44px] px-3 border-b border-gray-200 bg-gray-50 flex-shrink-0">
              <span className="text-sm font-medium text-gray-900 mr-4">执行函数体</span>
      <Form.Item
        name={['current_version', 'evaluator_content', 'code_evaluator', 'language_type']}
                className="!mb-0"
                initialValue="Python"
      >
                <Select size="small" style={{ width: 120 }} disabled>
          <Select.Option value="Python">Python</Select.Option>
          <Select.Option value="JS">JavaScript</Select.Option>
        </Select>
      </Form.Item>
            </div>
            <div className="flex-1" style={{ height: `${editorHeight}px` }}>
      <Form.Item
        name={['current_version', 'evaluator_content', 'code_evaluator', 'code_content']}
        rules={[{ required: true, message: '请输入评估代码' }]}
                initialValue={defaultPythonCode}
                className="!mb-0"
                style={{ 
                  margin: 0,
                  padding: 0,
                  height: '100%'
                }}
      >
        <Editor
          height={`${editorHeight}px`}
          language="python"
          value={codeContent}
          onChange={(val) => setCodeContent(val || '')}
          options={{
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            fontSize: 12,
            lineNumbers: 'on',
            folding: true,
            automaticLayout: true,
            readOnly: false,
            theme: 'vs-light'
          }}
        />
      </Form.Item>
            </div>
          </div>

          {/* 右侧：测试数据 */}
          <div className="flex-1 flex flex-col border border-gray-200 rounded-lg overflow-hidden" ref={testDataEditorRef}>
            <div className="flex items-center h-[44px] px-3 border-b border-gray-200 bg-gray-50 flex-shrink-0">
              <span className="text-sm font-medium text-gray-900 mr-2">测试数据: turn</span>
              <Tooltip title="turn代表单轮问答的评测场景">
                <QuestionCircleOutlined className="text-gray-400" />
              </Tooltip>
              <Select 
                size="small" 
                defaultValue="custom" 
                className="ml-auto"
                style={{ width: 100 }}
              >
                <Select.Option value="custom">自定义</Select.Option>
              </Select>
            </div>
            <div className="flex-1" style={{ height: `${editorHeight}px` }}>
              <Editor
                height={`${editorHeight}px`}
                language="json"
                value={testData}
                onChange={(value) => setTestData(value || '')}
                options={{
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  wordWrap: 'on',
                  fontSize: 14,
                  lineNumbers: 'on',
                  folding: true,
                  automaticLayout: true,
                  tabSize: 2,
                  insertSpaces: true,
                  formatOnPaste: true,
                  formatOnType: true,
                  readOnly: false,
                  theme: 'vs-light'
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 试运行结果 */}
      {(runResults.length > 0 || isRunning) && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <div className="flex items-center border-b border-gray-200 h-[36px] px-3 bg-gray-50">
            <h3 className="text-sm font-medium text-gray-900">试运行结果</h3>
            {runResults.length > 0 && (
              <div className="ml-4 flex items-center gap-2 text-xs text-gray-600">
                <span>总计: {runResults.length}</span>
                <span className="text-green-600">
                  成功: {runResults.filter(r => !r.evaluator_run_error).length}
                </span>
                <span className="text-red-600">
                  失败: {runResults.filter(r => r.evaluator_run_error).length}
                </span>
              </div>
            )}
          </div>
          <div className="p-4">
            {isRunning ? (
              <div className="flex items-center justify-center py-8">
                <Spin size="small" />
                <span className="ml-2 text-gray-600">试运行中...</span>
              </div>
            ) : runResults.length > 0 ? (
              <Collapse
                defaultActiveKey={[0]}
                items={runResults.map((result, index) => {
                  const hasError = !!result.evaluator_run_error
                  const score = result.evaluator_result?.score
                  const reasoning = result.evaluator_result?.reasoning || '无原因'
                  const errorMessage = result.evaluator_run_error?.message || ''
                  const stdout = result.stdout || ''
                  
                  return {
                    key: index,
                    label: (
                      <div className="flex items-center gap-4 w-full">
                        <Tag
                          color={hasError ? 'red' : 'green'}
                          icon={hasError ? <CloseCircleOutlined /> : <CheckCircleOutlined />}
                        >
                          {hasError ? '失败' : '成功'}
                        </Tag>
                        {score !== undefined && (
                          <span className="text-sm text-gray-600">得分: {score}</span>
                        )}
                        <span className="text-sm text-gray-600 flex-1">
                          原因: {hasError ? errorMessage : reasoning}
                        </span>
                      </div>
                    ),
                    children: (
                      <div>
                        {(stdout || errorMessage) ? (
                          <div style={{ height: '200px', borderTop: '1px solid #e5e7eb' }}>
                            <Editor
                              height="200px"
                              language="json"
                              value={stdout || errorMessage}
                              options={{
                                readOnly: true,
                                minimap: { enabled: false },
                                scrollBeyondLastLine: false,
                                wordWrap: 'on',
                                fontSize: 12,
                                lineNumbers: 'off',
                                folding: false,
                                automaticLayout: true,
                              }}
                              theme="vs-light"
                            />
                          </div>
                        ) : (
                          <div className="text-center py-4 text-gray-500 text-sm">
                            暂无运行输出
                          </div>
                        )}
                      </div>
                    ),
                  }
                })}
              />
            ) : (
              <div className="text-center py-8 text-gray-500">
                <p>暂无运行结果</p>
                <p className="text-sm mt-1">点击试运行按钮开始测试</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex justify-end gap-2">
        <Button
          icon={<PlayCircleOutlined />}
          onClick={handleRun}
          loading={isRunning}
          disabled={loading || isRunning}
        >
          试运行
        </Button>
        <Button
          type="primary"
          onClick={handleSubmit}
          loading={loading}
          disabled={isRunning}
        >
          创建
        </Button>
      </div>

      {/* 全屏Modal */}
      <Modal
        open={isFullscreen}
        onCancel={handleFullscreenClose}
        width="100vw"
        style={{ top: 0, paddingBottom: 0 }}
        bodyStyle={{
          height: 'calc(100vh - 78px)',
          padding: '20px',
          overflow: 'auto'
        }}
        footer={null}
        closable={true}
        maskClosable={false}
        title={
          <div className="flex items-center justify-between h-[78px] py-4 px-6 pb-1">
            <div className="text-[20px] font-medium text-gray-900">
              评估器配置
            </div>
            <div className="flex items-center gap-2">
              <Button
                icon={<PlayCircleOutlined />}
                onClick={handleFullscreenRun}
                loading={isRunning}
                disabled={loading || isRunning}
              >
                试运行
              </Button>
            </div>
          </div>
        }
      >
        <div className="flex flex-col gap-4" style={{ height: '100%' }}>
          {/* 编辑器区域 */}
          <div className="flex gap-4" style={{ height: `${fullscreenEditorHeight}px`, flexShrink: 0 }}>
            {/* 左侧：执行函数体 */}
            <div className="flex-1 flex flex-col border border-gray-200 rounded-lg overflow-hidden">
              <div className="flex items-center h-[44px] px-3 border-b border-gray-200 bg-gray-50 flex-shrink-0">
                <span className="text-sm font-medium text-gray-900 mr-4">执行函数体</span>
                <Select size="small" style={{ width: 120 }} disabled defaultValue="Python">
                  <Select.Option value="Python">Python</Select.Option>
                  <Select.Option value="JS">JavaScript</Select.Option>
                </Select>
              </div>
              <div className="flex-1" style={{ height: `${fullscreenEditorHeight - 44}px` }}>
                <Editor
                  height={`${fullscreenEditorHeight - 44}px`}
                  language="python"
                  value={fullscreenCodeContent}
                  onChange={(val) => setFullscreenCodeContent(val || '')}
                  options={{
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                    fontSize: 12,
                    lineNumbers: 'on',
                    folding: true,
                    automaticLayout: true,
                    readOnly: false,
                    theme: 'vs-light'
                  }}
                />
              </div>
            </div>

            {/* 右侧：测试数据 */}
            <div className="flex-1 flex flex-col border border-gray-200 rounded-lg overflow-hidden">
              <div className="flex items-center h-[44px] px-3 border-b border-gray-200 bg-gray-50 flex-shrink-0">
                <span className="text-sm font-medium text-gray-900 mr-2">测试数据: turn</span>
                <Tooltip title="turn代表单轮问答的评测场景">
                  <QuestionCircleOutlined className="text-gray-400" />
                </Tooltip>
                <Select 
                  size="small" 
                  defaultValue="custom" 
                  className="ml-auto"
                  style={{ width: 100 }}
                >
                  <Select.Option value="custom">自定义</Select.Option>
                </Select>
              </div>
              <div className="flex-1" style={{ height: `${fullscreenEditorHeight - 44}px` }}>
                <Editor
                  height={`${fullscreenEditorHeight - 44}px`}
                  language="json"
                  value={fullscreenTestData}
                  onChange={(value) => setFullscreenTestData(value || '')}
                  options={{
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                    fontSize: 14,
                    lineNumbers: 'on',
                    folding: true,
                    automaticLayout: true,
                    tabSize: 2,
                    insertSpaces: true,
                    formatOnPaste: true,
                    formatOnType: true,
                    readOnly: false,
                    theme: 'vs-light'
                  }}
                />
              </div>
            </div>
          </div>

          {/* 试运行结果区域 */}
          {(runResults.length > 0 || isRunning) && (
            <div className="border border-gray-200 rounded-lg overflow-hidden flex-shrink-0" style={{ maxHeight: '300px' }}>
              <div className="flex items-center border-b border-gray-200 h-[36px] px-3 bg-gray-50">
                <h3 className="text-sm font-medium text-gray-900">试运行结果</h3>
                {runResults.length > 0 && (
                  <div className="ml-4 flex items-center gap-2 text-xs text-gray-600">
                    <span>总计: {runResults.length}</span>
                    <span className="text-green-600">
                      成功: {runResults.filter(r => !r.evaluator_run_error).length}
                    </span>
                    <span className="text-red-600">
                      失败: {runResults.filter(r => r.evaluator_run_error).length}
                    </span>
                  </div>
                )}
              </div>
              <div className="p-4 overflow-y-auto" style={{ maxHeight: '264px' }}>
                {isRunning ? (
                  <div className="flex items-center justify-center py-8">
                    <Spin size="small" />
                    <span className="ml-2 text-gray-600">试运行中...</span>
                  </div>
                ) : runResults.length > 0 ? (
                  <Collapse
                    defaultActiveKey={[0]}
                    items={runResults.map((result, index) => {
                      const hasError = !!result.evaluator_run_error
                      const score = result.evaluator_result?.score
                      const reasoning = result.evaluator_result?.reasoning || '无原因'
                      const errorMessage = result.evaluator_run_error?.message || ''
                      const stdout = result.stdout || ''
                      
                      return {
                        key: index,
                        label: (
                          <div className="flex items-center gap-4 w-full">
                            <Tag
                              color={hasError ? 'red' : 'green'}
                              icon={hasError ? <CloseCircleOutlined /> : <CheckCircleOutlined />}
                            >
                              {hasError ? '失败' : '成功'}
                            </Tag>
                            {score !== undefined && (
                              <span className="text-sm text-gray-600">得分: {score}</span>
                            )}
                            <span className="text-sm text-gray-600 flex-1">
                              原因: {hasError ? errorMessage : reasoning}
                            </span>
                          </div>
                        ),
                        children: (
                          <div>
                            {(stdout || errorMessage) ? (
                              <div style={{ height: '150px', borderTop: '1px solid #e5e7eb' }}>
                                <Editor
                                  height="150px"
                                  language="json"
                                  value={stdout || errorMessage}
                                  options={{
                                    readOnly: true,
                                    minimap: { enabled: false },
                                    scrollBeyondLastLine: false,
                                    wordWrap: 'on',
                                    fontSize: 12,
                                    lineNumbers: 'off',
                                    folding: false,
                                    automaticLayout: true,
                                  }}
                                  theme="vs-light"
                                />
                              </div>
                            ) : (
                              <div className="text-center py-4 text-gray-500 text-sm">
                                暂无运行输出
                              </div>
                            )}
                          </div>
                        ),
                      }
                    })}
                  />
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <p>暂无运行结果</p>
                    <p className="text-sm mt-1">点击试运行按钮开始测试</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}
