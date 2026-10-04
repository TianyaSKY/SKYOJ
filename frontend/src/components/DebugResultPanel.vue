<template>
  <div v-loading="loading" class="debug-panel">
    <el-card class="status-card mb-4" shadow="never">
      <div class="status-row">
        <div class="status-block">
          <span class="status-label">对错判断：</span>
          <el-tag :type="verdictTagType" effect="dark" size="large">
            {{ verdictText }}
          </el-tag>
        </div>
        <div class="status-block">
          <el-tag :type="statusTagType" effect="plain">{{ statusText }}</el-tag>
          <el-tag class="ml-2" effect="plain">{{ detail?.language || '-' }}</el-tag>
          <el-tag v-if="detail?.case_name" class="ml-2" effect="plain">用例 {{ detail.case_name }}</el-tag>
        </div>
      </div>
    </el-card>

    <el-card class="diff-card mb-4" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="header-title">输入 / 期望输出 / 你的输出</span>
        </div>
      </template>
      <div class="diff-grid">
        <div class="diff-col">
          <div class="col-title">输入（第一个测试点）</div>
          <pre class="io-block">{{ detail?.input ?? '(无)' }}</pre>
        </div>
        <div class="diff-col">
          <div class="col-title">真实答案（期望输出）</div>
          <pre class="io-block">{{ detail?.expected_output ?? '(无)' }}</pre>
        </div>
        <div class="diff-col">
          <div class="col-title">你的输出</div>
          <pre :class="['io-block', isWrongAnswer ? 'is-wrong' : '']">{{
              detail?.actual_output ?? '(运行后才有输出)'
            }}</pre>
        </div>
      </div>
    </el-card>

    <el-card v-if="detail?.error_output" class="error-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="header-title">错误输出 / 编译信息</span>
        </div>
      </template>
      <pre class="error-block">{{ detail.error_output }}</pre>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import {computed, onBeforeUnmount, ref, watch} from 'vue'
import type { DebugRunResponse } from '@/types/debug'
import {getDebugRun} from '@/api/debug'
import {ElMessage} from 'element-plus'

const props = defineProps({
  debugRunId: {
    type: Number,
    required: true
  }
})

const detail = ref<DebugRunResponse | null>(null)
const loading = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null
let timeoutTimer: ReturnType<typeof setTimeout> | null = null
let generation = 0
let disposed = false
const MAX_POLL_DURATION_MS = 180000  // 每次运行最多等待三分钟

const isWrongAnswer = computed(() => detail.value?.status === 'Wrong Answer')

const statusText = computed(() => detail.value?.status || 'Pending')

const verdictText = computed(() => {
  if (!detail.value) return '等待判题…'
  switch (detail.value.status) {
    case 'Accepted':
      return '正确'
    case 'Wrong Answer':
      return '错误'
    case 'Compile Error':
      return '编译错误'
    case 'Runtime Error':
      return '运行时错误'
    case 'Time Limit Exceeded':
      return '超时'
    case 'System Error':
      return '系统错误'
    case 'Pending':
    default:
      return '判题中…'
  }
})

const verdictTagType = computed(() => {
  switch (detail.value?.status) {
    case 'Accepted':
      return 'success'
    case 'Wrong Answer':
    case 'Runtime Error':
      return 'danger'
    case 'Compile Error':
      return 'warning'
    case 'Time Limit Exceeded':
      return 'warning'
    case 'System Error':
      return 'info'
    case 'Pending':
    default:
      return 'info'
  }
})

const statusTagType = computed(() => {
  if (!detail.value) return 'info'
  switch (detail.value.status) {
    case 'Accepted':
      return 'success'
    case 'Wrong Answer':
    case 'Runtime Error':
    case 'Compile Error':
      return 'danger'
    case 'Time Limit Exceeded':
      return 'warning'
    default:
      return 'info'
  }
})

const fetchDebugRun = async (silent = false) => {
  const currentGeneration = generation
  const id = props.debugRunId
  if (!id || disposed) return
  if (!silent) loading.value = true
  try {
    const data = await getDebugRun(id)
    if (disposed || currentGeneration !== generation) return
    detail.value = data
    if (data.status && data.status !== 'Pending') {
      stopPolling()
    } else {
      startPolling()
    }
  } catch (err) {
    if (disposed || currentGeneration !== generation) return
    console.error('获取调试结果失败', err)
    ElMessage.error('获取调试结果失败，请稍后重试')
    stopPolling()
  } finally {
    if (!silent && !disposed && currentGeneration === generation) loading.value = false
  }
}

const startPolling = () => {
  if (disposed || timer !== null) return
  // 上次请求完成后再轮询，避免慢请求重叠。
  timer = setTimeout(() => {
    timer = null
    fetchDebugRun(true)
  }, 1500)
}

const stopPolling = () => {
  if (timer !== null) {
    clearTimeout(timer)
    timer = null
  }
  if (timeoutTimer !== null) {
    clearTimeout(timeoutTimer)
    timeoutTimer = null
  }
}

watch(
    () => props.debugRunId,
    (newId) => {
      generation++
      stopPolling()
      detail.value = null
      loading.value = false
      if (newId) {
        timeoutTimer = setTimeout(() => {
          generation++
          stopPolling()
          loading.value = false
          ElMessage.warning('判题超时，请稍后刷新重试')
        }, MAX_POLL_DURATION_MS)
        fetchDebugRun()
      }
    },
    {immediate: true}
)

onBeforeUnmount(() => {
  disposed = true
  generation++
  stopPolling()
})

</script>

<style scoped>
.debug-panel {
  padding: 0 16px 16px;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.mb-4 {
  margin-bottom: 16px;
}

.ml-2 {
  margin-left: 8px;
}

.status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.status-block {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.status-label {
  font-weight: 600;
  color: #303133;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-weight: 600;
  color: #303133;
}

.diff-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}

@media (max-width: 1100px) {
  .diff-grid {
    grid-template-columns: 1fr;
  }
}

.diff-col {
  display: flex;
  flex-direction: column;
}

.col-title {
  font-size: 0.9rem;
  color: #606266;
  margin-bottom: 8px;
  font-weight: 600;
}

.io-block {
  background-color: #f8f9fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px;
  min-height: 120px;
  max-height: 320px;
  overflow: auto;
  font-family: 'Fira Code', Consolas, 'Courier New', monospace;
  font-size: 0.85rem;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  color: #303133;
}

.io-block.is-wrong {
  background-color: #fef0f0;
  border-color: #fbc4c4;
  color: #c45656;
}

.error-block {
  background-color: #fef0f0;
  border: 1px solid #fbc4c4;
  border-radius: 6px;
  padding: 12px;
  font-family: 'Fira Code', Consolas, 'Courier New', monospace;
  font-size: 0.85rem;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  color: #c45656;
  max-height: 240px;
  overflow: auto;
}
</style>
