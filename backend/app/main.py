from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.db.init_db import create_tables
from app.api import documents, chat, auth, admin, categories, feishu, metrics, logs, attachments
from app.middleware.trace_id import TraceIdMiddleware

# Import logger to trigger setup
from app.services.observability import logger  # noqa: F401

# Feishu scheduler for periodic sync
from app.services.integrations.feishu_client import FeishuClient
from app.services.integrations.feishu_fetcher import FeishuFetcher
from app.services.integrations.scheduler import FeishuScheduler, set_scheduler

_scheduler: FeishuScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()

    # 启动飞书调度器（单例）
    global _scheduler
    _client = FeishuClient()  # 创建飞书客户端
    _fetcher = FeishuFetcher(client=_client)  # 注入客户端
    _scheduler = FeishuScheduler(_fetcher)
    set_scheduler(_scheduler)  # 注册到模块级单例，供 feishu.py 直接访问
    _scheduler.start()

    yield
    _scheduler.shutdown()


app = FastAPI(title="QA Copilot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trace_id middleware
app.add_middleware(TraceIdMiddleware)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(categories.router, tags=["categories"])
app.include_router(feishu.router, tags=["feishu"])
app.include_router(metrics.router, tags=["metrics"])
app.include_router(logs.router, tags=["logs"])
app.include_router(attachments.router, prefix="/api", tags=["attachments"])

# 挂载报表静态文件目录
app.mount("/reports", StaticFiles(directory="data/reports"), name="reports")
