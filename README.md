# EvalVerse

![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?logo=TypeScript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=Python&logoColor=white)
![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=React&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=FastAPI&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-5.7+-4479A1?logo=MySQL&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-6.0+-DC382D?logo=Redis&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

> 🚀 An AI agent and model evaluation platform built on the AutoGen framework, supporting text evaluation and multimodal evaluation (planned). The platform provides complete evaluation workflow management, experiment comparison analysis, and observability tracking.

<div align="center">
  🌐 <strong>English</strong> | <a href="README.zh.md">简体中文</a>
</div>

---

## 🌟 Project Overview

**EvalVerse** is a comprehensive AI agent and model evaluation platform designed for AI engineers, researchers, and teams. Built on a modern architecture with **FastAPI + React + TypeScript**, it enables efficient evaluation workflow management, real-time experiment tracking, and distributed observability.

🎯 Core Capabilities:

- **Dataset Management**: Import and version datasets in multiple formats (CSV, JSON, Excel)
- **Evaluator System**: Code-based and prompt-based evaluators with dynamic execution
- **Experiment Management**: Batch evaluation with concurrency control and progress tracking
- **Model Configuration**: Secure API key management and model parameter configuration
- **Observability**: Distributed tracing with OpenTelemetry integration
- **Result Analysis**: Experiment comparison and statistical aggregation

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18.2 + TypeScript 5.3 + Vite 5.0 |
| **UI Library** | Ant Design 5.12 |
| **Backend** | FastAPI 0.109 + Python 3.8+ |
| **Database** | MySQL 5.7+ (SQLAlchemy 2.0) |
| **Task Queue** | Celery 5.3 + Redis 5.0 |
| **LLM Framework** | AutoGen 0.2.12 |
| **Observability** | OpenTelemetry 1.22 |

---

## 🧠 Typical Use Cases

| Scenario | Description |
|----------|-------------|
| **Model Evaluation** | Evaluate multiple LLM models on custom datasets with various evaluators |
| **Experiment Comparison** | Compare experiment results across different model configurations |
| **Custom Evaluator Development** | Create and test custom evaluation logic using code evaluators |
| **Batch Processing** | Run large-scale evaluations with concurrency control and progress tracking |
| **Observability Analysis** | Trace and analyze evaluation execution paths using OpenTelemetry |
| **Model Performance Tracking** | Track model performance over time with versioned experiments |

---

## 🚧 Planned Features

| | Feature | Description |
|---|---|-------------|
| <span style="font-size: 2em">☐</span> | **Prompt Template Library** | Create reusable prompt templates with variable placeholders |
| <span style="font-size: 2em">☐</span> | **Prompt Version Control** | Git-like version diff comparison and rollback mechanism |
| <span style="font-size: 2em">☐</span> | **Prompt A/B Testing** | Multi-version prompt comparison experiments with automated analysis |
| <span style="font-size: 2em">☐</span> | **Intelligent Data Generation** | Auto-generate test data based on prompt templates, support multiple scenarios (QA, dialogue, summarization, translation) |
| <span style="font-size: 2em">☐</span> | **Data Annotation Interface** | Human annotation workspace with batch annotation tools and multi-annotator consistency analysis |
| <span style="font-size: 2em">☐</span> | **Human-in-the-Loop Annotation** | AI pre-annotation + human review with active learning |

---

## 📝 Changelog

### v1.0.0 (Current)

**Initial Release** - Complete evaluation platform with core features:

- ✅ **Dataset Management**: Import and version datasets in CSV, JSON, Excel formats
- ✅ **Evaluator System**: Code-based and prompt-based evaluators with dynamic execution
- ✅ **Experiment Management**: Batch evaluation with concurrency control and progress tracking
- ✅ **Model Configuration**: Secure API key management and model parameter configuration
- ✅ **Model Set Management**: Batch model evaluation with model set configuration
- ✅ **Observability**: Distributed tracing with OpenTelemetry integration
- ✅ **Result Analysis**: Experiment comparison and statistical aggregation
- ✅ **Evaluator Records**: Execution history and detailed evaluation logs

---

## 📁 Project Structure

```
evalverse/
├── backend/                    # Python Backend
│   ├── app/
│   │   ├── api/v1/            # API Routes
│   │   │   ├── dataset.py     # Dataset API
│   │   │   ├── evaluator.py   # Evaluator API
│   │   │   ├── experiment.py  # Experiment API
│   │   │   ├── model_config.py # Model Config API
│   │   │   ├── model_set.py   # Model Set API
│   │   │   └── observability.py # Observability API
│   │   ├── core/              # Core Configuration
│   │   │   ├── config.py      # App Configuration
│   │   │   └── database.py    # Database Configuration
│   │   ├── models/            # Database Models
│   │   ├── services/          # Business Logic Services
│   │   ├── tasks/             # Celery Tasks
│   │   └── utils/             # Utility Functions
│   ├── alembic/               # Database Migrations
│   ├── main.py                # Application Entry Point
│   └── requirements.txt        # Python Dependencies
│
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/        # React Components
│   │   ├── pages/             # Page Components
│   │   ├── services/          # API Services
│   │   ├── hooks/             # React Hooks
│   │   └── utils/             # Utility Functions
│   ├── package.json
│   └── vite.config.ts
│
└── README.md                   # Project Documentation
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- MySQL 5.7+ or 8.0+
- Redis 6.0+

### 1. Clone the Repository

```bash
git clone https://github.com/super6865/EvalVrese.git
cd EvalVrese
```

### 2. Backend Setup

#### Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Configure Environment Variables

Create a `.env` file in the `backend` directory:

```bash
# Database Configuration
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/evaluation_platform

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# LLM Configuration
OPENAI_API_KEY=your-openai-api-key
DEFAULT_LLM_MODEL=gpt-4

# Security Configuration
SECRET_KEY=your-secret-key-change-in-production

# CORS Configuration
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# OpenTelemetry Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

#### Initialize Database

1. **Create MySQL Database**:

```sql
CREATE DATABASE evaluation_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. **Initialize Database Schema** (Choose one method):

**Method 1: Using Alembic Migrations (Recommended)**

```bash
cd backend
alembic upgrade head
```

This will create all necessary tables based on Alembic migration files.

**Method 2: Using SQL Schema File**

```bash
cd backend
mysql -u your_username -p evaluation_platform < schema.sql
```

> **Note**: The `schema.sql` file is provided as an alternative to Alembic migrations. It contains the complete database structure and can be imported directly into MySQL.

#### Start Backend Server

```bash
uvicorn main:app --reload --port 8000
```

Backend API documentation:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

#### Start Celery Worker (Optional)

```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

### 3. Frontend Setup

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Configure API URL

Edit `frontend/src/services/api.ts` to ensure the API base URL points to the backend service.

#### Start Development Server

```bash
npm run dev
```

Frontend application: http://localhost:5173

---

## 📚 API Documentation

After starting the backend service, access the API documentation:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

---

## 📖 User Guide

For detailed usage instructions and step-by-step tutorials, please refer to:

- **English**: [User Guide](docs/USAGE.md)
- **中文**: [使用指南](docs/USAGE_zh.md)

The user guide covers:
- Dataset management and data import
- Creating and managing evaluators
- Running experiments and viewing results
- Model configuration and model sets
- Observability and trace analysis
- Best practices and troubleshooting

---

## 💻 Development

### Backend Development

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
pytest  # Run tests
```

### Frontend Development

```bash
cd frontend
npm run dev
npm run build  # Build for production
npm run lint   # Lint code
```

### Code Style

- **Python**: Follow PEP 8 style guide
- **TypeScript/React**: Use ESLint configuration

---

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Failed
**Problem**: Cannot connect to MySQL database  
**Solution**:
- Check if MySQL service is running
- Verify database connection parameters in `.env`
- Check firewall settings
- Verify database user permissions

#### Redis Connection Failed
**Problem**: Cannot connect to Redis  
**Solution**:
- Ensure Redis service is running: `redis-server`
- Verify `REDIS_URL` in `.env`
- Check Redis port (default: 6379)

#### Celery Worker Not Starting
**Problem**: Celery worker fails to start  
**Solution**:
- Verify Redis connection
- Check Celery broker and backend URLs
- Ensure all dependencies are installed

#### Frontend API Errors
**Problem**: Frontend cannot connect to backend  
**Solution**:
- Verify backend is running on port 8000
- Check CORS configuration in backend
- Verify API base URL in `frontend/src/services/api.ts`

---

## 🤝 Contributing

We welcome all forms of contributions!

### Contribution Process

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Reporting Issues

If you find bugs or have feature suggestions, please submit them in [GitHub Issues](https://github.com/super6865/EvalVrese/issues).

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

- [AutoGen](https://github.com/microsoft/autogen) - Microsoft's AutoGen framework
- [Coze Loop](https://github.com/coze-dev/cozeloop) - AI Agent development and operations platform
- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- [React](https://react.dev/) - UI library
- [Ant Design](https://ant.design/) - Enterprise-class UI component library

---

## 🌟 Support the Project

If you find EvalVerse helpful, please give it a ⭐ **Star**!  
Your support motivates us to keep improving and maintaining the project 💙

> GitHub: [https://github.com/super6865/EvalVrese](https://github.com/super6865/EvalVrese)

---

## 📞 Contact

For questions or suggestions, please contact us through:

- GitHub Issues: [Submit an Issue](https://github.com/super6865/EvalVrese/issues)
- Email: 15979193012@163.com

---

**Happy Evaluating! 🎉**
