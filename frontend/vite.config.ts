import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // 将 node_modules 中的大型依赖库分离到独立的 chunk
          if (id.includes('node_modules')) {
            // Ant Design 相关库
            if (id.includes('antd')) {
              return 'antd';
            }
            if (id.includes('@ant-design/icons')) {
              return 'antd-icons';
            }
            // Monaco Editor (代码编辑器)
            if (id.includes('monaco-editor') || id.includes('@monaco-editor')) {
              return 'monaco-editor';
            }
            // Excel 处理库
            if (id.includes('xlsx')) {
              return 'xlsx';
            }
            // ZIP 处理库
            if (id.includes('jszip')) {
              return 'jszip';
            }
            // React 核心库
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router')) {
              return 'react-vendor';
            }
            // 其他第三方库
            return 'vendor';
          }
        },
      },
    },
    // 启用压缩
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: false, // 保留 console，方便调试
        drop_debugger: true,
      },
    },
    // 设置 chunk 大小警告限制
    chunkSizeWarningLimit: 1000,
  },
  server: {
    host: '0.0.0.0', // 允许外部访问，frp 转发需要
    port: 5173,
    allowedHosts: ['frp-six.com'], // 允许 frp 域名访问
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false, // 允许自签名证书，解决 SSL 协议错误
        ws: true, // 支持 WebSocket
        configure: (proxy, _options) => {
          proxy.on('error', (err, req, res) => {
            console.error('[Vite Proxy Error]', {
              error: err.message,
              url: req.url,
              method: req.method,
              headers: req.headers,
            });
            if (!res.headersSent) {
              res.writeHead(500, {
                'Content-Type': 'application/json',
              });
              res.end(JSON.stringify({ 
                error: 'Proxy error', 
                message: err.message 
              }));
            }
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('[Vite Proxy] Sending Request:', {
              method: req.method,
              url: req.url,
              target: 'http://localhost:8000',
              host: req.headers.host,
            });
          });
          proxy.on('proxyRes', (proxyRes, req, res) => {
            console.log('[Vite Proxy] Received Response:', {
              status: proxyRes.statusCode,
              url: req.url,
              method: req.method,
            });
            
            // 处理 307/308 重定向，重写 Location 头以确保重定向保持在代理内
            if (proxyRes.statusCode === 307 || proxyRes.statusCode === 308) {
              const location = proxyRes.headers['location'];
              if (location) {
                console.log('[Vite Proxy] Redirect detected, original Location:', location);
                
                // 如果 Location 是完整 URL 且指向 localhost:8000，重写为相对路径
                if (location.startsWith('http://localhost:8000') || location.startsWith('https://localhost:8000')) {
                  const relativePath = location.replace(/^https?:\/\/localhost:8000/, '');
                  proxyRes.headers['location'] = relativePath;
                  console.log('[Vite Proxy] Rewritten Location:', relativePath);
                }
                // 如果 Location 已经是相对路径，确保它以 /api 开头
                else if (location.startsWith('/') && !location.startsWith('/api')) {
                  // 如果路径不包含 /api，可能需要添加
                  // 但通常 FastAPI 的重定向应该已经是正确的相对路径
                  console.log('[Vite Proxy] Location is relative path:', location);
                }
              }
            }
          });
        },
      },
    },
  },
})

