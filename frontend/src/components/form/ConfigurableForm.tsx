import { Form, Input, Select, Switch, FormInstance } from 'antd'
import { ReactNode } from 'react'

const { TextArea } = Input

export type FieldType = 'input' | 'password' | 'textarea' | 'select' | 'number' | 'switch'

export interface FormFieldConfig {
  name: string
  label: string
  type: FieldType
  placeholder?: string
  required?: boolean
  rules?: any[]
  options?: { label: string; value: any }[]
  tooltip?: string
  initialValue?: any
  valuePropName?: string
  min?: number
  max?: number
  step?: number
  rows?: number
  disabled?: boolean | ((form: FormInstance) => boolean)
  hidden?: boolean | ((form: FormInstance) => boolean)
  render?: (form: FormInstance) => ReactNode
  shouldUpdate?: (prevValues: any, currentValues: any) => boolean
  group?: string
  groupCondition?: (form: FormInstance) => boolean
}

export interface ConfigurableFormProps {
  form: FormInstance
  fields: FormFieldConfig[]
  layout?: 'vertical' | 'horizontal' | 'inline'
  className?: string
}

export function ConfigurableForm({ form, fields, layout = 'vertical', className }: ConfigurableFormProps) {
  const renderField = (field: FormFieldConfig) => {
    const rules = field.rules || []
    if (field.required && !rules.find((r: any) => r.required)) {
      rules.push({ required: true, message: `请输入${field.label}` })
    }

    const isDisabled = typeof field.disabled === 'function' ? field.disabled(form) : field.disabled
    const isHidden = typeof field.hidden === 'function' ? field.hidden(form) : field.hidden

    if (isHidden) {
      return null
    }

    if (field.render) {
      return (
        <Form.Item
          key={field.name}
          noStyle
          shouldUpdate={field.shouldUpdate}
        >
          {field.render(form)}
        </Form.Item>
      )
    }

    const commonProps = {
      disabled: isDisabled,
      placeholder: field.placeholder,
    }

    let inputElement: ReactNode

    switch (field.type) {
      case 'input':
        inputElement = <Input {...commonProps} />
        break
      case 'password':
        inputElement = <Input.Password {...commonProps} />
        break
      case 'textarea':
        inputElement = <TextArea {...commonProps} rows={field.rows || 4} />
        break
      case 'select':
        inputElement = (
          <Select {...commonProps}>
            {field.options?.map((option) => (
              <Select.Option key={option.value} value={option.value}>
                {option.label}
              </Select.Option>
            ))}
          </Select>
        )
        break
      case 'number':
        inputElement = (
          <Input
            type="number"
            {...commonProps}
            min={field.min}
            max={field.max}
            step={field.step}
          />
        )
        break
      case 'switch':
        inputElement = <Switch {...commonProps} />
        break
      default:
        inputElement = <Input {...commonProps} />
    }

    if (field.groupCondition) {
      return (
        <Form.Item
          key={field.name}
          noStyle
          shouldUpdate={(prevValues, currentValues) => {
            const prevType = prevValues.type
            const currentType = currentValues.type
            return prevType !== currentType
          }}
        >
          {(formInstance) => {
            if (!field.groupCondition!(formInstance)) {
              return null
            }
            return (
              <Form.Item
                name={field.name}
                label={field.label}
                rules={rules}
                tooltip={field.tooltip}
                initialValue={field.initialValue}
                valuePropName={field.valuePropName}
              >
                {inputElement}
              </Form.Item>
            )
          }}
        </Form.Item>
      )
    }

    return (
      <Form.Item
        key={field.name}
        name={field.name}
        label={field.label}
        rules={rules}
        tooltip={field.tooltip}
        initialValue={field.initialValue}
        valuePropName={field.valuePropName}
      >
        {inputElement}
      </Form.Item>
    )
  }

  return (
    <Form form={form} layout={layout} className={className}>
      {fields.map(renderField)}
    </Form>
  )
}

