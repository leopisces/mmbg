"""个股分析 API：指标 + 买卖点信号。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core import data_source, indicators, signals

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


@router.get("/{code}")
def analyze(code: str, days: int = Query(500, ge=60, le=2000), force: bool = Query(False)):
    """个股完整分析：K 线 + 全部指标 + 买卖点信号。

    返回结构:
    {
      code, name,
      kline: [{date, open, close, high, low, volume, amount, ma5...}],
      signals: [{date, type, strategy, price, strength}],
      latest_signal: {...},   # 最近一日信号状态
      counts: {buy, sell}     # 历史信号总数
    }
    """
    try:
        kdf = data_source.get_daily_kline(code, days=days, force_refresh=force)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if kdf.empty:
        raise HTTPException(status_code=404, detail=f"未获取到 {code} 的行情数据")

    name = _stock_name(code)
    ind_df = indicators.compute_all(kdf)
    sig_df = signals.generate_signals(ind_df)

    latest = signals.latest_signal_status(sig_df)

    # 序列化：日期转字符串、NaN → None
    kline = _df_to_records(ind_df)
    sig_list = _df_to_records(sig_df)
    counts = {
        "buy": sum(1 for s in sig_list if s["type"] == "buy"),
        "sell": sum(1 for s in sig_list if s["type"] == "sell"),
    }

    return {
        "code": code,
        "name": name,
        "kline": kline,
        "signals": sig_list,
        "latest_signal": latest,
        "counts": counts,
    }


def _stock_name(code: str) -> str:
    try:
        df = data_source.get_stock_list()
        row = df[df["code"] == code]
        if not row.empty:
            return str(row.iloc[0]["name"])
    except Exception:
        pass
    return code


def _df_to_records(df) -> list[dict]:
    """DataFrame → JSON 安全记录（NaN→None，date→ISO 字符串）。"""
    import math

    records = []
    for row in df.to_dict("records"):
        item: dict = {}
        for key, val in row.items():
            if isinstance(val, float) and math.isnan(val):
                item[key] = None
            else:
                item[key] = val
        records.append(item)
    return records