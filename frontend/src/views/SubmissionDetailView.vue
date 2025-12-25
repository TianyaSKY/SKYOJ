<template>
  <div class="submission-detail-container">
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

    <!-- Plagiarism Alert (Only for Teachers or if student has a log) -->
    <el-alert
      v-if="plagiarismLog"
      :title="`检测到代码相似度过高 (${(plagiarismLog.similarity_score * 100).toFixed(2)}%)`"
      type="warning"
      show-icon
      class="mb-4"
      :closable="false"
    >
      <template #default>
        <p>该提交与提交记录 <el-link type="primary" @click="viewTargetSubmission">#{{ plagiarismLog.target_submission_id }}</el-link> 存在高度相似性。</p>
        <div v-if="isTeacher" class="mt-2">
          <el-button type="warning" size="small" @click="compareCode">对比代码</el-button>
        </div>
      </template>
    </el-alert>

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

<script setup>
import {computed, onMounted, onUnmounted, ref} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {getSubmissionDetail} from '@/api/problem'
import {getPlagiarismDetail} from '@/api/plagiarism'
import {useUserStore} from '@/stores/user'
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
const router = useRouter()
const userStore = useUserStore()
const submissionId = route.params.id
const loading = ref(false)
let timer = null

const submission = ref({
  id: submissionId,
  status: 'Loading...',
  score: 0,
  log: '',
  code: '',
  language: 'python',
  created_at: ''
})

const plagiarismLog = ref(null)
const isTeacher = computed(() => userStore.user?.role === 'teacher')

const isPending = computed(() => {
  const pendingStatuses = ['Pending', 'Judging', 'Compiling', 'Loading...']
  return pendingStatuses.includes(submission.value.status)
})

const editorOptions = {
  readOnly: true,
  automaticLayout: true,
  minimap: {enabled: false},
  scrollBeyondLastLine: false,
  fontSize: 14,
  fontFamily: "'Fira Code', 'Consolas', monospace",
  renderWhitespace: 'selection'
}

const getStatusClass = (status) => {
  if (!status) return ''
  const s = status.toLowerCase()
  if (s === 'accepted') return 'status-success'
  if (s === 'wrong answer' || s.includes('error')) return 'status-danger'
  if (['pending', 'judging', 'compiling'].includes(s)) return 'status-info'
  return 'status-warning'
}

const getScoreColor = (percentage) => {
  if (percentage === 100) return '#67C23A'
  if (percentage >= 60) return '#E6A23C'
  return '#F56C6C'
}

const formatTime = (isoString) => {
  if (!isoString) return ''
  return new Date(isoString).toLocaleString()
}

const copyCode = async () => {
  try {
    await navigator.clipboard.writeText(submission.value.code)
    ElMessage.success('Code copied to clipboard')
  } catch (err) {
    ElMessage.error('Failed to copy code')
  }
}

const fetchSubmission = async (silent = false) => {
  if (!silent) loading.value = true
  try {
    const data = await getSubmissionDetail(submissionId)
    submission.value = data

    if (isPending.value) {
      startPolling()
    } else {
      stopPolling()
      // 判题结束后获取查重信息
      fetchPlagiarismInfo()
    }
  } catch (error) {
    ElMessage.error('Failed to load submission details')
    stopPolling()
  } finally {
    if (!silent) loading.value = false
  }
}

const fetchPlagiarismInfo = async () => {
  try {
    const log = await getPlagiarismDetail(submissionId)
    if (log) {
      plagiarismLog.value = log
    }
  } catch (error) {
    // 404 is expected if no plagiarism found
    console.log('No plagiarism log found or access denied')
  }
}

const viewTargetSubmission = () => {
  if (!plagiarismLog.value) return
  router.push({ name: 'submission-detail', params: { id: plagiarismLog.value.target_submission_id } })
}

const compareCode = () => {
  if (!plagiarismLog.value) return
  router.push({
    name: 'code-compare',
    query: {
      id1: plagiarismLog.value.submission_id,
      id2: plagiarismLog.value.target_submission_id,
      similarity: plagiarismLog.value.similarity_score
    }
  })
}

const startPolling = () => {
  if (timer) return
  timer = setInterval(() => {
    fetchSubmission(true)
  }, 2000)
}

const stopPolling = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

onMounted(() => {
  fetchSubmission()
})

onUnmounted(() => {
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
