"""买卖点信号引擎：基于经典技术指标的 5 大策略，全部可解释。

策略清单：
1. MACD 金叉（买入）/ 死叉（卖出）
2. 均线金叉：MA5 上穿 MA20（买入）/ 下穿（卖出）
3. KDJ：超卖区 K 上穿 D（买入）/ 超买区 K 下穿 D（卖出）
4. RSI：RSI6 下穿 30 进入超卖（买入）/ 上穿 70 进入超买（卖出）
5. BOLL：收盘价跌穿下轨（买入）/ 突破上轨（卖出）

信号强度 = 同一天同方向多策略共振次数。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core import indicators as ind

# 策略中文名（前端展示用）
STRATEGY_NAMES = {
    "MACD金叉": "MACD 金叉",
    "MACD死叉": "MACD 死叉",
    "均线金叉": "均线金叉 (MA5/MA20)",
    "均线死叉": "均线死叉 (MA5/MA20)",
    "KDJ超卖": "KDJ 超卖买入",
    "KDJ超买": "KDJ 超买卖出",
    "RSI超卖": "RSI 超卖 (RSI6<30)",
    "RSI超买": "RSI 超买 (RSI6>70)",
    "BOLL下轨突破": "BOLL 跌穿下轨",
    "BOLL上轨突破": "BOLL 突破上轨",
}


def _series(df: pd.DataFrame, name: str) -> pd.Series:
    """提取 float Series，规避类型存根推断噪声。"""
    return pd.Series(df[name].to_numpy(dtype=float), index=df.index)


def generate_signals(ind_df: pd.DataFrame) -> pd.DataFrame:
    """从指标 DataFrame 生成信号。

    入参: indicators.compute_all 的输出（必须包含全部指标列）。
    返回 DataFrame 列: date, type(buy/sell), strategy, price, strength
    """
    empty = pd.DataFrame(columns=["date", "type", "strategy", "price", "strength"])
    if ind_df.empty or len(ind_df) < 30:
        return empty

    close = _series(ind_df, "close")
    dif = _series(ind_df, "dif")
    dea = _series(ind_df, "dea")
    ma5 = _series(ind_df, "ma5")
    ma20 = _series(ind_df, "ma20")
    k = _series(ind_df, "k")
    d = _series(ind_df, "d")
    rsi6 = _series(ind_df, "rsi6")
    boll_lower = _series(ind_df, "boll_lower")
    boll_upper = _series(ind_df, "boll_upper")

    idx = ind_df.index

    def _rsi_level(level: float) -> pd.Series:
        return pd.Series(level, index=idx)

    # 各策略触发布尔列: (type, strategy, mask)
    triggers: list[tuple[str, str, pd.Series]] = [
        ("buy", "MACD金叉", ind.cross_up(dif, dea)),
        ("sell", "MACD死叉", ind.cross_down(dif, dea)),
        ("buy", "均线金叉", ind.cross_up(ma5, ma20)),
        ("sell", "均线死叉", ind.cross_down(ma5, ma20)),
        ("buy", "KDJ超卖", ind.cross_up(k, d) & (k < 20)),
        ("sell", "KDJ超买", ind.cross_down(k, d) & (k > 80)),
        ("buy", "RSI超卖", ind.cross_down(rsi6, _rsi_level(30.0))),
        ("sell", "RSI超买", ind.cross_up(rsi6, _rsi_level(70.0))),
        ("buy", "BOLL下轨突破", ind.cross_down(close, boll_lower)),
        ("sell", "BOLL上轨突破", ind.cross_up(close, boll_upper)),
    ]

    records: list[dict] = []
    dates_arr = ind_df["date"].to_numpy()
    prices_arr = np.round(close.to_numpy(), 3)
    for sig_type, strategy, mask in triggers:
        bool_arr = np.asarray(mask.to_numpy(), dtype=bool)
        for pos in np.flatnonzero(bool_arr):
            records.append({
                "date": dates_arr[pos],
                "type": sig_type,
                "strategy": strategy,
                "price": float(prices_arr[pos]),
            })

    if not records:
        return empty

    df = pd.DataFrame(records)
    # 同一天同方向多策略 → strength = 共振次数
    grouped = pd.DataFrame(df.groupby(["date", "type"], as_index=False).agg(
        price=("price", "first"),
        strategy=("strategy", lambda x: "; ".join(x)),
    ))
    strategy_col = pd.Series(grouped["strategy"].to_numpy(), index=grouped.index)
    grouped["strength"] = strategy_col.str.count(";") + 1
    grouped = pd.DataFrame(grouped.sort_values("date").reset_index(drop=True))
    return grouped


def latest_signal_status(signals: pd.DataFrame) -> dict:
    """最近一天的信号状态汇总（用于扫描列表展示）。"""
    empty_status = {"has_signal": False, "buy": False, "sell": False,
                    "strength": 0, "date": None, "detail": ""}
    if signals is None or signals.empty:
        return empty_status
    last_date = pd.Series(signals["date"].to_numpy()).max()
    mask = pd.Series(signals["date"].to_numpy()) == last_date
    last = pd.DataFrame(signals[mask.to_numpy()])
    buys = pd.DataFrame(last[last["type"] == "buy"])
    sells = pd.DataFrame(last[last["type"] == "sell"])
    strength = int(float(pd.Series(last["strength"].to_numpy()).max()))
    return {
        "has_signal": not last.empty,
        "buy": not buys.empty,
        "sell": not sells.empty,
        "strength": strength,
        "date": str(last_date),
        "detail": "；".join(last["strategy"].tolist()),
    }