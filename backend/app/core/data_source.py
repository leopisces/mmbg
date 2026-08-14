"""数据源层：基于 akshare 获取 A 股数据，带本地缓存与重试。"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

# 禁用系统代理（akshare 直连东财 API，走代理反而易断）
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""

# 彻底禁用 requests 从 Windows 注册表读取的系统代理
import urllib.request
urllib.request.getproxies = lambda: {}

import akshare as ak
import pandas as pd

from app.config import CACHE_DIR, KLINE_CACHE_TTL, STOCK_LIST_CACHE_TTL

# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _retry(fn, tries: int = 5, delay: float = 2.0):
    """akshare 接口偶发失败，做指数退避重试。"""
    last_err: Exception | None = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - 网络/接口异常都要重试
            last_err = e
            if i < tries - 1:
                time.sleep(delay * (i + 1))
    raise RuntimeError(f"akshare 请求失败: {last_err}")


def _cache_path(name: str) -> Path:
    return CACHE_DIR / name


def _is_cache_fresh(path: Path, ttl: int) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.now() - mtime < timedelta(seconds=ttl)


def _read_csv_cache(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path, dtype={"code": str})
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 股票列表
# ---------------------------------------------------------------------------

def get_stock_list(force_refresh: bool = False) -> pd.DataFrame:
    """全部 A 股代码 + 名称。列: code, name"""
    path = _cache_path("stock_list.csv")
    if not force_refresh and _is_cache_fresh(path, STOCK_LIST_CACHE_TTL):
        df = _read_csv_cache(path)
        if df is not None and not df.empty:
            return df

    df = _retry(lambda: ak.stock_info_a_code_name())
    df = df.rename(columns={"code": "code", "name": "name"})
    df["code"] = df["code"].astype(str).str.zfill(6)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return df


def get_etf_list(force_refresh: bool = False) -> pd.DataFrame:
    """全部 ETF 代码 + 名称。列: code, name"""
    path = _cache_path("etf_list.csv")
    if not force_refresh and _is_cache_fresh(path, STOCK_LIST_CACHE_TTL):
        df = _read_csv_cache(path)
        if df is not None and not df.empty:
            return df

    raw = _retry(lambda: ak.fund_etf_spot_em())
    df = raw[["代码", "名称"]].rename(columns={"代码": "code", "名称": "name"})
    df["code"] = df["code"].astype(str).str.zfill(6)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return df


def search_stocks(keyword: str, limit: int = 20) -> list[dict]:
    """按代码或名称模糊搜索股票 + ETF。"""
    keyword = keyword.strip()
    if not keyword:
        return []

    # 搜索 A 股
    stocks = get_stock_list()
    m1 = stocks["code"].str.contains(keyword, case=False, na=False)
    m2 = stocks["name"].str.contains(keyword, na=False)
    result = stocks[m1 | m2].head(limit)

    # 搜索 ETF（补充）
    if len(result) < limit:
        try:
            etfs = get_etf_list()
            e1 = etfs["code"].str.contains(keyword, case=False, na=False)
            e2 = etfs["name"].str.contains(keyword, na=False)
            etf_result = etfs[e1 | e2].head(limit - len(result))
            result = pd.concat([result, etf_result], ignore_index=True)
        except Exception:
            pass  # ETF 接口失败不影响股票搜索

    return result.to_dict("records")


# ---------------------------------------------------------------------------
# 日 K 线
# ---------------------------------------------------------------------------

def _to_tx_symbol(code: str) -> str:
    """6位股票代码 → 腾讯格式：600519 → sh600519，000001 → sz000001。"""
    code = str(code).zfill(6)
    # 6/9 开头 = 上海主板/科创板，5 开头 = 上海 ETF
    if code.startswith(("5", "6", "9")):
        return f"sh{code}"
    return f"sz{code}"


def get_daily_kline(
    symbol: str,
    days: int = 500,
    adjust: str = "qfq",
    force_refresh: bool = False,
) -> pd.DataFrame:
    """获取个股日 K 线（前复权，默认最近 500 个交易日）。

    返回列: date, open, close, high, low, volume, amount
    date 为 datetime.date，其余为 float。
    """
    symbol = str(symbol).zfill(6)
    # 固定起始日期 5 年前，缓存键稳定
    start = (datetime.now() - timedelta(days=2000)).strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")

    path = _cache_path(f"kline_{symbol}_{adjust}.csv")
    if not force_refresh and _is_cache_fresh(path, KLINE_CACHE_TTL):
        df = _read_csv_cache(path)
        if df is not None and not df.empty:
            return _normalize_kline(df, days)

    # 优先腾讯数据源（不经过东财 push2 服务器，兼容性更好）
    try:
        raw = _retry(lambda: ak.stock_zh_a_hist_tx(
            symbol=_to_tx_symbol(symbol), start_date=start, end_date=end,
        ))
    except Exception:
        # 腾讯失败则回退东财
        raw = _retry(lambda: ak.stock_zh_a_hist(
            symbol=symbol, period="daily", start_date=start,
            end_date=end, adjust=adjust,
        ))
        if raw is not None and not raw.empty:
            raw = raw.rename(columns={
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume", "成交额": "amount",
            })

    if raw is None or raw.empty:
        return pd.DataFrame(columns=["date", "open", "close", "high", "low", "volume", "amount"])

    raw.to_csv(path, index=False, encoding="utf-8-sig")
    return _normalize_kline(raw, days)


def _normalize_kline(df: pd.DataFrame, days: int = 500) -> pd.DataFrame:
    out = df[["date", "open", "close", "high", "low", "volume", "amount"]].copy()
    out["date"] = pd.to_datetime(out["date"]).dt.date
    for col in ["open", "close", "high", "low", "volume", "amount"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["date"])
    # 只保留最近 N 个交易日
    if len(out) > days:
        out = out.iloc[-days:]
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 实时行情（用于全市场扫描）
# ---------------------------------------------------------------------------

def get_realtime_spot() -> pd.DataFrame:
    """全市场实时行情快照。列: code, name, price, change_pct, volume, amount"""
    raw = _retry(lambda: ak.stock_zh_a_spot_em())
    keep = ["代码", "名称", "最新价", "涨跌幅", "成交量", "成交额"]
    raw = raw[[c for c in keep if c in raw.columns]]
    raw = raw.rename(columns={
        "代码": "code", "名称": "name", "最新价": "price",
        "涨跌幅": "change_pct", "成交量": "volume", "成交额": "amount",
    })
    raw["code"] = raw["code"].astype(str).str.zfill(6)
    for col in ["price", "change_pct", "volume", "amount"]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    return raw