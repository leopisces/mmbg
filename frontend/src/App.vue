<template>
  <div class="app">
    <header class="header">
      <h1>A股买卖点分析</h1>
      <p class="disclaimer">基于经典技术指标，仅供研究参考，不构成投资建议</p>
    </header>

    <div class="search-bar">
      <input
        v-model="keyword"
        placeholder="输入股票代码或名称，如 600519 或 茅台"
        @keyup.enter="doSearch"
        class="search-input"
      />
      <button @click="doSearch" class="btn btn-primary">搜索</button>
      <button @click="analyze" class="btn btn-success" :disabled="!selectedCode">
        分析 {{ selectedCode || '' }}
      </button>
    </div>

    <div v-if="searchResults.length" class="search-results">
      <div
        v-for="s in searchResults"
        :key="s.code"
        class="search-item"
        :class="{ active: s.code === selectedCode }"
        @click="selectStock(s)"
      >
        <span class="code">{{ s.code }}</span>
        <span class="name">{{ s.name }}</span>
      </div>
    </div>

    <div v-if="loading" class="loading">分析中，请稍候...</div>

    <div v-if="result" class="result-panel">
      <div class="stock-header">
        <h2>{{ result.name }} ({{ result.code }})</h2>
        <div class="signal-summary">
          <span class="count buy">买入信号: {{ result.counts.buy }}</span>
          <span class="count sell">卖出信号: {{ result.counts.sell }}</span>
          <span v-if="result.latest_signal.has_signal" class="latest-signal" :class="result.latest_signal.buy ? 'buy' : 'sell'">
            最新: {{ result.latest_signal.detail }} ({{ result.latest_signal.date }})
          </span>
        </div>
      </div>

      <KLineChart :data="result.kline" :signals="result.signals" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { searchStocks, analyzeStock, type StockInfo, type AnalyzeResult } from './api'
import KLineChart from './components/KLineChart.vue'

const keyword = ref('')
const searchResults = ref<StockInfo[]>([])
const selectedCode = ref('')
const selectedName = ref('')
const loading = ref(false)
const result = ref<AnalyzeResult | null>(null)

async function doSearch() {
  if (!keyword.value.trim()) return
  searchResults.value = await searchStocks(keyword.value.trim())
  if (searchResults.value.length === 1) {
    selectStock(searchResults.value[0])
  }
}

function selectStock(s: StockInfo) {
  selectedCode.value = s.code
  selectedName.value = s.name
  searchResults.value = []
  keyword.value = `${s.code} ${s.name}`
}

async function analyze() {
  if (!selectedCode.value) return
  loading.value = true
  result.value = null
  try {
    result.value = await analyzeStock(selectedCode.value)
  } catch (e: any) {
    alert('分析失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.app {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  text-align: center;
  margin-bottom: 24px;
}

.header h1 {
  font-size: 28px;
  color: #1a1a1a;
  margin-bottom: 4px;
}

.disclaimer {
  color: #999;
  font-size: 13px;
}

.search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.search-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: #409eff;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn:hover { opacity: 0.85; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #409eff; color: #fff; }
.btn-success { background: #67c23a; color: #fff; }

.search-results {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 16px;
  max-height: 200px;
  overflow-y: auto;
}

.search-item {
  padding: 10px 16px;
  cursor: pointer;
  display: flex;
  gap: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.search-item:hover { background: #f5f7fa; }
.search-item.active { background: #ecf5ff; }

.search-item .code { font-weight: 600; color: #333; }
.search-item .name { color: #666; }

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
  font-size: 16px;
}

.result-panel {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.stock-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 8px;
}

.stock-header h2 {
  font-size: 20px;
  color: #1a1a1a;
}

.signal-summary {
  display: flex;
  gap: 12px;
  align-items: center;
}

.count {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
}

.count.buy { background: #fef0f0; color: #f56c6c; }
.count.sell { background: #f0f9eb; color: #67c23a; }

.latest-signal {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
}

.latest-signal.buy { background: #f56c6c; color: #fff; }
.latest-signal.sell { background: #67c23a; color: #fff; }
</style>