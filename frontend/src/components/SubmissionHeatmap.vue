<template>
  <div class="heatmap-container">
    <div class="heatmap-header">
      <span class="total-count">{{ totalSubmissions }} submissions in the last year</span>
    </div>
    <div class="heatmap-scroll">
      <div :style="{ gridTemplateColumns: `repeat(${weeks.length}, 1fr)` }" class="heatmap-grid">
        <div v-for="(week, wIndex) in weeks" :key="wIndex" class="heatmap-week">
          <div
              v-for="(day, dIndex) in week"
              :key="dIndex"
              :class="getColorClass(day.count)"
              :title="formatTitle(day)"
              class="heatmap-day"
          ></div>
        </div>
      </div>
    </div>
    <div class="heatmap-footer">
      <span>Less</span>
      <div class="legend">
        <div class="heatmap-day level-0"></div>
        <div class="heatmap-day level-1"></div>
        <div class="heatmap-day level-2"></div>
        <div class="heatmap-day level-3"></div>
        <div class="heatmap-day level-4"></div>
      </div>
      <span>More</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import {computed} from 'vue'
import { parseServerDate } from '@/utils/date'

interface ActivityDay { date: string; count: number }
const props = defineProps<{ submissions: Array<{ created_at: string | null }> }>()

const dateKey = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

const activity = computed(() => {
  const now = new Date()
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const start = new Date(end)
  start.setFullYear(end.getFullYear() - 1)
  // 闰年的 2 月 29 日对应上一年的 2 月最后一天。
  if (start.getMonth() !== end.getMonth()) start.setDate(0)
  const firstDate = dateKey(start), lastDate = dateKey(end)
  const counts = new Map<string, number>()
  let total = 0
  for (const submission of props.submissions) {
    const date = parseServerDate(submission.created_at)
    if (!date || date > now) continue
    const key = dateKey(date)
    if (key < firstDate || key > lastDate) continue
    counts.set(key, (counts.get(key) || 0) + 1)
    total += 1
  }

  const current = new Date(start)
  current.setDate(current.getDate() - current.getDay())
  const weeks: ActivityDay[][] = []
  let dayIndex = 0
  // 每次递增日历日期，用序号分周，不依赖夏令时下每天的毫秒数。
  while (current <= end || current.getDay() !== 0) {
    const weekIndex = Math.floor(dayIndex / 7)
    if (!weeks[weekIndex]) weeks[weekIndex] = []
    const key = dateKey(current)
    weeks[weekIndex].push({ date: key, count: counts.get(key) || 0 })
    current.setDate(current.getDate() + 1)
    dayIndex += 1
  }
  return { weeks, total }
})

const totalSubmissions = computed(() => activity.value.total)
const weeks = computed(() => activity.value.weeks)

const getColorClass = (count: number) => {
  if (count === 0) return 'level-0'
  if (count <= 2) return 'level-1'
  if (count <= 5) return 'level-2'
  if (count <= 10) return 'level-3'
  return 'level-4'
}

const formatTitle = (day: ActivityDay) => {
  return `${day.count} submissions on ${day.date}`
}
</script>

<style scoped>
.heatmap-container {
  padding: 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background-color: var(--el-bg-color);
  font-size: 12px;
}

.heatmap-header {
  margin-bottom: 10px;
  font-weight: 500;
}

.heatmap-scroll {
  overflow-x: auto;
  padding-bottom: 8px;
}

.heatmap-grid {
  display: grid;
  gap: 3px;
  min-width: max-content;
}

.heatmap-week {
  display: grid;
  grid-template-rows: repeat(7, 1fr);
  gap: 3px;
}

.heatmap-day {
  width: 11px;
  height: 11px;
  border-radius: 2px;
  background-color: var(--el-fill-color-lighter);
}

.heatmap-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
  color: var(--el-text-color-secondary);
}

.legend {
  display: flex;
  gap: 3px;
}

/* GitHub-like colors */
.level-0 {
  background-color: var(--el-fill-color-lighter);
}

.level-1 {
  background-color: #9be9a8;
}

.level-2 {
  background-color: #40c463;
}

.level-3 {
  background-color: #30a14e;
}

.level-4 {
  background-color: #216e39;
}

/* Dark mode adjustments if needed */
:deep(.dark) .level-1 {
  background-color: #0e4429;
}

:deep(.dark) .level-2 {
  background-color: #006d32;
}

:deep(.dark) .level-3 {
  background-color: #26a641;
}

:deep(.dark) .level-4 {
  background-color: #39d353;
}
</style>
