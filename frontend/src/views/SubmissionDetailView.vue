<template>
  <div class="submission-detail-container">
    <!-- Status Overview -->
    <el-card class="status-card mb-4" shadow="hover" v-loading="loading">
      <div class="status-wrapper">
        <div class="status-main">
          <div class="status-icon">
            <el-icon v-if="submission.status === 'Accepted'" color="#67C23A" :size="50"><CircleCheckFilled /></el-icon>
            <el-icon v-else-if="submission.status === 'Wrong Answer'" color="#F56C6C" :size="50"><CircleCloseFilled /></el-icon>
            <el-icon v-else color="#E6A23C" :size="50"><QuestionFilled /></el-icon>
          </div>
          <div class="status-text">
            <h1 :class="getStatusClass(submission.status)">{{ submission.status }}</h1>
            <div class="meta-info">
              <el-tag size="small" effect="plain" class="mr-2">{{ submission.language }}</el-tag>
              <span class="time-text"><el-icon><Clock /></el-icon> {{ formatTime(submission.created_at) }}</span>
            </div>
          </div>
        </div>

        <div class="score-display">
          <el-progress
            type="dashboard"
            :percentage="submission.score"
            :color="getScoreColor"
            :width="80"
          >
            <template #default="{ percentage }">
              <span class="score-value">{{ percentage }}</span>
            </template>
          </el-progress>
        </div>
      </div>
    </el-card>

    <!-- Judge Log / Test Cases -->
    <el-card class="log-card mb-4" shadow="hover" v-if="submission.log">
      <template #header>
        <div class="card-header">
          <span class="header-title"><el-icon><List /></el-icon> Judge Feedback</span>
        </div>
      </template>
      <div class="log-content">
        <!-- If log contains specific keywords, we could try to parse it, but for now display as pre -->
        <pre>{{ submission.log }}</pre>
      </div>
    </el-card>

    <!-- Source Code -->
    <el-card class="code-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="header-title"><el-icon><Document /></el-icon> Source Code</span>
          <el-button size="small" @click="copyCode" :icon="CopyDocument">Copy</el-button>
        </div>
      </template>
      <div class="editor-wrapper">
        <vue-monaco-editor
          v-if="submission.code"
          v-model:value="submission.code"
          :language="submission.language || 'python'"
          theme="vs-light"
          :options="editorOptions"
          class="monaco-editor"
        />
        <el-empty v-else description="No code available" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getSubmissionDetail } from '@/api/problem'
import { ElMessage } from 'element-plus'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import {
  CircleCheckFilled,
  CircleCloseFilled,
  QuestionFilled,
  Clock,
  List,
  Document,
  CopyDocument
} from '@element-plus/icons-vue'

const route = useRoute()
const submissionId = route.params.id
const loading = ref(false)

const submission = ref({
  id: submissionId,
  status: 'Loading...',
  score: 0,
  log: '',
  code: '',
  language: 'python',
  created_at: ''
})

const editorOptions = {
  readOnly: true,
  automaticLayout: true,
  minimap: { enabled: false },
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

const fetchSubmission = async () => {
  loading.value = true
  try {
    const data = await getSubmissionDetail(submissionId)
    submission.value = data
  } catch (error) {
    ElMessage.error('Failed to load submission details')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSubmission()
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

.status-success { color: var(--el-color-success); }
.status-danger { color: var(--el-color-danger); }
.status-warning { color: var(--el-color-warning); }

.meta-info {
  display: flex;
  align-items: center;
  color: var(--el-text-color-secondary);
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
</style>
