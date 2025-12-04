import axios from 'axios'

// 动态检测 API baseURL
function getApiBaseURL(): string {
  // 优先使用环境变量配置
  if (import.meta.env.VITE_API_BASE_URL) {
    console.log('[API Config] Using VITE_API_BASE_URL:', import.meta.env.VITE_API_BASE_URL)
    return import.meta.env.VITE_API_BASE_URL
  }

  // 检测当前访问环境
  const isHttps = window.location.protocol === 'https:'
  const hostname = window.location.hostname
  const isFrpDomain = hostname.includes('frp-cup.com') || hostname.includes('frp-six.com')

  // 如果是通过 frp HTTPS 访问，使用相对路径（依赖 Vite 代理或 frp 转发）
  // 相对路径会被浏览器解析为当前协议和域名
  const baseURL = '/api/v1'

  console.log('[API Config]', {
    protocol: window.location.protocol,
    hostname,
    isHttps,
    isFrpDomain,
    baseURL,
    fullURL: `${window.location.origin}${baseURL}`,
  })

  return baseURL
}

const api = axios.create({
  baseURL: getApiBaseURL(),
  headers: {
    'Content-Type': 'application/json',
  },
})

// 添加请求拦截器用于调试
api.interceptors.request.use(
  (config) => {
    console.log('[API Request]', {
      method: config.method?.toUpperCase(),
      url: config.url,
      baseURL: config.baseURL,
      fullURL: `${config.baseURL}${config.url}`,
    })
    return config
  },
  (error) => {
    console.error('[API Request Error]', error)
    return Promise.reject(error)
  }
)

// 添加响应拦截器用于调试
api.interceptors.response.use(
  (response) => {
    console.log('[API Response]', {
      status: response.status,
      url: response.config.url,
      data: response.data,
    })
    return response
  },
  (error) => {
    console.error('[API Response Error]', {
      message: error.message,
      url: error.config?.url,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
    })
    return Promise.reject(error)
  }
)

export default api

