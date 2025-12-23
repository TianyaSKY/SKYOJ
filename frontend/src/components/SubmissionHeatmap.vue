<template>
  <div class="heatmap-container">
    <div class="heatmap-header">
      <span class="total-count">{{ totalSubmissions }} submissions in the last year</span>
    </div>
    <div class="heatmap-scroll">
      <div class="heatmap-grid" :style="{ gridTemplateColumns: `repeat(${weeks.length}, 1fr)` }">
        <div v-for="(week, wIndex) in weeks" :key="wIndex" class="heatmap-week">
          <div
            v-for="(day, dIndex) in week"
            :key="dIndex"
            class="heatmap-day"
            :class="getColorClass(day.count)"
            :title="formatTitle(day)"
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

<script setup>
import { computed } from 'vue'

const props = defineProps({
  submissions: {
    type: Array,
    required: true
  }
})

const totalSubmissions = computed(() => props.submissions.length)

const weeks = computed(() => {
  const endDate = new Date()
  const startDate = new Date()
  startDate.setFullYear(endDate.getFullYear() - 1)
  // Adjust to the start of the week (Sunday)
  startDate.setDate(startDate.getDate() - startDate.getDay())

  const submissionCounts = {}
  props.submissions.forEach(sub => {
    const date = new Date(sub.created_at).toISOString().split('T')[0]
    submissionCounts[date] = (submissionCounts[date] || 0) + 1
  })

  const weeksArr = []
  let currentDay = new Date(startDate)

  while (currentDay <= endDate || currentDay.getDay() !== 0) {
    const weekIndex = Math.floor(daysBetween(startDate, currentDay) / 7)
    if (!weeksArr[weekIndex]) weeksArr[weekIndex] = []

    const dateStr = currentDay.toISOString().split('T')[0]
    weeksArr[weekIndex].push({
      date: dateStr,
      count: submissionCounts[dateStr] || 0
    })

    currentDay.setDate(currentDay.getDate() + 1)
  }

  return weeksArr
})

function daysBetween(start, end) {
  const diffTime = Math.abs(end - start)
  return Math.floor(diffTime / (1000 * 60 * 60 * 24))
}

const getColorClass = (count) => {
  if (count === 0) return 'level-0'
  if (count <= 2) return 'level-1'
  if (count <= 5) return 'level-2'
  if (count <= 10) return 'level-3'
  return 'level-4'
}

const formatTitle = (day) => {
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
.level-0 { background-color: var(--el-fill-color-lighter); }
.level-1 { background-color: #9be9a8; }
.level-2 { background-color: #40c463; }
.level-3 { background-color: #30a14e; }
.level-4 { background-color: #216e39; }

/* Dark mode adjustments if needed */
:deep(.dark) .level-1 { background-color: #0e4429; }
:deep(.dark) .level-2 { background-color: #006d32; }
:deep(.dark) .level-3 { background-color: #26a641; }
:deep(.dark) .level-4 { background-color: #39d353; }
</style>
