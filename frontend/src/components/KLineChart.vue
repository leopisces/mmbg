<template>
  <div class="chart-container">
    <div ref="chartRef" class="chart"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { KLineItem, Signal } from '../api'

const props = defineProps<{
  data: KLineItem[]
  signals: Signal[]
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function buildOption(data: KLineItem[], signals: Signal[]) {
  const dates = data.map(d => d.date)
  const ohlc = data.map(d => [d.open, d.close, d.low, d.high])
  const volumes = data.map(d => d.volume)
  const ma5 = data.map(d => d.ma5)
  const ma10 = data.map(d => d.ma10)
  const ma20 = data.map(d => d.ma20)
  const ma60 = data.map(d => d.ma60)

  // MACD
  const dif = data.map(d => d.dif)
  const dea = data.map(d => d.dea)
  const hist = data.map(d => d.hist)

  // 买卖点标记
  const buySignals: any[] = []
  const sellSignals: any[] = []
  signals.forEach(s => {
    const idx = dates.indexOf(s.date)
    if (idx === -1) return
    const item = {
      coord: [s.date, data[idx].low * 0.995],
      value: `买(${s.strength})`,
      symbol: 'triangle',
      symbolSize: 10 + s.strength * 4,
      symbolRotate: 0,
      itemStyle: { color: '#f56c6c' },
    }
    const sellItem = {
      coord: [s.date, data[idx].high * 1.005],
      value: `卖(${s.strength})`,
      symbol: 'triangle',
      symbolSize: 10 + s.strength * 4,
      symbolRotate: 180,
      itemStyle: { color: '#67c23a' },
    }
    if (s.type === 'buy') buySignals.push(item)
    if (s.type === 'sell') sellSignals.push(sellItem)
  })

  // Volume colors
  const volumeColors = data.map(d => d.close >= d.open ? '#f56c6c' : '#67c23a')

  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      textStyle: { fontSize: 12 },
    },
    legend: {
      data: ['K线', 'MA5', 'MA10', 'MA20', 'MA60', 'DIF', 'DEA', 'MACD'],
      top: 0,
      textStyle: { fontSize: 11 },
    },
    axisPointer: {
      link: [{ xAxisIndex: [0, 1, 2] }],
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1, 2], start: 60, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1, 2], bottom: 5, height: 20 },
    ],
    grid: [
      { left: '8%', right: '3%', top: '8%', height: '48%' },
      { left: '8%', right: '3%', top: '60%', height: '12%' },
      { left: '8%', right: '3%', top: '76%', height: '12%' },
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false } },
      { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false } },
      { type: 'category', data: dates, gridIndex: 2, axisLabel: { fontSize: 10 } },
    ],
    yAxis: [
      { scale: true, gridIndex: 0, splitLine: { lineStyle: { type: 'dashed' } } },
      { scale: true, gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false } },
      { scale: true, gridIndex: 2, splitLine: { show: false }, axisLabel: { show: false } },
    ],
    series: [
      // K线
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#f56c6c',
          color0: '#67c23a',
          borderColor: '#f56c6c',
          borderColor0: '#67c23a',
        },
        markPoint: {
          data: [...buySignals, ...sellSignals],
          label: { show: false },
        },
      },
      // 均线
      { name: 'MA5', type: 'line', data: ma5, xAxisIndex: 0, yAxisIndex: 0, smooth: true, lineStyle: { width: 1 }, symbol: 'none' },
      { name: 'MA10', type: 'line', data: ma10, xAxisIndex: 0, yAxisIndex: 0, smooth: true, lineStyle: { width: 1 }, symbol: 'none' },
      { name: 'MA20', type: 'line', data: ma20, xAxisIndex: 0, yAxisIndex: 0, smooth: true, lineStyle: { width: 1 }, symbol: 'none' },
      { name: 'MA60', type: 'line', data: ma60, xAxisIndex: 0, yAxisIndex: 0, smooth: true, lineStyle: { width: 1 }, symbol: 'none' },
      // 成交量
      {
        name: '成交量',
        type: 'bar',
        data: volumes.map((v, i) => ({
          value: v,
          itemStyle: { color: volumeColors[i] },
        })),
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
      // MACD
      {
        name: 'DIF',
        type: 'line',
        data: dif,
        xAxisIndex: 2,
        yAxisIndex: 2,
        lineStyle: { width: 1 },
        symbol: 'none',
      },
      {
        name: 'DEA',
        type: 'line',
        data: dea,
        xAxisIndex: 2,
        yAxisIndex: 2,
        lineStyle: { width: 1 },
        symbol: 'none',
      },
      {
        name: 'MACD',
        type: 'bar',
        data: hist?.map((v, i) => ({
          value: v,
          itemStyle: { color: v != null && v >= 0 ? '#f56c6c' : '#67c23a' },
        })),
        xAxisIndex: 2,
        yAxisIndex: 2,
      },
    ],
  }
}

function renderChart() {
  if (!chartRef.value || !props.data.length) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }
  chart.setOption(buildOption(props.data, props.signals), true)
}

onMounted(() => {
  nextTick(renderChart)
  window.addEventListener('resize', () => chart?.resize())
})

watch(() => [props.data, props.signals], renderChart, { deep: true })
</script>

<style scoped>
.chart-container {
  width: 100%;
  background: #fff;
}

.chart {
  width: 100%;
  height: 600px;
}
</style>