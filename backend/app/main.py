from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.connection import init_db
from app.jobs import shutdown
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    shutdown()


app = FastAPI(
    title="连锁便利店周销量 Holt-Winters 预测工具",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
