<template>
  <div :class="{ 'scrollable-container': isKaggle }" class="problem-detail-container">
    <!-- Exam Header (if in exam) -->
    <div v-if="examId" class="exam-status-bar">
      <el-button :icon="ArrowLeft" round size="small" @click="backToExam">返回考试题单</el-button>
      <div class="exam-badge">
        <el-icon>
          <Timer/>
        </el-icon>
        <span>正在进行考试模式</span>
      </div>
    </div>

    <!-- Kaggle Layout (Top-Bottom) -->
    <div v-if="isKaggle" class="kaggle-layout">
      <el-card class="problem-card mb-4" shadow="never">
        <template #header>
          <div class="card-header">
            <div class="title-row">
              <h2 class="problem-title">#{{ problem.id }} {{ problem.title }}</h2>
              <div class="problem-meta">
                <el-tooltip content="数据科学竞赛模式，提交 CSV 预测结果，基于 Metric 评分。" placement="top">
                  <el-tag effect="light" size="small" type="success">Kaggle</el-tag>
                </el-tooltip>
                <el-tooltip content="程序运行的最长时间限制，超过此时间将被判定为 TLE (Time Limit Exceeded)"
                            placement="top">
                  <el-tag effect="plain" size="small" type="info">
                    <el-icon>
                      <Timer/>
                    </el-icon>
                    {{ problem.time_limit }}ms
                  </el-tag>
                </el-tooltip>
              </div>
            </div>
          </div>
        </template>
        <div class="problem-content">
          <div class="markdown-body" v-html="renderedContent"></div>
        </div>
      </el-card>

      <el-card class="upload-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span class="header-title">提交预测结果 (CSV)</span>
          </div>
        </template>
        <div class="upload-area">
          <el-upload
              :auto-upload="false"
              :file-list="fileList"
              :limit="1"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              accept=".csv"
              action="#"
              class="upload-demo"
              drag
          >
            <el-icon class="el-icon--upload">
              <upload-filled/>
            </el-icon>
            <div class="el-upload__text">
              将 CSV 文件拖到此处，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                仅支持 CSV 文件。请确保您的文件格式符合题目要求。
              </div>
            </template>
          </el-upload>
          <div class="upload-actions">
            <el-button :disabled="!selectedFile" :loading="submitting" round size="large" type="primary"
                       @click="handleSubmitKaggle">
              提交 CSV 结果
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Standard Layout (Left-Right) -->
    <el-row v-else :gutter="0" class="full-height split-layout">
      <!-- Left Column: Problem Description -->
      <el-col :span="12" class="left-column">
        <div class="problem-panel-header">
          <div class="problem-header">
            <h2 class="problem-title">#{{ problem.id }} {{ problem.title }}</h2>
            <div class="problem-meta">
              <el-tooltip content="程序运行的最长时间限制，超过此时间将被判定为 TLE (Time Limit Exceeded)"
                          placement="top">
                <el-tag effect="plain" size="small" type="info">
                  <el-icon>
                    <Timer/>
                  </el-icon>
                  {{ problem.time_limit }}ms
                </el-tag>
              </el-tooltip>
              <el-tooltip content="程序运行可使用的最大内存限制，超过此限制将被判定为 MLE (Memory Limit Exceeded)"
                          placement="top">
                <el-tag effect="plain" size="small" type="info">
                  <el-icon>
                    <Monitor/>
                  </el-icon>
                  {{ problem.memory_limit }}MB
                </el-tag>
              </el-tooltip>
              <el-tooltip :content="getTypeDescription(problem.type)" placement="top">
                <el-tag :type="getTypeTag(problem.type)" effect="light" size="small">{{
                    problem.type?.toUpperCase()
                  }}
                </el-tag>
              </el-tooltip>
            </div>
          </div>
          <div class="problem-tag-row">
            <TagPanel :problem-id="Number(problem.id)" />
          </div>
          <el-divider/>
        </div>
        <div class="problem-content problem-content-scroll">
          <div class="markdown-body" v-html="renderedContent"></div>
        </div>
        <div class="solution-section">
          <SolutionPanel :problem-id="Number(problem.id)" />
        </div>
      </el-col>

      <!-- Right Column: Code Editor -->
      <el-col :span="12" class="right-column">
        <div class="editor-container">
          <div class="editor-toolbar">
            <div class="toolbar-left">
              <el-select v-model="language" class="lang-select" placeholder="Language" size="default">
                <el-option
                    v-for="opt in availableLanguageOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                />
              </el-select>

              <!-- Settings Popover -->
              <el-popover :width="300" placement="bottom" popper-class="editor-settings-popover" trigger="click">
                <template #reference>
                  <el-button :icon="Setting" circle class="settings-btn" size="default"/>
                </template>
                <div class="settings-panel">
                  <h4 class="settings-title">编辑器设置</h4>
                  <el-form label-position="left" label-width="80px" size="small">
                    <el-form-item label="字体大小">
                      <el-select v-model="fontSize" @change="saveSettings">
                        <el-option v-for="size in [12, 14, 16, 18, 20, 24]" :key="size" :label="size + 'px'"
                                   :value="size"/>
                      </el-select>
                    </el-form-item>
                    <el-form-item label="字体家族">
                      <el-select v-model="fontFamily" @change="saveSettings">
                        <el-option label="Fira Code" value="'Fira Code', monospace"/>
                        <el-option label="JetBrains Mono" value="'JetBrains Mono', monospace"/>
                        <el-option label="Source Code Pro" value="'Source Code Pro', monospace"/>
                        <el-option label="Courier New" value="'Courier New', monospace"/>
                      </el-select>
                    </el-form-item>
                    <el-form-item label="启用连字">
                      <el-switch v-model="fontLigatures" @change="saveSettings"/>
                    </el-form-item>
                  </el-form>
                </div>
              </el-popover>
            </div>
            <div class="toolbar-right">
              <el-button
                  v-if="isAcm"
                  :icon="MagicStick"
                  :loading="debugging"
                  class="debug-btn"
                  round
                  size="default"
                  type="warning"
                  @click="handleDebug"
              >
                调试
              </el-button>
              <el-button :loading="submitting" class="submit-btn" round size="default" type="primary"
                         @click="handleSubmit">
                提交代码
              </el-button>
            </div>
          </div>
          <div class="editor-wrapper">
            <vue-monaco-editor
                v-model:value="code"
                :language="language"
                :options="editorOptions"
                class="monaco-editor"
                theme="vs-dark"
            />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Debug Result Drawer -->
    <el-drawer
        v-model="debugDrawerVisible"
        :close-on-press-escape="true"
        direction="rtl"
        size="60%"
        title="ACM 调试运行结果（仅第一个测试点，不计入成绩）"
    >
      <DebugResultPanel
          v-if="debugDrawerVisible && debugRunId !== null"
          :debug-run-id="debugRunId"
          @close="debugDrawerVisible = false"
      />
    </el-drawer>

    <!-- Realtime Judge Result Toast -->
    <transition name="el-fade-in">
      <div v-if="realtimeStatus === 'received' && realtimeResult" class="realtime-toast">
        <div class="toast-content">
          <el-icon class="toast-icon"><CircleCheckFilled/></el-icon>
          <div class="toast-text">
            <strong>判题完成：{{ realtimeResult.status }}</strong>
            <span>得分 {{ Number(realtimeResult.score ?? 0).toFixed(1) }}</span>
          </div>
          <el-button size="small" type="primary" @click="goToSubmissionDetail">查看详情</el-button>
          <el-button size="small" @click="realtimeStatus = 'closed'">关闭</el-button>
        </div>
      </div>
      <div v-else-if="realtimeStatus === 'pending'" class="realtime-toast pending">
        <div class="toast-content">
          <el-icon class="toast-icon is-loading"><Loading/></el-icon>
          <div class="toast-text">
            <strong>判题中...</strong>
            <span>实时等待结果</span>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import type { editor } from 'monaco-editor'
import type { ProblemDetailResponse } from '@/types/problem'
import type { SubmissionWS } from '@/utils/websocket'
import type { SubmissionMessage } from '@/schemas/submission'
import type { UploadFile, UploadFiles, TagProps } from 'element-plus'
import { parseRouteId } from '@/utils/route'
import {computed, inject, onBeforeUnmount, ref, watch} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {getProblemDetail, submitSolution} from '@/api/problem'
import {debugSolution} from '@/api/debug'
import {ElMessage} from 'element-plus'
import {VueMonacoEditor} from '@guolao/vue-monaco-editor'
import {ArrowLeft, CircleCheckFilled, Loading, MagicStick, Monitor, Setting, Timer, UploadFilled} from '@element-plus/icons-vue'
import {createSubmissionWS} from '@/utils/websocket'
import {submissionMessageSchema} from '@/schemas/submission'
import DebugResultPanel from '@/components/DebugResultPanel.vue'
import SolutionPanel from '@/components/SolutionPanel.vue'
import TagPanel from '@/components/TagPanel.vue'

// 题面 Markdown 渲染（含 LaTeX / 代码高亮），统一从 utils/markdown 入口复用，避免各处独立初始化导致配置漂移
import {renderMarkdown} from '@/utils/markdown'

const route = useRoute()
const router = useRouter()
const setAnswerWorkspaceActive = inject<((active: boolean) => void) | null>('setAnswerWorkspaceActive', null)
const problemId = computed(() => parseRouteId(route.params.id))
let pageVersion = 0
let disposed = false
const problemLoaded = ref(false)
const isCurrentPage = (version: number) => !disposed && version === pageVersion
const examId = computed(() => parseRouteId(route.query.exam_id))

const emptyProblem = (): Omit<ProblemDetailResponse, 'id'> & {id: number | null} => ({
  id: null,
  title: 'Loading...',
  content: '',
  time_limit: 0,
  memory_limit: 0,
  type: '',
  language: '',
  template_code: null
})
const problem = ref(emptyProblem())

const language = ref('python')
const code = ref('')
const submitting = ref(false)
const debugging = ref(false)
const debugDrawerVisible = ref(false)
const debugRunId = ref<number | null>(null)

// WebSocket: 提交后等待实时判题结果
const realtimeResult = ref<SubmissionMessage | null>(null)
const realtimeStatus = ref('idle') // 'idle' | 'pending' | 'received' | 'closed'
let activeWS: SubmissionWS | null = null

function clearRealtimeWS() {
  if (activeWS) {
    activeWS.close()
    activeWS = null
  }
}

function startRealtimeWait(submissionId: number) {
  const version = pageVersion
  clearRealtimeWS()
  realtimeResult.value = null
  realtimeStatus.value = 'pending'
  const token = localStorage.getItem('token') || ''
  activeWS = createSubmissionWS(submissionId, token, {
    onMessage: (data) => {
      if (!isCurrentPage(version)) return
      const parsed = submissionMessageSchema.safeParse(data)
      if (!parsed.success) {
        console.warn('判题推送格式无效', parsed.error.issues)
        return
      }
      realtimeResult.value = parsed.data
      realtimeStatus.value = 'received'
      ElMessage.success(`判题完成：${parsed.data.status} (${(parsed.data.score ?? 0).toFixed(1)} 分)`)
    },
    onError: () => {
      if (!isCurrentPage(version)) return
      if (!realtimeResult.value) realtimeStatus.value = 'closed'
    },
    onClose: () => {
      if (!isCurrentPage(version)) return
      // 服务端发送结果后会正常关闭连接，不能因此隐藏已收到的成绩。
      if (!realtimeResult.value) realtimeStatus.value = 'closed'
    },
    onReconnect: () => {
      if (!isCurrentPage(version)) return
      if (!realtimeResult.value) realtimeStatus.value = 'pending'
    },
  })
  activeWS.connect()
}

// Editor Settings
const fontSize = ref(parseInt(localStorage.getItem('editorFontSize') || '16'))
const fontFamily = ref(localStorage.getItem('editorFontFamily') || "'Fira Code', 'Courier New', monospace")
const fontLigatures = ref(localStorage.getItem('editorFontLigatures') !== 'false')

const saveSettings = () => {
  localStorage.setItem('editorFontSize', String(fontSize.value))
  localStorage.setItem('editorFontFamily', fontFamily.value)
  localStorage.setItem('editorFontLigatures', String(fontLigatures.value))
}

// Kaggle specific refs
const fileList = ref<UploadFiles>([])
const selectedFile = ref<File | null>(null)

const isKaggle = computed(() => {
  return problem.value.type && problem.value.type.toLowerCase() === 'kaggle'
})

const isAcm = computed(() => {
  return problem.value.type && problem.value.type.toLowerCase() === 'acm'
})

watch(isKaggle, (isKaggleProblem) => {
  setAnswerWorkspaceActive?.(!isKaggleProblem)
}, {immediate: true})

const getTypeTag = (type: string) => {
  const map: Record<string, TagProps['type']> = {
    'acm': 'primary',
    'kaggle': 'success',
    'oop': 'warning'
  }
  return map[type?.toLowerCase()] || 'info'
}

const getTypeDescription = (type: string) => {
  const map: Record<string, string> = {
    'acm': '经典的算法竞赛模式，标准 I/O，严格文本比对。',
    'kaggle': '数据科学竞赛模式，提交 CSV 预测结果，基于 Metric 评分。',
    'oop': '面向对象编程模式，实现特定接口/类，运行单元测试。'
  }
  return map[type?.toLowerCase()] || '未知题目类型'
}

const editorOptions = computed<editor.IStandaloneEditorConstructionOptions>(() => ({
  automaticLayout: true,
  minimap: {enabled: false},
  fontSize: fontSize.value,
  fontFamily: fontFamily.value,
  fontLigatures: fontLigatures.value,
  scrollBeyondLastLine: false,
  lineNumbers: 'on',
  roundedSelection: false,
  scrollBeyondLastColumn: 0,
  cursorStyle: 'line',
  cursorBlinking: 'smooth',
  formatOnPaste: true,
  formatOnType: true,
}))

const allLanguageOptions = [
  {label: 'Python', value: 'python'},
  {label: 'C++', value: 'cpp'},
  {label: 'C', value: 'c'},
  {label: 'Java', value: 'java'}
]

const availableLanguageOptions = computed(() => {
  if (!problem.value.language) return allLanguageOptions
  const allowed = problem.value.language.split(',').map(s => s.trim().toLowerCase())
  return allLanguageOptions.filter(opt => allowed.includes(opt.value))
})

const templates: Record<string, string> = {
  python: 'import sys\nimport os\n',
  cpp: '#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your code here\n    return 0;\n}',
  c: '#include <stdio.h>\n\nint main() {\n    // Write your code here\n    return 0;\n}',
  java: 'import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        // Write your code here\n    }\n}'
}

// Set initial code
code.value = templates[language.value]

// Watch for language changes to update the editor's code template
watch(language, (newLang) => {
  code.value = templates[newLang] || ''
})

// Configure MarkdownIt — 题面渲染复用 utils/markdown 的统一实例，确保 LaTeX / 换行 / XSS 防护与编辑器预览一致

const renderedContent = computed(() => renderMarkdown(problem.value.content))

const fetchProblem = async (version: number) => {
  try {
    if (problemId.value === null || (route.query.exam_id != null && examId.value === null)) throw new Error('题目或考试 ID 无效')
    const data = await getProblemDetail(problemId.value)
    if (!isCurrentPage(version)) return
    if (data) {
      problem.value = data
      // Set default language from allowed list
      if (availableLanguageOptions.value.length > 0) {
        language.value = availableLanguageOptions.value[0].value
      }
      code.value = templates[language.value] || ''
      problemLoaded.value = true
    }
  } catch (error) {
    if (isCurrentPage(version)) ElMessage.error('Failed to load problem')
  }
}

const backToExam = () => {
  router.push(`/exam/${examId.value}`)
}

// Standard Submission
const handleSubmit = async () => {
  if (!problemLoaded.value || submitting.value || problemId.value === null) return
  const version = pageVersion
  if (!code.value.trim()) {
    ElMessage.warning('Code cannot be empty')
    return
  }

  submitting.value = true
  try {
    const res = await submitSolution({
      problem_id: problemId.value,
      code: code.value,
      language: language.value,
      exam_id: examId.value || -1
    })
    if (!isCurrentPage(version)) return
    ElMessage.success('Submission received!')
    startRealtimeWait(res.submission_id)
  } catch (error) {
    if (isCurrentPage(version)) ElMessage.error('Submission failed')
  } finally {
    if (isCurrentPage(version)) submitting.value = false
  }
}

// 收到实时结果后，用户点击跳转查看详情
const goToSubmissionDetail = () => {
  if (!realtimeResult.value) return
  clearRealtimeWS()
  router.push(`/submission/${realtimeResult.value.submission_id || ''}`)
}

// Debug Run（仅 ACM 题目，不计入成绩，仅跑第一个测试点）
const handleDebug = async () => {
  if (!problemLoaded.value || debugging.value || problemId.value === null) return
  const version = pageVersion
  if (!isAcm.value) {
    ElMessage.warning('仅 ACM 类型题目支持调试运行')
    return
  }
  if (!code.value.trim()) {
    ElMessage.warning('Code cannot be empty')
    return
  }

  debugging.value = true
  try {
    const res = await debugSolution({
      problem_id: problemId.value,
      code: code.value,
      language: language.value,
      exam_id: examId.value || -1
    })
    if (!isCurrentPage(version)) return
    debugRunId.value = res.debug_run_id
    debugDrawerVisible.value = true
  } catch (error) {
    if (isCurrentPage(version)) ElMessage.error('调试运行失败')
  } finally {
    if (isCurrentPage(version)) debugging.value = false
  }
}

// Kaggle File Handling
const handleFileChange = (uploadFile: UploadFile, uploadFiles: UploadFiles) => {
  if (uploadFiles.length > 1) {
    uploadFiles.splice(0, 1) // Keep only the latest
  }
  selectedFile.value = uploadFile.raw || null
  fileList.value = uploadFiles
}

const handleFileRemove = () => {
  selectedFile.value = null
  fileList.value = []
}

// Kaggle Submission
const handleSubmitKaggle = async () => {
  if (!problemLoaded.value || submitting.value || problemId.value === null) return
  const version = pageVersion
  if (!selectedFile.value) {
    ElMessage.warning('Please select a CSV file')
    return
  }

  if (!selectedFile.value.name.endsWith('.csv')) {
    ElMessage.error('Only CSV files are allowed')
    return
  }

  submitting.value = true
  try {
    const formData = new FormData()
    formData.append('problem_id', String(problemId.value))
    formData.append('file', selectedFile.value)
    formData.append('code', 'Kaggle Submission')
    formData.append('language', 'csv')
    formData.append('exam_id', String(examId.value || -1))

    const res = await submitSolution(formData)
    if (!isCurrentPage(version)) return
    ElMessage.success('File uploaded successfully!')
    startRealtimeWait(res.submission_id)
  } catch (error) {
    if (isCurrentPage(version)) ElMessage.error('Upload failed')
  } finally {
    if (isCurrentPage(version)) submitting.value = false
  }
}

// 路由复用时清除旧题目状态，并使未完成的请求和订阅回调失效。
watch(() => [problemId.value, examId.value], () => {
  const version = ++pageVersion
  clearRealtimeWS()
  problemLoaded.value = false
  problem.value = emptyProblem()
  code.value = ''
  selectedFile.value = null
  fileList.value = []
  submitting.value = false
  debugging.value = false
  debugRunId.value = null
  debugDrawerVisible.value = false
  realtimeResult.value = null
  realtimeStatus.value = 'idle'
  fetchProblem(version)
}, {immediate: true})

onBeforeUnmount(() => {
  disposed = true
  pageVersion += 1
  setAnswerWorkspaceActive?.(false)
  clearRealtimeWS()
})
</script>

<style scoped>
.problem-detail-container {
  height: 100%;
  background-color: #fff;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.scrollable-container {
  height: auto;
  min-height: calc(100vh - 60px);
  overflow-y: auto;
  padding: 20px;
  background-color: #f5f7fa;
  display: block;
}

.exam-status-bar {
  background-color: #fffbe6;
  border-bottom: 1px solid #ffe58f;
  padding: 10px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.exam-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #faad14;
  font-weight: 600;
}

.full-height {
  flex: 1;
  min-height: 0;
}

.split-layout {
  border-top: 1px solid #e8e8e8;
  overflow: hidden;
}

.left-column {
  height: 100%;
  border-right: 1px solid #e8e8e8;
  background-color: #fff;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.problem-panel-header {
  flex-shrink: 0;
  padding: 32px 32px 0;
}

.problem-content-scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
  padding: 0 32px 32px;
}

.problem-header {
  margin-bottom: 20px;
}

.problem-title {
  font-size: 1.8rem;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 16px;
}

.problem-meta {
  display: flex;
  gap: 12px;
  align-items: center;
}

.problem-meta .el-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: help;
}

.problem-tag-row {
  margin: 8px 0;
}

.solution-section {
  margin-top: 16px;
  padding-bottom: 24px;
}

.right-column {
  height: 100%;
  background-color: #1e1e1e;
  min-height: 0;
  overflow: hidden;
}

.editor-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.editor-toolbar {
  height: 50px;
  background-color: #252526;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #333;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.lang-select :deep(.el-input__wrapper) {
  background-color: #3c3c3c;
  box-shadow: none !important;
  border: none;
}

.lang-select :deep(.el-input__inner) {
  color: #ccc;
}

.lang-select {
  width: 120px;
}

.settings-btn {
  background-color: transparent;
  border: none;
  color: #888;
  transition: color 0.3s;
}

.settings-btn:hover {
  color: #fff;
  background-color: #3c3c3c;
}

.submit-btn {
  padding: 8px 24px;
  font-weight: 600;
}

.debug-btn {
  margin-right: 8px;
  font-weight: 600;
}

.editor-wrapper {
  flex: 1;
  min-height: 0;
  overscroll-behavior: contain;
}

.monaco-editor {
  height: 100%;
}

/* Settings Panel */
.settings-panel {
  padding: 10px;
}

.settings-title {
  margin: 0 0 16px;
  font-size: 1rem;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}

/* Kaggle Layout Styles */
.kaggle-layout {
  max-width: 1000px;
  margin: 0 auto;
}

.kaggle-layout .problem-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.upload-area {
  padding: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.upload-demo {
  width: 100%;
}

.upload-actions {
  margin-top: 32px;
}

/* Markdown Styles */
.markdown-body {
  font-size: 1.05rem;
  line-height: 1.7;
  color: #333;
}

.markdown-body :deep(h2) {
  font-size: 1.5rem;
  margin-top: 32px;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}

.markdown-body :deep(pre) {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #eaecf0;
}

.markdown-body :deep(code) {
  font-family: 'Fira Code', monospace;
  background-color: #f0f2f5;
  padding: 2px 6px;
  border-radius: 4px;
  color: #e01979;
}

.markdown-body :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: inherit;
}

@media (max-width: 768px) {
  .split-layout {
    flex-wrap: nowrap;
    flex-direction: column;
  }

  .left-column,
  .right-column {
    flex: 1 1 50%;
    width: 100%;
    max-width: 100%;
    height: 50%;
  }

  .left-column {
    border-right: 0;
    border-bottom: 1px solid #e8e8e8;
  }

  .problem-panel-header {
    padding: 16px 16px 0;
  }

  .problem-content-scroll {
    padding: 0 16px 16px;
  }

  .problem-title {
    font-size: 1.35rem;
    margin-bottom: 10px;
  }

  .problem-meta {
    flex-wrap: wrap;
    gap: 8px;
  }

  .editor-toolbar {
    padding: 0 12px;
  }
}

.realtime-toast {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 2000;
  background: #ffffff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  padding: 14px 18px;
  min-width: 320px;
}

.realtime-toast.pending {
  background: #f0f9ff;
  border-color: #91caff;
}

.toast-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toast-icon {
  font-size: 24px;
  color: #67c23a;
}

.toast-icon.is-loading {
  color: #409eff;
  animation: spin 1s linear infinite;
}

.toast-text {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.toast-text strong {
  color: #1a1a1a;
}

.toast-text span {
  color: #888;
  font-size: 12px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
