"""
FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import dataset, evaluator, evaluator_record, experiment, observability, model_config, model_set, prompt

app = FastAPI(
    title="EvalVerse API",
    description="EvalVerse - AI Agent and Model Evaluation Platform with AutoGen",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    redirect_slashes=False,  # 禁用自动重定向尾斜杠，避免 307 重定向导致 SSL 错误
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dataset.router, prefix="/api/v1/datasets", tags=["datasets"])
app.include_router(evaluator.router, prefix="/api/v1/evaluators", tags=["evaluators"])
app.include_router(evaluator_record.router, prefix="/api/v1/evaluator-records", tags=["evaluator-records"])
app.include_router(experiment.router, prefix="/api/v1/experiments", tags=["experiments"])
app.include_router(observability.router, prefix="/api/v1/observability", tags=["observability"])
app.include_router(model_config.router, prefix="/api/v1/model-configs", tags=["model-configs"])
app.include_router(model_set.router, prefix="/api/v1/model-sets", tags=["model-sets"])
app.include_router(prompt.router, prefix="/api/v1/prompts", tags=["prompts"])


@app.get("/")
async def root():
    return {"message": "EvalVerse API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

