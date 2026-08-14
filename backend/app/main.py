"""FastAPI 应用入口。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze, stocks, watchlist

app = FastAPI(
    title="A股买卖点分析",
    description="基于经典技术指标的 A 股买卖点分析工具（仅供研究参考，不构成投资建议）",
    version="0.1.0",
)

# 开发环境放开跨域（前端 Vite dev server）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router)
app.include_router(analyze.router)
app.include_router(watchlist.router)


@app.get("/")
def root():
    return {"name": "A股买卖点分析", "version": "0.1.0", "docs": "/docs"}