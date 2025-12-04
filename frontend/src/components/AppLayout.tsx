import { Layout, Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  DatabaseOutlined,
  CheckCircleOutlined,
  ExperimentOutlined,
  EyeOutlined,
} from '@ant-design/icons'

const { Header, Content, Sider } = Layout

interface AppLayoutProps {
  children: React.ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    {
      key: '/datasets',
      icon: <DatabaseOutlined />,
      label: '数据集',
    },
    {
      key: '/evaluators',
      icon: <CheckCircleOutlined />,
      label: '评估器',
    },
    {
      key: '/experiments',
      icon: <ExperimentOutlined />,
      label: '实验',
    },
    {
      key: '/observability',
      icon: <EyeOutlined />,
      label: '可观测性',
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ color: 'white', fontSize: '20px', fontWeight: 'bold' }}>
        EvalVerse
      </Header>
      <Layout>
        <Sider width={200} theme="light">
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ height: '100%' }}
          />
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content>{children}</Content>
        </Layout>
      </Layout>
    </Layout>
  )
}

