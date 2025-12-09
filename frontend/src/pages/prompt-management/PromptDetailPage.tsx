import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout, Spin, message } from 'antd'
import { promptService } from '../../services/promptService'
import type { Prompt, PromptVersion } from '../../types/prompt'
import { PromptDetailHeader } from './components/PromptDetailHeader'
import { PromptTemplateEditor } from './components/PromptTemplateEditor'
import { CommonConfigPanel } from './components/CommonConfigPanel'
import { DebugPanel } from './components/DebugPanel'
import { VersionListPanel } from './components/VersionListPanel'
import './PromptDetailPage.css'

const { Content } = Layout

export default function PromptDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [prompt, setPrompt] = useState<Prompt | null>(null)
  const [loading, setLoading] = useState(true)
  const [versionListVisible, setVersionListVisible] = useState(false)
  const [configAreaVisible, setConfigAreaVisible] = useState(true)
  const [debugAreaVisible, setDebugAreaVisible] = useState(true)
  const [currentVersion, setCurrentVersion] = useState<string | null>(null)
  const [versions, setVersions] = useState<PromptVersion[]>([])
  
  // Prompt state
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([
    { role: 'system', content: '' },
  ])
  const [variables, setVariables] = useState<Array<{ name: string; value: any; type?: string }>>([])
  const [modelConfig, setModelConfig] = useState<any>({
    model_config_id: undefined,
    temperature: 0.7,
    max_tokens: 4096,
    top_p: 1,
    frequency_penalty: 0,
    presence_penalty: 0,
  })
  const [tools, setTools] = useState<any[]>([])
  const [stepDebug, setStepDebug] = useState(false)
  
  // Debug state
  const [debugInput, setDebugInput] = useState('')
  const [debugResult, setDebugResult] = useState<any>(null)
  const [isExecuting, setIsExecuting] = useState(false)
  const [executionHistory, setExecutionHistory] = useState<any[]>([])
  
  const saveDraftTimerRef = useRef<NodeJS.Timeout | null>(null)
  // Store last saved content for change detection
  const lastSavedContentRef = useRef<{
    messages: Array<{ role: string; content: string }>
    variables: Array<{ name: string; value: any; type?: string }>
    modelConfig: any
    tools: any[]
  } | null>(null)
  // Flag to prevent auto-save during version loading
  const isLoadingVersionRef = useRef<boolean>(false)

  const promptId = id && !isNaN(Number(id)) ? Number(id) : null

  useEffect(() => {
    if (promptId) {
      loadPrompt()
      loadExecutionHistory()
      loadVersions()
    } else if (id) {
      message.error('无效的 Prompt ID')
      navigate('/prompt-management')
    }
  }, [promptId, id])

  const loadPrompt = async () => {
    if (!promptId) return
    setLoading(true)
    try {
      const data = await promptService.get(promptId)
      setPrompt(data)
      
      // Prepare initial content
      let initialMessages = messages
      let initialVariables = variables
      let initialModelConfig = modelConfig
      let initialTools = tools
      
      // Load draft or commit data
      if (data.prompt_draft?.detail) {
        const detail = data.prompt_draft.detail
        if (detail.messages) {
          initialMessages = detail.messages
          setMessages(detail.messages)
        }
        if (detail.variables) {
          initialVariables = detail.variables
          setVariables(detail.variables)
        }
        if (detail.model_config && Object.keys(detail.model_config).length > 0) {
          initialModelConfig = detail.model_config
          setModelConfig(detail.model_config)
        }
        if (detail.tools) {
          initialTools = detail.tools
          setTools(detail.tools)
        }
      } else if (data.prompt_commit?.detail) {
        const detail = data.prompt_commit.detail
        if (detail.messages) {
          initialMessages = detail.messages
          setMessages(detail.messages)
        }
        if (detail.variables) {
          initialVariables = detail.variables
          setVariables(detail.variables)
        }
        if (detail.model_config && Object.keys(detail.model_config).length > 0) {
          initialModelConfig = detail.model_config
          setModelConfig(detail.model_config)
        }
        if (detail.tools) {
          initialTools = detail.tools
          setTools(detail.tools)
        }
      }
      
      // Store initial content to ref after loading
      lastSavedContentRef.current = {
        messages: JSON.parse(JSON.stringify(initialMessages)),
        variables: JSON.parse(JSON.stringify(initialVariables)),
        modelConfig: JSON.parse(JSON.stringify(initialModelConfig)),
        tools: JSON.parse(JSON.stringify(initialTools)),
      }
      
      // Set current version:
      // 1. If there's a draft with base_version, use base_version (user is editing based on that version)
      // 2. Otherwise, use latest_version (viewing the latest committed version)
      // 3. If neither exists, set to null
      const baseVersion = data.prompt_draft?.draft_info?.base_version
      const latestVersion = data.prompt_basic?.latest_version
      setCurrentVersion(baseVersion || latestVersion || null)
    } catch (error: any) {
      message.error('加载 Prompt 失败: ' + (error.message || '未知错误'))
      navigate('/prompt-management')
    } finally {
      setLoading(false)
    }
  }

  const loadExecutionHistory = async () => {
    if (!promptId) return
    try {
      const history = await promptService.getExecutionHistory(promptId)
      setExecutionHistory(history)
    } catch (error) {
      console.error('Failed to load execution history:', error)
    }
  }

  const loadVersions = async () => {
    if (!promptId) return
    try {
      const versionList = await promptService.listVersions(promptId)
      setVersions(versionList)
    } catch (error) {
      console.error('Failed to load versions:', error)
    }
  }

  const loadVersion = async (version: string) => {
    if (!promptId) return
    setLoading(true)
    
    // Set flag to prevent auto-save during version loading
    isLoadingVersionRef.current = true
    
    // Clear any pending save operations
    if (saveDraftTimerRef.current) {
      clearTimeout(saveDraftTimerRef.current)
      saveDraftTimerRef.current = null
    }
    
    try {
      const versionData = await promptService.getVersion(promptId, version)
      
      // Prepare content from version
      let initialMessages = messages
      let initialVariables = variables
      let initialModelConfig = modelConfig
      let initialTools = tools
      
      if (versionData.content) {
        const detail = versionData.content
        if (detail.messages) {
          initialMessages = detail.messages
        }
        if (detail.variables) {
          initialVariables = detail.variables
        }
        if (detail.model_config && Object.keys(detail.model_config).length > 0) {
          initialModelConfig = detail.model_config
        }
        if (detail.tools) {
          initialTools = detail.tools
        }
      }
      
      // Update all states synchronously
      setMessages(initialMessages)
      setVariables(initialVariables)
      setModelConfig(initialModelConfig)
      setTools(initialTools)
      
      // Store initial content to ref immediately (before state updates complete)
      // This ensures that when useEffect triggers, hasContentChanged will return false
      lastSavedContentRef.current = {
        messages: JSON.parse(JSON.stringify(initialMessages)),
        variables: JSON.parse(JSON.stringify(initialVariables)),
        modelConfig: JSON.parse(JSON.stringify(initialModelConfig)),
        tools: JSON.parse(JSON.stringify(initialTools)),
      }
      
      // Set current version
      setCurrentVersion(version)
      
      // Update prompt state to reflect that we're viewing a committed version (not a draft)
      if (prompt) {
        setPrompt({
          ...prompt,
          prompt_draft: {
            draft_info: {
              is_modified: false,
              base_version: version,
              updated_at: versionData.created_at || new Date().toISOString(),
            },
            detail: {
              messages: initialMessages,
              variables: initialVariables,
              model_config: initialModelConfig,
              tools: initialTools,
            },
          },
          prompt_commit: {
            commit_info: {
              version: version,
              description: versionData.description,
              committed_at: versionData.created_at || new Date().toISOString(),
            },
            detail: {
              messages: initialMessages,
              variables: initialVariables,
              model_config: initialModelConfig,
              tools: initialTools,
            },
          },
        })
      }
      
      message.success(`已切换到版本 ${version}`)
    } catch (error: any) {
      message.error('加载版本失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
      // Reset flag after a short delay to allow state updates to complete
      setTimeout(() => {
        isLoadingVersionRef.current = false
      }, 100)
    }
  }

  // Deep comparison function
  const hasContentChanged = (
    current: {
      messages: Array<{ role: string; content: string }>
      variables: Array<{ name: string; value: any; type?: string }>
      modelConfig: any
      tools: any[]
    },
    lastSaved: {
      messages: Array<{ role: string; content: string }>
      variables: Array<{ name: string; value: any; type?: string }>
      modelConfig: any
      tools: any[]
    } | null
  ): boolean => {
    if (!lastSaved) return true
    
    // Compare messages
    if (JSON.stringify(current.messages) !== JSON.stringify(lastSaved.messages)) {
      return true
    }
    
    // Compare variables
    if (JSON.stringify(current.variables) !== JSON.stringify(lastSaved.variables)) {
      return true
    }
    
    // Compare modelConfig
    if (JSON.stringify(current.modelConfig) !== JSON.stringify(lastSaved.modelConfig)) {
      return true
    }
    
    // Compare tools
    if (JSON.stringify(current.tools) !== JSON.stringify(lastSaved.tools)) {
      return true
    }
    
    return false
  }

  // Auto-save draft
  const saveDraft = async () => {
    if (!promptId) return
    
    // Skip auto-save if we're loading a version
    if (isLoadingVersionRef.current) {
      return
    }
    
    const currentContent = {
      messages,
      variables,
      modelConfig,
      tools,
    }
    
    // Check if content has actually changed
    if (!hasContentChanged(currentContent, lastSavedContentRef.current)) {
      return
    }
    
    if (saveDraftTimerRef.current) {
      clearTimeout(saveDraftTimerRef.current)
    }
    
    saveDraftTimerRef.current = setTimeout(async () => {
      try {
        // Get base_version from current state or currentVersion
        const baseVersion = prompt?.prompt_draft?.draft_info?.base_version || currentVersion
        
        await promptService.saveDraft(promptId, {
          messages,
          variables,
          model_config: modelConfig,
          tools,
        }, baseVersion)
        
        // Update last saved content after successful save
        lastSavedContentRef.current = {
          messages: JSON.parse(JSON.stringify(messages)),
          variables: JSON.parse(JSON.stringify(variables)),
          modelConfig: JSON.parse(JSON.stringify(modelConfig)),
          tools: JSON.parse(JSON.stringify(tools)),
        }
        
        // Update prompt state to reflect draft save
        // Preserve base_version from current state if it exists
        if (prompt) {
          setPrompt({
            ...prompt,
            prompt_draft: {
              draft_info: {
                is_modified: true,
                updated_at: new Date().toISOString(),
                base_version: prompt.prompt_draft?.draft_info?.base_version || currentVersion || prompt.prompt_basic?.latest_version,
              },
              detail: {
                messages,
                variables,
                model_config: modelConfig,
                tools,
              },
            },
          })
        }
      } catch (error) {
        console.error('Failed to save draft:', error)
      }
    }, 1000)
  }

  // Extract variables from messages
  useEffect(() => {
    const variableRegex = /\{\{(\w+)\}\}/g
    const extractedVariables = new Set<string>()
    
    // Extract variables from all messages
    messages.forEach((msg) => {
      const content = msg.content || ''
      const matches = Array.from(content.matchAll(variableRegex))
      matches.forEach((match) => {
        extractedVariables.add(match[1])
      })
    })
    
    // Update variables state
    setVariables((prev) => {
      const existingVariablesMap = new Map(prev.map((v) => [v.name, v]))
      const newVariables: Array<{ name: string; value: any; type?: string }> = []
      
      // Add or keep existing variables that are still in messages
      extractedVariables.forEach((varName) => {
        const existing = existingVariablesMap.get(varName)
        if (existing) {
          // Keep existing variable with its value
          newVariables.push(existing)
        } else {
          // Add new variable with empty value
          newVariables.push({ name: varName, value: '', type: 'string' })
        }
      })
      
      return newVariables
    })
  }, [messages])

  useEffect(() => {
    if (promptId && prompt) {
      saveDraft()
    }
    return () => {
      if (saveDraftTimerRef.current) {
        clearTimeout(saveDraftTimerRef.current)
      }
    }
  }, [messages, variables, modelConfig, tools, promptId, prompt])

  const handleSubmitVersion = async (version: string, description?: string) => {
    if (!promptId) return
    try {
      await promptService.submitVersion(promptId, version, description)
      message.success('版本提交成功')
      await loadPrompt()
      await loadVersions()
    } catch (error: any) {
      message.error('提交版本失败: ' + (error.message || '未知错误'))
    }
  }

  const handleDebug = async () => {
    if (!promptId || !debugInput.trim()) {
      message.warning('请输入测试问题')
      return
    }

    // Validate model_config_id exists and is valid
    const modelConfigId = modelConfig?.model_config_id
    if (!modelConfigId || modelConfigId === undefined || modelConfigId === null || modelConfigId === 0) {
      console.error('Model config validation failed:', {
        modelConfig,
        model_config_id: modelConfigId,
        modelConfig_keys: modelConfig ? Object.keys(modelConfig) : 'modelConfig is null/undefined',
      })
      message.error('请先选择模型配置')
      return
    }

    setIsExecuting(true)
    try {
      // Build model_config object with validated model_config_id
      // Always include model_config_id and other valid fields from modelConfig
      const debugModelConfig: any = {
        model_config_id: modelConfigId, // Use the validated ID
      }
      
      // Copy other valid fields from modelConfig (excluding undefined/null)
      if (modelConfig) {
        Object.keys(modelConfig).forEach(key => {
          const value = modelConfig[key]
          // Skip undefined/null values, but include all other fields
          if (value !== undefined && value !== null && key !== 'model_config_id') {
            debugModelConfig[key] = value
          }
        })
      }
      
      console.log('Debug request data:', {
        prompt_id: promptId,
        model_config: debugModelConfig,
        model_config_id: debugModelConfig.model_config_id,
        modelConfig_original: modelConfig,
        modelConfigId_validated: modelConfigId,
        debugModelConfig_keys: Object.keys(debugModelConfig),
      })
      
      const result = await promptService.debug({
        prompt_id: promptId,
        messages: [
          ...messages,
          { role: 'user', content: debugInput },
        ],
        variables: variables.reduce((acc, v) => {
          acc[v.name] = v.value
          return acc
        }, {} as Record<string, any>),
        model_config: debugModelConfig,
      })
      
      setDebugResult(result)
      
      // Add to execution history
      const newExecution = {
        id: `exec_${Date.now()}`,
        timestamp: new Date().toISOString(),
        input: debugInput,
        output: result.content || result.error,
        success: !result.error,
      }
      setExecutionHistory([newExecution, ...executionHistory])
    } catch (error: any) {
      setDebugResult({
        error: error.message || '执行失败',
      })
    } finally {
      setIsExecuting(false)
    }
  }

  if (loading && !prompt) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!prompt) {
    return <div>Prompt 不存在</div>
  }

  return (
    <div className="prompt-detail-page" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <PromptDetailHeader
        prompt={prompt}
        onBack={() => navigate('/prompt-management')}
        onVersionListToggle={() => setVersionListVisible(!versionListVisible)}
        onSubmitVersion={handleSubmitVersion}
        onDelete={async () => {
          if (!promptId) return
          try {
            await promptService.delete(promptId)
            message.success('删除成功')
            navigate('/prompt-management')
          } catch (error: any) {
            message.error('删除失败: ' + (error.message || '未知错误'))
          }
        }}
        versions={versions}
      />

      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        {/* Left Panel - Prompt Template Editor */}
        <div
          style={{
            background: '#fff',
            borderRight: '1px solid #f0f0f0',
            overflow: 'auto',
            flex: '1 1 0%',
            minWidth: 0,
          }}
        >
          <PromptTemplateEditor
            messages={messages}
            onChange={setMessages}
          />
        </div>

        {/* Middle Panel - Common Config */}
        {configAreaVisible && (
          <div
            style={{
              background: '#fff',
              borderRight: '1px solid #f0f0f0',
              overflow: 'auto',
              flex: '1 1 0%',
              minWidth: 0,
            }}
          >
            <CommonConfigPanel
              modelConfig={modelConfig}
              onModelConfigChange={setModelConfig}
              variables={variables}
              onVariablesChange={setVariables}
              tools={tools}
              onToolsChange={setTools}
              stepDebug={stepDebug}
              onStepDebugChange={setStepDebug}
            />
          </div>
        )}

        {/* Right Panel - Debug */}
        {debugAreaVisible && (
          <div
            style={{
              background: '#fff',
              borderLeft: '1px solid #f0f0f0',
              overflow: 'auto',
              flex: '1 1 0%',
              minWidth: 0,
            }}
          >
            <DebugPanel
              input={debugInput}
              onInputChange={setDebugInput}
              result={debugResult}
              isExecuting={isExecuting}
              onExecute={handleDebug}
              executionHistory={executionHistory}
              modelConfig={modelConfig}
            />
          </div>
        )}
      </div>

      {/* Version List Sidebar */}
      {versionListVisible && (
        <VersionListPanel
          promptId={promptId!}
          visible={versionListVisible}
          onClose={() => setVersionListVisible(false)}
          onVersionSelect={async (version) => {
            await loadVersion(version.version)
          }}
          currentVersion={currentVersion}
          latestVersion={prompt?.prompt_basic?.latest_version || null}
        />
      )}
    </div>
  )
}

