# EvalVerse

![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?logo=TypeScript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=Python&logoColor=white)
![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=React&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=FastAPI&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-5.7+-4479A1?logo=MySQL&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-6.0+-DC382D?logo=Redis&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

> 🚀 一个基于 AutoGen 框架的 AI 智能体和大模型评估平台，支持文本评估和多模态评估（规划中）。该平台提供了完整的评估工作流管理、实验对比分析和可观测性追踪功能。

<div align="center">
  🌐 <a href="README.md"><strong>English</strong></a> | <strong>简体中文</strong>
</div>

---

## 🌟 项目简介

**EvalVerse** 是一个面向 AI 工程师、研究人员和团队的 AI 智能体和大模型评估平台。基于 **FastAPI + React + TypeScript** 的现代化架构，实现高效评估工作流管理、实时实验追踪和分布式可观测性。

🎯 核心能力：

- **数据集管理**：支持多种格式（CSV、JSON、Excel）的数据集导入和版本管理
- **评估器系统**：代码评估器和提示评估器，支持动态执行
- **实验管理**：批量评估，支持并发控制和进度追踪
- **模型配置**：安全的 API 密钥管理和模型参数配置
- **可观测性**：基于 OpenTelemetry 的分布式追踪
- **结果分析**：实验对比和统计聚合

---

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | React 18.2 + TypeScript 5.3 + Vite 5.0 |
| **UI 组件库** | Ant Design 5.12 |
| **后端** | FastAPI 0.109 + Python 3.8+ |
| **数据库** | MySQL 5.7+ (SQLAlchemy 2.0) |
| **任务队列** | Celery 5.3 + Redis 5.0 |
| **LLM 框架** | AutoGen 0.2.12 |
| **可观测性** | OpenTelemetry 1.22 |

---

## 🧠 典型使用场景

| 场景 | 描述 |
|------|------|
| **模型评估** | 使用多种评估器在自定义数据集上评估多个 LLM 模型 |
| **实验对比** | 对比不同模型配置下的实验结果 |
| **自定义评估器开发** | 使用代码评估器创建和测试自定义评估逻辑 |
| **批量处理** | 使用并发控制和进度追踪运行大规模评估 |
| **可观测性分析** | 使用 OpenTelemetry 追踪和分析评估执行路径 |
| **模型性能追踪** | 通过版本化实验追踪模型性能随时间的变化 |

---

## 🚧 规划中

| | 功能点 | 描述 |
|---|---|------|
| <span style="font-size: 2em">☐</span> | **Prompt 模板库** | 创建可复用的 Prompt 模板，支持变量占位符和动态参数 |
| <span style="font-size: 2em">☐</span> | **Prompt 版本控制** | 类似 Git 的版本 diff 对比和回滚机制 |
| <span style="font-size: 2em">☐</span> | **Prompt A/B 测试** | 多版本 Prompt 对比实验，自动化效果分析 |
| <span style="font-size: 2em">☐</span> | **智能数据生成** | 基于 Prompt 模板自动生成测试数据，支持多种场景类型（问答、对话、摘要、翻译等） |
| <span style="font-size: 2em">☐</span> | **数据标注界面** | 人工标注工作台，支持批量标注和多标注者一致性分析 |
| <span style="font-size: 2em">☐</span> | **人机协同标注** | AI 预标注 + 人工复核，支持主动学习机制 |

---

## 📝 更新日志

### v1.0.0 (当前版本)

**初始版本** - 完整的评估平台，包含核心功能：

- ✅ **数据集管理**：支持 CSV、JSON、Excel 格式的数据集导入和版本管理
- ✅ **评估器系统**：代码评估器和提示评估器，支持动态执行
- ✅ **实验管理**：批量评估，支持并发控制和进度追踪
- ✅ **模型配置**：安全的 API 密钥管理和模型参数配置
- ✅ **模型集管理**：支持批量模型评估的模型集配置
- ✅ **可观测性**：基于 OpenTelemetry 的分布式追踪
- ✅ **结果分析**：实验对比和统计聚合
- ✅ **评估器记录**：执行历史和详细的评估日志

---

## 📁 项目结构

```
evalverse/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── api/v1/            # API 路由
│   │   │   ├── dataset.py     # 数据集 API
│   │   │   ├── evaluator.py   # 评估器 API
│   │   │   ├── experiment.py  # 实验 API
│   │   │   ├── model_config.py # 模型配置 API
│   │   │   ├── model_set.py   # 模型集 API
│   │   │   └── observability.py # 可观测性 API
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py      # 应用配置
│   │   │   └── database.py    # 数据库配置
│   │   ├── models/            # 数据库模型
│   │   ├── services/          # 业务逻辑服务
│   │   ├── tasks/             # Celery 任务
│   │   └── utils/             # 工具函数
│   ├── alembic/               # 数据库迁移
│   ├── main.py                # 应用入口
│   └── requirements.txt        # Python 依赖
│
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/        # React 组件
│   │   ├── pages/             # 页面组件
│   │   ├── services/          # API 服务
│   │   ├── hooks/             # React Hooks
│   │   └── utils/             # 工具函数
│   ├── package.json
│   └── vite.config.ts
│
└── README.md                   # 项目文档
```

---

## 🚀 快速开始

### 前置要求

- Python 3.8+
- Node.js 18+
- MySQL 5.7+ 或 8.0+
- Redis 6.0+

### 1. 克隆项目

```bash
git clone https://github.com/super6865/EvalVrese.git
cd EvalVrese
```

### 2. 后端设置

#### 安装依赖

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 配置环境变量

在 `backend` 目录下创建 `.env` 文件：

```bash
# 数据库配置
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/evaluation_platform

# Redis 配置
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# LLM 配置
OPENAI_API_KEY=your-openai-api-key
DEFAULT_LLM_MODEL=gpt-4

# 安全配置
SECRET_KEY=your-secret-key-change-in-production

# CORS 配置
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# OpenTelemetry 配置
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

#### 初始化数据库

1. **创建 MySQL 数据库**:

```sql
CREATE DATABASE evaluation_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. **初始化数据库结构**（选择一种方式）：

**方式一：使用 Alembic 迁移（推荐）**

```bash
cd backend
alembic upgrade head
```

这将根据 Alembic 迁移文件创建所有必要的表。

**方式二：使用 SQL 结构文件**

```bash
cd backend
mysql -u your_username -p evaluation_platform < schema.sql
```

> **注意**：项目提供了 `schema.sql` 文件作为 Alembic 迁移的备选方案。该文件包含完整的数据库结构，可以直接导入到 MySQL 中。

#### 启动后端服务

```bash
uvicorn main:app --reload --port 8000
```

后端 API 文档：
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

#### 启动 Celery Worker（可选）

```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

### 3. 前端设置

#### 安装依赖

```bash
cd frontend
npm install
```

#### 配置 API 地址

编辑 `frontend/src/services/api.ts`，确保 API 基础 URL 指向后端服务。

#### 启动开发服务器

```bash
npm run dev
```

前端应用：http://localhost:5173

---

## 📚 API 文档

启动后端服务后，可以通过以下地址访问 API 文档：

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

---

## 📖 使用指南

详细的使用说明和分步教程，请参考：

- **English**: [User Guide](docs/USAGE.md)
- **中文**: [使用指南](docs/USAGE_zh.md)

使用指南包含：
- 数据集管理和数据导入
- 创建和管理评估器
- 运行实验和查看结果
- 模型配置和模型集
- 可观测性和链路分析
- 最佳实践和故障排除

---

## 💻 开发指南

### 后端开发

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
pytest  # 运行测试
```

### 前端开发

```bash
cd frontend
npm run dev
npm run build  # 构建生产版本
npm run lint   # 代码检查
```

### 代码规范

- **Python**: 遵循 PEP 8 规范
- **TypeScript/React**: 使用 ESLint 配置

---

## 🔧 故障排除

### 常见问题

#### 数据库连接失败
**问题**: 无法连接到 MySQL 数据库  
**解决方案**:
- 检查 MySQL 服务是否运行
- 验证 `.env` 文件中的数据库连接参数
- 检查防火墙设置
- 验证数据库用户权限

#### Redis 连接失败
**问题**: 无法连接到 Redis  
**解决方案**:
- 确保 Redis 服务正在运行：`redis-server`
- 验证 `.env` 中的 `REDIS_URL`
- 检查 Redis 端口（默认：6379）

#### Celery Worker 无法启动
**问题**: Celery worker 启动失败  
**解决方案**:
- 验证 Redis 连接
- 检查 Celery broker 和 backend URL
- 确保所有依赖已安装

#### 前端 API 错误
**问题**: 前端无法连接到后端  
**解决方案**:
- 验证后端是否在 8000 端口运行
- 检查后端的 CORS 配置
- 验证 `frontend/src/services/api.ts` 中的 API 基础 URL

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 贡献流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 报告问题

如果发现 bug 或有功能建议，请在 [GitHub Issues](https://github.com/super6865/EvalVrese/issues) 中提交。

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

---

## 🙏 致谢

- [AutoGen](https://github.com/microsoft/autogen) - Microsoft 的 AutoGen 框架
- [Coze Loop](https://github.com/coze-dev/cozeloop) - AI 智能体开发与运维平台
- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的 Web 框架
- [React](https://react.dev/) - UI 库
- [Ant Design](https://ant.design/) - 企业级 UI 组件库

---

## 🌟 支持项目

如果你觉得 EvalVerse 有帮助，请给项目一颗 ⭐ **Star**！  
感谢支持，将持续维护和优化本项目 💙

> GitHub: [https://github.com/super6865/EvalVrese](https://github.com/super6865/EvalVrese)

---

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- GitHub Issues: [提交问题](https://github.com/super6865/EvalVrese/issues)
- Email: 15979193012@163.com

---

**Happy Evaluating! 🎉**
