"""应用配置"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 数据缓存目录（日K CSV 缓存，避免重复请求 akshare）
CACHE_DIR = BASE_DIR / "data_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 日K缓存有效期（秒），默认 1 天
KLINE_CACHE_TTL = int(os.environ.get("KLINE_CACHE_TTL", 24 * 3600))

# 全市场股票列表缓存有效期（秒）
STOCK_LIST_CACHE_TTL = int(os.environ.get("STOCK_LIST_CACHE_TTL", 12 * 3600))

# SQLite 数据库（自选股等）
DB_PATH = BASE_DIR / "mmbg.db"

# 股票代码格式：6 位数字，如 600519 / 000001
