<template>
  <div class="submission-detail-container">
    <el-alert v-if="loadError" class="mb-4" type="error" title="提交详情加载失败" :closable="false" show-icon>
      <el-button :loading="loading" :disabled="loading" size="small" @click="retrySubmission">重新加载</el-button>
    </el-alert>
    <!-- Status Overview -->
    <el-card v-loading="loading" class="status-card mb-4" shadow="hover">
      <div class="status-wrapper">
        <div class="status-main">
          <div class="status-icon">
            <el-icon v-if="submission.status === 'Accepted'" :size="50" color="#67C23A">
              <CircleCheckFilled/>
            </el-icon>
            <el-icon v-else-if="submission.status === 'Wrong Answer'" :size="50" color="#F56C6C">
              <CircleCloseFilled/>
            </el-icon>
            <el-icon v-else-if="isPending" :size="50" class="is-loading" color="#409EFF">
              <Loading/>
            </el-icon>
            <el-icon v-else :size="50" color="#E6A23C">
              <QuestionFilled/>
            </el-icon>
          </div>
          <div class="status-text">
            <h1 :class="getStatusClass(submission.status)">{{ submission.status }}</h1>
            <div class="meta-info">
              <el-tag class="mr-2" effect="plain" size="small">{{ submission.language }}</el-tag>
              <span class="time-text"><el-icon><Clock/></el-icon> {{ formatTime(submission.created_at) }}</span>
            </div>
          </div>
        </div>

        <div class="score-display">
          <el-progress
              :color="getScoreColor"
              :percentage="submission.score"
              :width="80"
              type="dashboard"
          >
            <template #default="{ percentage }">
              <span class="score-value">{{ percentage }}</span>
            </template>
          </el-progress>
        </div>
      </div>
    </el-card>

    <!-- Judge Log / Test Cases -->
    <el-card v-if="submission.log" class="log-card mb-4" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="header-title"><el-icon><List/></el-icon> Judge Feedback</span>
        </div>
      </template>
      <div class="log-content">
        <pre>{{ submission.log }}</pre>
      </div>
    </el-card>

    <!-- Source Code -->
    <el-card class="code-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="header-title"><el-icon><Document/></el-icon> Source Code</span>
          <el-button :icon="CopyDocument" size="small" @click="copyCode">Copy</el-button>
        </div>
      </template>
      <div class="editor-wrapper">
        <vue-monaco-editor
            v-if="submission.code"
            v-model:value="submission.code"
            :language="submission.language || 'python'"
            :options="editorOptions"
            class="monaco-editor"
            theme="vs-light"
        />
        <el-empty v-else description="No code available"/>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import {computed, onUnmounted, ref, watch} from 'vue'
import {useRoute} from 'vue-router'
import { formatServerDateTime as formatTime } from '@/utils/date'
import type { SubmissionDetailResponse } from '@/types/submission'
import type { editor } from 'monaco-editor'
import { parseRouteId } from '@/utils/route'
import {getSubmissionDetail} from '@/api/problem'
import {ElMessage} from 'element-plus'
import {VueMonacoEditor} from '@guolao/vue-monaco-editor'
import {
  CircleCheckFilled,
  CircleCloseFilled,
  Clock,
  CopyDocument,
  Document,
  List,
  Loading,
  QuestionFilled
} from '@element-plus/icons-vue'

const route = useRoute()
const loading = ref(false)
const loadError = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null
let requestVersion = 0
let disposed = false

const initialSubmission = (id: unknown): Omit<SubmissionDetailResponse, 'id'> & {id: number | null} => ({
  id: parseRouteId(id),
  status: 'Loading...',
  score: 0,
  log: '',
  code: '',
  language: 'python',
  created_at: '',
  exam_id: null,
  case_results: []
})
const submission = ref(initialSubmission(route.params.id))

const isPending = computed(() => {
  const pendingStatuses = ['Pending', 'Judging', 'Compiling', 'Loading...']
  return pendingStatuses.includes(submission.value.status)
})

const editorOptions: editor.IStandaloneEditorConstructionOptions = {
  readOnly: true,
  automaticLayout: true,
  minimap: {enabled: false},
  scrollBeyondLastLine: false,
  fontSize: 14,
  fontFamily: "'Fira Code', 'Consolas', monospace",
  renderWhitespace: 'selection'
}

const getStatusClass = (status: string) => {
  if (!status) return ''
  const s = status.toLowerCase()
  if (s === 'accepted') return 'status-success'
  if (s === 'wrong answer' || s.includes('error')) return 'status-danger'
  if (['pending', 'judging', 'compiling'].includes(s)) return 'status-info'
  return 'status-warning'
}

const getScoreColor = (percentage: number) => {
  if (percentage === 100) return '#67C23A'
  if (percentage >= 60) return '#E6A23C'
  return '#F56C6C'
}


const copyCode = async () => {
  try {
    await navigator.clipboard.writeText(submission.value.code || '')
    ElMessage.success('Code copied to clipboard')
  } catch (err) {
    ElMessage.error('Failed to copy code')
  }
}

const fetchSubmission = async (silent = false) => {
  const version = ++requestVersion
  const submissionId = parseRouteId(route.params.id)
  if (!silent) loading.value = true
  try {
    if (submissionId === null) throw new Error('提交 ID 无效')
    const data = await getSubmissionDetail(submissionId)
    if (disposed || version !== requestVersion) return
    submission.value = data
    loadError.value = false

    if (isPending.value) {
      startPolling()
    } else {
      stopPolling()
    }
  } catch (error) {
    if (disposed || version !== requestVersion) return
    loadError.value = true
    if (submission.value.status === 'Loading...') submission.value.status = 'Load Failed'
    ElMessage.error('Failed to load submission details')
    stopPolling()
  } finally {
    if (!silent && !disposed && version === requestVersion) loading.value = false
  }
}

const retrySubmission = async () => {
  if (disposed || loading.value) return
  stopPolling()
  await fetchSubmission()
}

const startPolling = () => {
  if (disposed || timer !== null) return
  // 上次查询完成后再等待两秒，避免慢请求产生重叠轮询。
  timer = setTimeout(() => {
    timer = null
    fetchSubmission(true)
  }, 2000)
}

const stopPolling = () => {
  if (timer !== null) {
    clearTimeout(timer)
    timer = null
  }
}

watch(() => route.params.id, (id) => {
  stopPolling()
  submission.value = initialSubmission(id)
  loadError.value = false
  fetchSubmission()
}, { immediate: true })

onUnmounted(() => {
  disposed = true
  requestVersion++
  stopPolling()
})
</script>

<style scoped>
.submission-detail-container {
  max-width: 1000px;
  margin: 0 auto;
  padding-bottom: 40px;
}

.mb-4 {
  margin-bottom: 20px;
}

.mt-2 {
  margin-top: 8px;
}

.status-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
}

.status-main {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-text h1 {
  margin: 0 0 5px 0;
  font-size: 2rem;
}

.status-success {
  color: var(--el-color-success);
}

.status-danger {
  color: var(--el-color-danger);
}

.status-warning {
  color: var(--el-color-warning);
}

.status-info {
  color: var(--el-color-primary);
}

.meta-info {
  display: flex;
  align-items: center;
  font-size: 0.9rem;
}

.time-text {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mr-2 {
  margin-right: 10px;
}

.score-value {
  font-size: 1.5rem;
  font-weight: bold;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.log-content pre {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  font-family: 'Consolas', monospace;
  white-space: pre-wrap;
  margin: 0;
  color: #303133;
}

.code-card {
  display: flex;
  flex-direction: column;
}

.editor-wrapper {
  height: 500px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
}

.monaco-editor {
  width: 100%;
  height: 100%;
}

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
