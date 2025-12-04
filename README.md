# EvalVerse

AI评估平台，基于Python后端和AutoGen框架实现。支持智能体和大模型的文本评测，未来将支持多模态评测。

## 项目结构

```
evalverse/
├── backend/          # Python后端
├── frontend/         # React前端
└── docs/            # 文档
```

## 快速开始

### 后端

1. 创建虚拟环境：
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库等连接信息
```

4. 运行服务：
```bash
uvicorn main:app --reload --port 8000
```

### 前端

1. 安装依赖：
```bash
cd frontend
npm install
```

2. 运行开发服务器：
```bash
npm run dev
```

访问 http://localhost:5173

## 开发计划

详见 `docs/python.plan.md`

