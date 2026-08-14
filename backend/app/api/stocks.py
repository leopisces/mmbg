"""股票相关 API：搜索、日 K 行情。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core import data_source

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/search")
def search(keyword: str = Query(..., min_length=1, max_length=20), limit: int = Query(20, ge=1, le=100)):
    """按代码或名称模糊搜索 A 股。"""
    return data_source.search_stocks(keyword, limit)


@router.get("/list")
def stock_list(force: bool = Query(False)):
    """全部 A 股列表（分页由前端处理，先返回全量供搜索补全）。"""
    df = data_source.get_stock_list(force_refresh=force)
    return df.to_dict("records")


@router.get("/{code}/kline")
def kline(code: str, days: int = Query(500, ge=60, le=2000), force: bool = Query(False)):
    """个股日 K 线。"""
    try:
        df = data_source.get_daily_kline(code, days=days, force_refresh=force)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if df.empty:
        raise HTTPException(status_code=404, detail=f"未获取到 {code} 的行情数据")
    return df.to_dict("records")