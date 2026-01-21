// Monaco Editor 配置
// 配置 @monaco-editor/react 使用本地安装的 monaco-editor，而不是从 CDN 加载

import { loader } from '@monaco-editor/react'
import * as monaco from 'monaco-editor'

// 配置 loader 使用本地的 monaco-editor
loader.config({ monaco })

// 配置 Worker 路径
// vite-plugin-monaco-editor 会在 /monacoeditorwork 路径下提供 worker 文件
// @ts-ignore
self.MonacoEnvironment = {
  getWorkerUrl: function (_moduleId: string, label: string) {
    if (label === 'json') {
      return '/monacoeditorwork/json.worker.js'
    }
    if (label === 'css' || label === 'scss' || label === 'less') {
      return '/monacoeditorwork/css.worker.js'
    }
    if (label === 'html' || label === 'handlebars' || label === 'razor') {
      return '/monacoeditorwork/html.worker.js'
    }
    if (label === 'typescript' || label === 'javascript') {
      return '/monacoeditorwork/ts.worker.js'
    }
    return '/monacoeditorwork/editor.worker.js'
  }
}

