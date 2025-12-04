import { FieldSchema, FieldData } from '../../../services/datasetService'
import { Tag, Tooltip } from 'antd'

interface FieldDataCellProps {
  fieldSchema: FieldSchema
  fieldData?: FieldData
}

export default function FieldDataCell({ fieldSchema, fieldData }: FieldDataCellProps) {
  if (!fieldData || !fieldData.content) {
    return <span className="text-gray-400">-</span>
  }

  const content = fieldData.content
  const contentType = content.content_type || 'Text'

  // Text content
  if (contentType === 'Text' && content.text) {
    const text = content.text
    const format = content.format || 'PlainText'
    
    // Truncate long text
    const maxLength = 100
    const isTruncated = text.length > maxLength
    const displayText = isTruncated ? text.substring(0, maxLength) + '...' : text
    
    const textContent = (
      <div className="text-sm whitespace-pre-wrap break-words">
        {displayText}
      </div>
    )
    
    if (format === 'Markdown') {
      const markdownContent = (
        <div className="text-sm">
          <pre className="whitespace-pre-wrap break-words">{displayText}</pre>
        </div>
      )
      
      // If truncated, wrap with Tooltip
      if (isTruncated) {
        return (
          <Tooltip 
            title={
              <div className="max-w-2xl max-h-96 overflow-auto">
                <pre className="whitespace-pre-wrap break-words text-xs">{text}</pre>
              </div>
            } 
            placement="topLeft"
            overlayStyle={{ maxWidth: '800px' }}
          >
            {markdownContent}
          </Tooltip>
        )
      }
      return markdownContent
    }
    
    // If truncated, wrap with Tooltip
    if (isTruncated) {
      return (
        <Tooltip 
          title={
            <div className="max-w-2xl max-h-96 overflow-auto">
              <pre className="whitespace-pre-wrap break-words text-xs">{text}</pre>
            </div>
          } 
          placement="topLeft"
          overlayStyle={{ maxWidth: '800px' }}
        >
          {textContent}
        </Tooltip>
      )
    }
    
    return textContent
  }

  // Image content
  if (contentType === 'Image' && content.image) {
    const imageUrl = content.image.url
    const imageName = content.image.name || 'Image'
    
    if (imageUrl) {
      return (
        <div className="flex items-center gap-2">
          <img
            src={imageUrl}
            alt={imageName}
            className="max-w-16 max-h-16 object-contain rounded"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none'
            }}
          />
          <span className="text-sm text-gray-600 truncate max-w-32">{imageName}</span>
        </div>
      )
    }
    return <span className="text-gray-400">-</span>
  }

  // Audio content
  if (contentType === 'Audio' && content.audio) {
    const audioUrl = content.audio.url
    
    if (audioUrl) {
      return (
        <div className="flex items-center gap-2">
          <audio controls src={audioUrl} className="h-8" />
        </div>
      )
    }
    return <span className="text-gray-400">-</span>
  }

  // MultiPart content
  if (contentType === 'MultiPart' && content.multi_part) {
    return (
      <div className="text-sm">
        <Tag color="blue">{content.multi_part.length} 个部分</Tag>
      </div>
    )
  }

  return <span className="text-gray-400">-</span>
}

