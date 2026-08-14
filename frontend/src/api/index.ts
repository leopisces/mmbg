import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export interface StockInfo {
  code: string
  name: string
}

export interface KLineItem {
  date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
  amount: number
  ma5: number | null
  ma10: number | null
  ma20: number | null
  ma60: number | null
  dif: number | null
  dea: number | null
  hist: number | null
  k: number | null
  d: number | null
  j: number | null
  rsi6: number | null
  rsi14: number | null
  boll_mid: number | null
  boll_upper: number | null
  boll_lower: number | null
}

export interface Signal {
  date: string
  type: 'buy' | 'sell'
  strategy: string
  price: number
  strength: number
}

export interface AnalyzeResult {
  code: string
  name: string
  kline: KLineItem[]
  signals: Signal[]
  latest_signal: {
    has_signal: boolean
    buy: boolean
    sell: boolean
    strength: number
    date: string | null
    detail: string
  }
  counts: { buy: number; sell: number }
}

export async function searchStocks(keyword: string): Promise<StockInfo[]> {
  const { data } = await api.get('/stocks/search', { params: { keyword } })
  return data
}

export async function analyzeStock(code: string, days = 200): Promise<AnalyzeResult> {
  const { data } = await api.get(`/analyze/${code}`, { params: { days } })
  return data
}

export async function getWatchlist(): Promise<StockInfo[]> {
  const { data } = await api.get('/watchlist')
  return data
}

export async function addWatch(code: string, name: string): Promise<void> {
  await api.post(`/watchlist/${code}`, null, { params: { name } })
}

export async function removeWatch(code: string): Promise<void> {
  await api.delete(`/watchlist/${code}`)
}