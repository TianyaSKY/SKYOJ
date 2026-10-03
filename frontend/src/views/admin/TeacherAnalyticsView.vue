<template>
  <div class="analytics-container">
    <div class="page-header">
      <h1 class="page-title">学情分析</h1>
      <p class="page-desc">平台全局学习数据，辅助教师优化题目难度与考试设计。</p>
    </div>

    <!-- Stats Overview -->
    <el-row :gutter="20" class="stats-row">
      <el-col v-for="stat in overviewStats" :key="stat.label" :span="6">
        <div class="stat-card">
          <div class="stat-value" :style="{ color: stat.color }">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- 通过率分布 -->
      <el-col :lg="12" :md="24">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <span class="card-title">题目通过率分布</span>
          </template>
          <div v-loading="loading" style="min-height: 280px">
            <div v-if="passRates.length" class="bar-chart">
              <div
                v-for="item in passRates"
                :key="item.problem_id"
                class="bar-row"
              >
                <span class="bar-label" :title="item.title">
                  #{{ item.problem_id }} {{ truncate(item.title, 12) }}
                </span>
                <div class="bar-track">
                  <div
                    class="bar-fill"
                    :style="{ width: item.pass_rate + '%', background: passRateColor(item.pass_rate) }"
                  />
                </div>
                <span class="bar-value">{{ item.pass_rate.toFixed(1) }}%</span>
              </div>
            </div>
            <el-empty v-else description="暂无提交数据" />
          </div>
        </el-card>
      </el-col>

      <!-- 题目难度热力图 -->
      <el-col :lg="12" :md="24">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <span class="card-title">题目难度评估（提交数 × 错误率）</span>
          </template>
          <div v-loading="loading" style="min-height: 280px">
            <div v-if="difficultyData.length" class="heatmap-grid">
              <div
                v-for="item in difficultyData"
                :key="item.problem_id"
                class="heatmap-cell"
                :style="{ background: difficultyColor(item.difficulty) }"
                :title="`#${item.problem_id} ${item.title}: 难度 ${item.difficulty.toFixed(1)}`"
              >
                <span class="cell-id">#{{ item.problem_id }}</span>
                <span class="cell-val">{{ item.difficulty.toFixed(1) }}</span>
              </div>
            </div>
            <el-empty v-else description="暂无题目数据" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 提交趋势 -->
    <el-card class="trend-card" shadow="hover">
      <template #header>
        <span class="card-title">每日提交趋势（近 30 天）</span>
      </template>
      <div v-loading="loading" style="min-height: 200px">
        <div v-if="dailyTrend.length" class="trend-bars">
          <div
            v-for="item in dailyTrend"
            :key="item.date"
            class="trend-bar-col"
          >
            <div class="trend-bar-wrap">
              <div
                class="trend-bar"
                :style="{ height: (item.count / maxDailyCount * 100) + '%' }"
                :title="`${item.date}: ${item.count} 次提交`"
              />
            </div>
            <span class="trend-label">{{ shortDate(item.date) }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无提交趋势数据" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const loading = ref(false)
const analyticsData = ref(null)

const overviewStats = computed(() => {
  if (!analyticsData.value) return []
  const d = analyticsData.value
  return [
    { label: '总提交数', value: d.total_submissions ?? 0, color: '#409EFF' },
    { label: 'AC 次数', value: d.total_accepted ?? 0, color: '#67C23A' },
    { label: '总题目数', value: d.total_problems ?? 0, color: '#E6A23C' },
    { label: '全局通过率', value: ((d.global_pass_rate ?? 0) * 100).toFixed(1) + '%', color: '#F56C6C' },
  ]
})

const passRates = computed(() => analyticsData.value?.problem_pass_rates ?? [])
const difficultyData = computed(() => analyticsData.value?.problem_difficulty ?? [])
const dailyTrend = computed(() => analyticsData.value?.daily_submissions ?? [])

const maxDailyCount = computed(() => {
  const arr = dailyTrend.value
  if (!arr || !arr.length) return 1
  return Math.max(...arr.map(i => i.count))
})

const passRateColor = (rate) => {
  if (rate >= 0.6) return '#67C23A'
  if (rate >= 0.3) return '#E6A23C'
  return '#F56C6C'
}

const difficultyColor = (score) => {
  if (score <= 20) return '#e7f7e7'
  if (score <= 40) return '#fff8e1'
  if (score <= 60) return '#ffe0b2'
  if (score <= 80) return '#ffab91'
  return '#ef9a9a'
}

const truncate = (s, n) => s.length > n ? s.slice(0, n) + '…' : s
const shortDate = (s) => s ? s.slice(5) : ''

const fetchAnalytics = async () => {
  loading.value = true
  try {
    const res = await request({ url: '/admin/analytics', method: 'get' })
    analyticsData.value = res
  } catch {
    ElMessage.error('获取学情数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => { fetchAnalytics() })
</script>

<style scoped>
.analytics-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
}

.page-header {
  margin-bottom: 32px;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 8px;
}

.page-desc {
  color: #888;
  font-size: 1.1rem;
  margin: 0;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
}

.stat-label {
  font-size: 0.9rem;
  color: #888;
  margin-top: 8px;
}

.chart-card, .trend-card {
  border-radius: 12px;
  margin-bottom: 24px;
}

.card-title {
  font-weight: 600;
  font-size: 1.05rem;
}

/* Bar chart */
.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-label {
  width: 120px;
  font-size: 0.85rem;
  color: #606266;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-track {
  flex: 1;
  height: 14px;
  background: #f0f2f5;
  border-radius: 7px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 7px;
  transition: width 0.6s ease;
}

.bar-value {
  width: 50px;
  text-align: right;
  font-size: 0.85rem;
  color: #606266;
  flex-shrink: 0;
}

/* Heatmap grid */
.heatmap-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
  gap: 8px;
}

.heatmap-cell {
  border-radius: 8px;
  padding: 10px 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: default;
  transition: transform 0.2s;
}

.heatmap-cell:hover {
  transform: scale(1.05);
}

.cell-id {
  font-size: 0.75rem;
  font-weight: 700;
  color: #333;
}

.cell-val {
  font-size: 0.85rem;
  font-weight: 600;
  color: #333;
}

/* Trend bars */
.trend-bars {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 180px;
  padding-top: 8px;
}

.trend-bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.trend-bar-wrap {
  width: 100%;
  height: 150px;
  display: flex;
  align-items: flex-end;
}

.trend-bar {
  width: 100%;
  background: #409EFF;
  border-radius: 4px 4px 0 0;
  min-height: 2px;
  transition: height 0.4s ease;
}

.trend-label {
  font-size: 0.7rem;
  color: #909399;
}
</style>
