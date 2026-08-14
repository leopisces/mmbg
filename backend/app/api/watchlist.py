"""自选股 API。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app import models

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
def list_watchlist():
    """自选股列表。"""
    return models.list_watchlist()


@router.post("/{code}")
def add_watch(code: str, name: str = ""):
    """加入自选。code 必填，name 可自动补齐。"""
    if not name:
        from app.core import data_source

        df = data_source.get_stock_list()
        row = df[df["code"] == code]
        name = str(row.iloc[0]["name"]) if not row.empty else code
    return models.add_watch(code, name)


@router.delete("/{code}")
def remove_watch(code: str):
    """移出自选。"""
    if not models.remove_watch(code):
        raise HTTPException(status_code=404, detail=f"{code} 不在自选中")
    return {"ok": True}