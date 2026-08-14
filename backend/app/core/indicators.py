"""技术指标计算引擎：纯 pandas/numpy 实现，与主流行情软件（东方财富/通达信）口径一致。

统一约定：
- 所有函数输入 pandas.Series，返回 Series 或 Series 元组
- 不修改输入，NaN 前导值保留
- 返回处统一用 pd.Series(...) 包装，规避类型存根推断噪声
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ma(close: pd.Series, n: int = 20) -> pd.Series:
    """简单移动平均线 MA"""
    return pd.Series(close.rolling(window=n, min_periods=n).mean())


def ema(close: pd.Series, n: int = 12) -> pd.Series:
    """指数移动平均线 EMA（alpha = 2/(n+1)，与行情软件一致）"""
    return pd.Series(close.ewm(span=n, adjust=False).mean())


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD 指标。

    返回 (dif, dea, hist)，其中 hist = 2*(dif-dea)（国内软件惯例）。
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    dif = ema_fast - ema_slow
    dea = ema(dif, signal)
    hist = 2.0 * (dif - dea)
    return dif, dea, hist


def kdj(high: pd.Series, low: pd.Series, close: pd.Series,
        n: int = 9, m1: int = 3, m2: int = 3):
    """KDJ 随机指标。

    RSV = (C - L_n) / (H_n - L_n) * 100
    K = SMA(RSV, m1, 1)，D = SMA(K, m2, 1)，J = 3K - 2D
    其中 SMA(X, N, M) 为国内软件平滑算法 Y = (M*X + (N-M)*Y_prev)/N，
    等价于 pandas ewm(alpha=M/N, adjust=False)。
    """
    low_n = pd.Series(low.rolling(window=n, min_periods=1).min())
    high_n = pd.Series(high.rolling(window=n, min_periods=1).max())
    denom = high_n - low_n
    rsv = (close - low_n) / denom * 100.0
    # 一字板（high==low）时 0/0 → 用中性值 50
    rsv = rsv.where(denom != 0, 50.0)
    k = pd.Series(rsv.ewm(alpha=1.0 / m1, adjust=False).mean())
    d = pd.Series(k.ewm(alpha=1.0 / m2, adjust=False).mean())
    j = 3.0 * k - 2.0 * d
    return k, d, j


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """RSI 相对强弱指标（Wilder 平滑，与国内软件一致）。

    RSI = 100 - 100 / (1 + RS)，RS = 平均涨幅 / 平均跌幅。
    边界：avg_loss==0 → RSI=100；avg_gain==0 且 avg_loss>0 → RSI=0。
    """
    delta = close.diff()
    gain = pd.Series(delta.clip(lower=0.0))
    loss = pd.Series((-delta).clip(lower=0.0))
    avg_gain = pd.Series(gain.ewm(alpha=1.0 / n, adjust=False).mean())
    avg_loss = pd.Series(loss.ewm(alpha=1.0 / n, adjust=False).mean())
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    result = pd.Series(100.0 - 100.0 / (1.0 + rs))
    result = result.fillna(0.0)
    # avg_loss == 0（无跌幅）→ 100；否则用计算值
    values = np.where(avg_loss.to_numpy() > 0, result.to_numpy(), 100.0)
    return pd.Series(values, index=close.index)


def boll(close: pd.Series, n: int = 20, k: float = 2.0):
    """BOLL 布林带。

    中轨 = MA(n)，上下轨 = 中轨 ± k * 标准差(n, ddof=0)。
    国内软件使用总体标准差（ddof=0）。
    """
    mid = pd.Series(close.rolling(window=n, min_periods=n).mean())
    std = pd.Series(close.rolling(window=n, min_periods=n).std(ddof=0))
    upper = mid + k * std
    lower = mid - k * std
    return mid, upper, lower


def cross_up(a: pd.Series, b: pd.Series) -> pd.Series:
    """a 上穿 b：前值 a<=b 且当前 a>b（NaN 视为不触发）"""
    prev_ok = a.shift(1) <= b.shift(1)
    curr_ok = a > b
    return pd.Series((prev_ok & curr_ok).fillna(False))


def cross_down(a: pd.Series, b: pd.Series) -> pd.Series:
    """a 下穿 b：前值 a>=b 且当前 a<b"""
    prev_ok = a.shift(1) >= b.shift(1)
    curr_ok = a < b
    return pd.Series((prev_ok & curr_ok).fillna(False))


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """从 DataFrame 提取 float Series，规避类型存根推断噪声。"""
    return pd.Series(df[name].to_numpy(dtype=float), index=df.index)


def compute_all(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """一次性计算全部指标，合并到原 DataFrame。

    输入列: date, open, close, high, low, volume
    新增列: ma5, ma10, ma20, ma60, dif, dea, hist,
            k, d, j, rsi6, rsi14, boll_mid, boll_upper, boll_lower
    """
    out = ohlcv.copy()
    close = _col(out, "close")
    high = _col(out, "high")
    low = _col(out, "low")

    out["ma5"] = ma(close, 5)
    out["ma10"] = ma(close, 10)
    out["ma20"] = ma(close, 20)
    out["ma60"] = ma(close, 60)

    dif, dea, hist = macd(close)
    out["dif"], out["dea"], out["hist"] = dif, dea, hist

    k, d, j = kdj(high, low, close)
    out["k"], out["d"], out["j"] = k, d, j

    out["rsi6"] = rsi(close, 6)
    out["rsi14"] = rsi(close, 14)

    mid, upper, lower = boll(close)
    out["boll_mid"], out["boll_upper"], out["boll_lower"] = mid, upper, lower

    return out