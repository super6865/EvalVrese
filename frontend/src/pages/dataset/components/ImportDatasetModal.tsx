import { useState, useEffect, useRef } from 'react'
import { Modal, Upload, Button, Form, Select, message, Progress, Alert, Space, Tooltip, Dropdown, Typography } from 'antd'
import { UploadOutlined, CheckCircleOutlined, DownloadOutlined, InfoCircleOutlined } from '@ant-design/icons'
import type { UploadFile, UploadProps } from 'antd/es/upload'
import { datasetService, Dataset, FieldSchema } from '../../../services/datasetService'
import { getFileHeaders, getDefaultColumnMap } from '../../../utils/fileUpload'

const { Option } = Select

interface ImportDatasetModalProps {
  visible: boolean
  dataset: Dataset | null
  fieldSchemas: FieldSchema[]
  versionId?: number | null
  onClose: () => void
  onSuccess: () => void
}

interface FieldMapping {
  source: string  // 文件列名（导入数据列）
  target: string  // 数据集字段名（评测集列）
  fieldSchema?: FieldSchema
}

interface ImportJob {
  id: number
  status: string
  total?: number
  processed?: number
  added?: number
  errors?: any[]
}

export default function ImportDatasetModal({
  visible,
  dataset,
  fieldSchemas,
  versionId,
  onClose,
  onSuccess
}: ImportDatasetModalProps) {
  const [form] = Form.useForm()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploadedFile, setUploadedFile] = useState<any>(null)
  const [csvHeaders, setCsvHeaders] = useState<string[]>([])
  const [fieldMappings, setFieldMappings] = useState<FieldMapping[]>([])
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importJob, setImportJob] = useState<ImportJob | null>(null)
  const [progressInterval, setProgressInterval] = useState<NodeJS.Timeout | null>(null)
  const [downloadingTemplateLoading, setDownloadingTemplateLoading] = useState(false)
  const [overwriteValue, setOverwriteValue] = useState(false)
  const dragSubTextRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (visible) {
      form.resetFields()
      setFileList([])
      setUploadedFile(null)
      setCsvHeaders([])
      setFieldMappings([])
      setImportJob(null)
      setOverwriteValue(false)
      setLoading(false)
      setImporting(false)  // 确保 importing 状态也被重置
    } else {
      if (progressInterval) {
        clearInterval(progressInterval)
        setProgressInterval(null)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible])


  // Poll for job progress
  useEffect(() => {
    if (importJob && (importJob.status === 'Pending' || importJob.status === 'Running')) {
      const interval = setInterval(async () => {
        try {
          const job = await datasetService.getImportJob(importJob.id)
          setImportJob(job)
          
          if (job.status === 'Completed' || job.status === 'Failed') {
            clearInterval(interval)
            setProgressInterval(null)
            if (job.status === 'Completed') {
              message.success('导入完成')
              onSuccess()
              setTimeout(() => {
                onClose()
              }, 2000)
            } else {
              message.error('导入失败')
            }
          }
        } catch (error) {
          // Error handling for job status fetch
        }
      }, 2000)
      
      setProgressInterval(interval)
      return () => clearInterval(interval)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [importJob])

  const beforeUpload = (file: File) => {
    // 验证文件大小
    const maxSize = 200 * 1024 * 1024 // 200MB
    if (file.size > maxSize) {
      message.error('文件大小不能超过 200MB')
      return false
    }
    
    // 验证文件格式
    const validExtensions = ['.csv', '.zip', '.xlsx', '.xls']
    const fileName = file.name.toLowerCase()
    const isValidFormat = validExtensions.some(ext => fileName.endsWith(ext))
    
    if (!isValidFormat) {
      message.error('不支持的文件格式，请上传 csv、zip、xlsx 或 xls 文件')
      return false
    }
    
    // 返回 true 以允许 customRequest 执行
    return true
  }

  const handleUpload: UploadProps['customRequest'] = async ({ file, onSuccess, onError }) => {
    if (!dataset) {
      const error = new Error('数据集不存在')
      onError?.(error)
      return
    }

    setLoading(true)
    try {
      const uploadFile = file as File
      // 保存 file 对象（UploadFile 类型），用于 onSuccess 回调
      const uploadFileObj = file
      
      // Step 1: Upload file to backend
      const uploadResult = await datasetService.uploadFile(dataset.id, uploadFile)
      
      if (!uploadResult || !uploadResult.file_path) {
        throw new Error('文件上传失败：服务器未返回文件路径')
      }
      
      setUploadedFile(uploadResult)
      
      // Step 2: Read headers from file (frontend)
      const { headers: fileHeaders, error: headerError } = await getFileHeaders(uploadFile)
      
      if (headerError) {
        message.warning(`读取文件头信息失败: ${headerError}`)
      }
      
      setCsvHeaders(fileHeaders || [])
      
      // Step 3: Generate default column mappings (based on dataset fields)
      const availableFieldSchemas = fieldSchemas.filter(f => f.status !== 'Deleted')
      const defaultMappings = getDefaultColumnMap(availableFieldSchemas, fileHeaders || [])
      
      setFieldMappings(defaultMappings)
      form.setFieldsValue({
        file_path: uploadResult.file_path,
        file_format: uploadResult.file_format,
        field_mappings: defaultMappings,
        overwrite: false
      })
      setOverwriteValue(false)
      
      // 状态更新（React 状态更新是异步的，不需要立即检查）
      setUploadedFile(uploadResult)
      setCsvHeaders(fileHeaders || [])
      setFieldMappings(defaultMappings)
      
      // 调用 onSuccess 回调，告诉 Upload 组件上传成功
      // onSuccess 签名: (response: any, file: UploadFile, xhr?: any) => void
      // 传递响应结果和原始 file 对象，让 Upload 组件正确更新 fileList 状态
      onSuccess?.(uploadResult, uploadFileObj)
      message.success('文件上传成功')
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || 
                          error?.response?.data?.message || 
                          error?.message || 
                          '未知错误'
      
      // 确保错误被正确处理
      const errorObj = error instanceof Error ? error : new Error(errorMessage)
      onError?.(errorObj)
      
      message.error({
        content: `文件上传失败: ${errorMessage}`,
        duration: 5
      })
      
      // 重置状态
      setUploadedFile(null)
      setCsvHeaders([])
      setFieldMappings([])
    } finally {
      setLoading(false)
    }
  }

  const handleFieldMappingChange = (index: number, source: string) => {
    const newMappings = [...fieldMappings]
    newMappings[index] = {
      ...newMappings[index],
      source
    }
    setFieldMappings(newMappings)
    form.setFieldsValue({ field_mappings: newMappings })
  }

  const handleSubmit = async () => {
    if (!dataset || !uploadedFile) {
      message.error({
        content: '请先上传文件',
        duration: 3
      })
      return
    }

    if (fieldSchemas.length === 0) {
      message.error({
        content: '请先定义数据集字段（Schema）后再进行导入',
        duration: 5
      })
      return
    }

    // Validate field mappings - at least one mapping with source is required
    const validMappings = fieldMappings.filter(m => m.source && m.target)
    if (validMappings.length === 0) {
      message.error({
        content: '请至少配置一个字段映射（选择导入数据列）',
        duration: 5
      })
      return
    }

    setImporting(true)
    try {
      const result = await datasetService.importDataset(dataset.id, {
        file_path: uploadedFile.file_path,
        file_format: uploadedFile.file_format,
        field_mappings: validMappings.map(m => ({ source: m.source, target: m.target })),
        overwrite_dataset: form.getFieldValue('overwrite') || false,
        version_id: versionId || undefined
      })

      setImportJob({
        id: result.job_id,
        status: result.status
      })
      
      // 导入任务已创建，重置 importing 状态
      // 后续通过轮询 importJob 状态来跟踪进度
      setImporting(false)
      
      message.success({
        content: '导入任务已创建，正在处理中...',
        duration: 3
      })
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.response?.data?.message || error?.message || '未知错误'
      message.error({
        content: `导入失败: ${errorMessage}`,
        duration: 5
      })
      setImporting(false)
    }
  }

  const getTypeText = (fieldSchema?: FieldSchema): string => {
    if (!fieldSchema) return 'String'
    const contentType = fieldSchema.content_type || 'Text'
    const format = fieldSchema.default_display_format || 'PlainText'
    
    if (contentType === 'Text') {
      return format === 'JSON' ? 'Object' : 'String'
    }
    return contentType
  }

  const progress = importJob && importJob.total && importJob.total > 0
    ? Math.round((importJob.processed || 0) / importJob.total * 100)
    : 0

  // Determine button disabled state and tooltip
  const getImportButtonState = () => {
    if (!uploadedFile) {
      return { disabled: true, tooltip: '请先上传文件' }
    }
    if (fieldSchemas.length === 0) {
      return { disabled: true, tooltip: '请先定义数据集字段（Schema）' }
    }
    if (fieldMappings.length === 0) {
      return { disabled: true, tooltip: '未找到可映射的字段' }
    }
    const hasValidMapping = fieldMappings.some(item => item?.source && item?.target)
    if (!hasValidMapping) {
      return { disabled: true, tooltip: '请至少配置一个字段映射（选择导入数据列）' }
    }
    return { disabled: false, tooltip: '' }
  }

  const importButtonState = getImportButtonState()
  const disableImport = importButtonState.disabled

  return (
    <Modal
      title="导入数据"
      open={visible}
      onCancel={onClose}
      width={800}
      footer={null}
      destroyOnClose
    >
      <Form form={form} layout="vertical">
        {/* File Upload */}
        <Form.Item label="上传数据" required>
          <Upload
            fileList={fileList}
            onChange={({ fileList }) => {
              setFileList(fileList)
              if (fileList.length === 0) {
                setUploadedFile(null)
                setCsvHeaders([])
                setFieldMappings([])
              }
            }}
            customRequest={handleUpload}
            accept=".csv,.zip,.xlsx,.xls"
            maxCount={1}
            beforeUpload={beforeUpload}
            draggable
            showUploadList={{
              showPreviewIcon: false,
              showRemoveIcon: true,
            }}
          >
            <div style={{ 
              padding: '40px 20px',
              border: '2px dashed #d9d9d9',
              borderRadius: '8px',
              textAlign: 'center',
              cursor: 'pointer',
              background: '#fafafa'
            }}>
              <UploadOutlined style={{ fontSize: '48px', color: '#1890ff', marginBottom: '16px' }} />
              <div style={{ fontSize: '16px', color: '#666', marginBottom: '8px' }}>
                点击上传或者拖拽文件至此处
              </div>
              <div 
                ref={dragSubTextRef}
                style={{ 
                  fontSize: '12px', 
                  color: '#999',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '12px'
                }}
              >
                <span>支持文件格式：csv、zip、xlsx、xls，文件最大200MB, 仅支持导入一个文件</span>
                <Dropdown
                  menu={{
                    items: [
                      {
                        key: 'csv',
                        label: 'CSV模板',
                        onClick: async () => {
                          setDownloadingTemplateLoading(true)
                          // TODO: 实现下载模板功能，需要后端API支持
                          message.info('下载模板功能待实现')
                          setDownloadingTemplateLoading(false)
                        }
                      }
                    ]
                  }}
                  trigger={['click']}
                >
                  <Typography.Link 
                    style={{ 
                      fontSize: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <DownloadOutlined />
                    下载模板
                    {downloadingTemplateLoading && <span style={{ marginLeft: '4px' }}>...</span>}
                  </Typography.Link>
                </Dropdown>
              </div>
            </div>
          </Upload>
          {uploadedFile && (
            <div style={{ marginTop: 8, color: '#52c41a' }}>
              <CheckCircleOutlined /> {uploadedFile.filename}
            </div>
          )}
        </Form.Item>

        {/* Column Mapping */}
        {uploadedFile && (
          <Form.Item 
            label={
              <Space>
                <span>列映射</span>
                <InfoCircleOutlined style={{ fontSize: '14px', color: '#1890ff' }} />
              </Space>
            }
            required
            tooltip="如果待导入数据集的列没有配置映射关系，则该列不会被导入"
          >
            {fieldSchemas.length === 0 ? (
              <Alert
                message="请先定义数据集字段（Schema）"
                description="在导入数据之前，请先在数据集设置中定义字段（Schema）。点击右上角的「编辑 Schema」按钮来添加字段。"
                type="warning"
                showIcon
              />
            ) : fieldMappings.length === 0 ? (
              <Alert
                message="未找到可映射的字段"
                description="数据集中没有可用的字段定义，请先添加字段定义后再进行导入。"
                type="info"
                showIcon
              />
            ) : (
              <>
                <Typography.Text type="secondary" style={{ display: 'block', marginBottom: '12px', fontSize: '12px' }}>
                  如果待导入数据集的列没有配置映射关系，则该列不会被导入
                </Typography.Text>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {fieldMappings.map((mapping, index) => (
                    <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {/* 评测集列（只读） */}
                      <div style={{
                        width: '276px',
                        padding: '8px 12px',
                        border: '1px solid #d9d9d9',
                        borderRadius: '6px',
                        background: '#fafafa',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        minHeight: '32px',
                        overflow: 'hidden'
                      }}>
                        <div style={{ flex: 1, overflow: 'hidden' }}>
                          <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                            评测集列
                          </div>
                          <div style={{ fontSize: '14px', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {mapping.target || mapping.fieldSchema?.name || ''}
                          </div>
                        </div>
                        <div style={{ 
                          marginLeft: '8px',
                          padding: '2px 8px',
                          background: '#e6f7ff',
                          borderRadius: '4px',
                          fontSize: '12px',
                          color: '#1890ff',
                          flexShrink: 0
                        }}>
                          {getTypeText(mapping.fieldSchema)}
                        </div>
                      </div>

                      {/* 等号 */}
                      <div style={{
                        width: '32px',
                        height: '32px',
                        border: '1px solid #d9d9d9',
                        borderRadius: '6px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}>
                        <span style={{ fontSize: '16px', color: '#666' }}>=</span>
                      </div>

                      {/* 导入数据列（下拉选择） */}
                      <div style={{ width: '276px', flexShrink: 0 }}>
                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                          导入数据列
                          {mapping.fieldSchema?.is_required && (
                            <span style={{ color: '#ff4d4f', marginLeft: '2px' }}>*</span>
                          )}
                        </div>
                        <Select
                          value={mapping.source}
                          placeholder="选择导入数据列"
                          style={{ width: '100%' }}
                          allowClear
                          onChange={(value) => handleFieldMappingChange(index, value || '')}
                        >
                          {csvHeaders.map(header => (
                            <Option key={header} value={header}>
                              {header}
                            </Option>
                          ))}
                        </Select>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </Form.Item>
        )}

        {/* Import Method */}
        {uploadedFile && (
          <Form.Item 
            name="overwrite" 
            label="导入方式" 
            required
            rules={[{ required: true, message: '请选择导入方式' }]}
          >
            <div style={{ display: 'flex', gap: '8px' }}>
              <div
                onClick={() => {
                  setOverwriteValue(false)
                  form.setFieldsValue({ overwrite: false })
                }}
                style={{
                  flex: 1,
                  border: `1px solid ${overwriteValue === false ? '#1890ff' : '#d9d9d9'}`,
                  borderRadius: '6px',
                  padding: '8px 16px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  backgroundColor: overwriteValue === false ? '#e6f7ff' : 'transparent',
                  color: overwriteValue === false ? '#1890ff' : '#666',
                  transition: 'all 0.2s'
                }}
              >
                追加数据
              </div>
              <div
                onClick={() => {
                  Modal.confirm({
                    title: '确认全量覆盖',
                    content: '导入数据将覆盖现有数据，此操作不可恢复，是否继续？',
                    okText: '确认',
                    cancelText: '取消',
                    okButtonProps: { danger: true },
                    onOk: () => {
                      setOverwriteValue(true)
                      form.setFieldsValue({ overwrite: true })
                    }
                  })
                }}
                style={{
                  flex: 1,
                  border: `1px solid ${overwriteValue === true ? '#1890ff' : '#d9d9d9'}`,
                  borderRadius: '6px',
                  padding: '8px 16px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  backgroundColor: overwriteValue === true ? '#e6f7ff' : 'transparent',
                  color: overwriteValue === true ? '#1890ff' : '#666',
                  transition: 'all 0.2s'
                }}
              >
                全量覆盖
              </div>
            </div>
          </Form.Item>
        )}

        {/* Import Progress */}
        {importJob && (
          <Form.Item label="导入进度">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Progress
                percent={progress}
                status={importJob.status === 'Failed' ? 'exception' : 'active'}
                format={() => {
                  if (importJob.status === 'Completed') {
                    return `完成 (${importJob.added || 0} / ${importJob.total || 0})`
                  } else if (importJob.status === 'Failed') {
                    return '失败'
                  } else {
                    return `${importJob.processed || 0} / ${importJob.total || 0}`
                  }
                }}
              />
              <div style={{ fontSize: 12, color: '#666' }}>
                状态: {importJob.status === 'Pending' ? '等待中' : 
                       importJob.status === 'Running' ? '处理中' :
                       importJob.status === 'Completed' ? '已完成' : '失败'}
              </div>
              {importJob.errors && importJob.errors.length > 0 && (
                <Alert
                  message="导入错误"
                  type="error"
                  description={
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      {importJob.errors.map((error: any, index: number) => (
                        <li key={index}>
                          {error.summary || error.type} ({error.error_count || 0} 条)
                        </li>
                      ))}
                    </ul>
                  }
                />
              )}
            </Space>
          </Form.Item>
        )}

        {/* Actions */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'flex-end', 
          gap: '8px',
          paddingTop: '16px',
          borderTop: '1px solid #f0f0f0',
          marginTop: '16px'
        }}>
          <Button 
            onClick={onClose} 
            disabled={importing && importJob?.status !== 'Completed'}
          >
            {importJob?.status === 'Completed' ? '关闭' : '取消'}
          </Button>
          <Tooltip title={importButtonState.tooltip}>
            <Button
              type="primary"
              onClick={handleSubmit}
              loading={importing}
              disabled={disableImport || !!importJob || loading}
            >
              {importJob ? '导入中...' : '导入'}
            </Button>
          </Tooltip>
        </div>
      </Form>
    </Modal>
  )
}
