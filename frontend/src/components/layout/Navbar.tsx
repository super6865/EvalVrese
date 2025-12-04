import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import type { MenuProps } from 'antd'
import {
  DatabaseOutlined,
  CheckCircleOutlined,
  ExperimentOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SettingOutlined,
  FolderOutlined,
  AppstoreOutlined,
  MonitorOutlined,
  ControlOutlined,
  RadarChartOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import classNames from 'classnames'

import logo from '../../assets/images/logo.svg'
import logoMini from '../../assets/images/logo-mini.svg'

const { Sider } = Layout

interface MenuItem {
  key: string
  label: string
  icon?: React.ReactNode
  children?: MenuItem[]
}

const menuItems: MenuItem[] = [
  {
    key: 'data-management',
    label: '数据管理',
    icon: <FolderOutlined />,
    children: [
      {
        key: 'datasets',
        label: '样本集',
        icon: <DatabaseOutlined />,
      },
      {
        key: 'model-sets',
        label: '模型集',
        icon: <AppstoreOutlined />,
      },
    ],
  },
  {
    key: 'evaluation-task',
    label: '评测任务',
    icon: <AppstoreOutlined />,
    children: [
      {
        key: 'evaluators',
        label: '评估器',
        icon: <CheckCircleOutlined />,
      },
      {
        key: 'experiments',
        label: '实验',
        icon: <ExperimentOutlined />,
      },
    ],
  },
  {
    key: 'monitoring',
    label: '监控',
    icon: <MonitorOutlined />,
    children: [
      {
        key: 'observability',
        label: '链路追踪',
        icon: <RadarChartOutlined />,
      },
      {
        key: 'trace-analysis',
        label: '事件日志',
        icon: <FileTextOutlined />,
      },
    ],
  },
  {
    key: 'system-config',
    label: '系统配置',
    icon: <ControlOutlined />,
    children: [
      {
        key: 'model-configs',
        label: '模型配置',
        icon: <SettingOutlined />,
      },
    ],
  },
]

export function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [selectedKeys, setSelectedKeys] = useState<string[]>([])
  const [openKeys, setOpenKeys] = useState<string[]>([])

  useEffect(() => {
    // 根据当前路径设置选中的菜单项和展开的父级菜单
    const path = location.pathname
    const keys: string[] = []
    const open: string[] = []
    
    if (path.startsWith('/datasets')) {
      keys.push('datasets')
      open.push('data-management')
    } else if (path.startsWith('/model-sets')) {
      keys.push('model-sets')
      open.push('data-management')
    } else if (path.startsWith('/evaluators')) {
      keys.push('evaluators')
      open.push('evaluation-task')
    } else if (path.startsWith('/experiments')) {
      keys.push('experiments')
      open.push('evaluation-task')
    } else if (path.startsWith('/observability')) {
      keys.push('observability')
      open.push('monitoring')
    } else if (path.startsWith('/trace-analysis')) {
      keys.push('trace-analysis')
      open.push('monitoring')
    } else if (path.startsWith('/model-configs')) {
      keys.push('model-configs')
      open.push('system-config')
    }
    
    setSelectedKeys(keys)
    setOpenKeys(open)
  }, [location.pathname])

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    // 只处理叶子节点（子菜单项）的点击
    const isLeafNode = menuItems.some(item => 
      item.children?.some(child => child.key === key)
    )
    if (isLeafNode) {
      navigate(`/${key}`)
    }
  }

  const handleOpenChange: MenuProps['onOpenChange'] = (keys) => {
    setOpenKeys(keys)
  }

  return (
    <div className="h-full">
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={240}
        theme="light"
        className={classNames(
          'h-full min-h-full max-h-full min-w-[88px] !px-0 overflow-hidden !bg-white',
        )}
        style={{
          overflow: 'hidden',
          height: '100%',
          position: 'relative',
        }}
      >
        <div className={classNames('mb-[10px] relative', collapsed ? 'px-2' : 'px-6')}>
          <div className={classNames(
            'flex items-center w-full gap-3 py-[8px]',
            collapsed ? 'justify-center' : 'pl-[8px] pr-0'
          )}>
            {collapsed ? (
              <div className="flex items-center justify-center w-full">
                <img src={logoMini} alt="EvalVerse" className="w-[36px] h-[36px]" />
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <img src={logo} alt="EvalVerse" className="h-[36px] w-[36px] flex-shrink-0" />
                  <span className="text-2xl font-semibold coz-fg-primary whitespace-nowrap">EvalVerse</span>
                </div>
                <div
                  className="cursor-pointer flex-shrink-0 coz-fg-secondary h-[16px] w-[16px] hover:coz-fg-primary transition-colors flex items-center justify-center"
                  onClick={() => setCollapsed(!collapsed)}
                >
                  <MenuFoldOutlined className="text-base" />
                </div>
              </>
            )}
          </div>
          {collapsed && (
            <div
              className="absolute top-[17px] right-2 cursor-pointer flex-shrink-0 coz-fg-secondary h-[16px] w-[16px] hover:coz-fg-primary transition-colors flex items-center justify-center z-10"
              onClick={() => setCollapsed(!collapsed)}
            >
              <MenuUnfoldOutlined className="text-base" />
            </div>
          )}
        </div>
        <div className="px-6 flex-1 !pr-[18px] pb-2 overflow-y-auto styled-scrollbar">
          <Menu
            mode="inline"
            selectedKeys={selectedKeys}
            openKeys={openKeys}
            items={menuItems as any}
            onClick={handleMenuClick}
            onOpenChange={handleOpenChange}
            className="border-r-0"
            style={{
              background: 'transparent',
            }}
          />
        </div>
      </Sider>
    </div>
  )
}

