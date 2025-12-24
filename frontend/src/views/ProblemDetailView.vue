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
        <div class="column-content">
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
          <el-divider/>
          <div class="problem-content">
            <div class="markdown-body" v-html="renderedContent"></div>
          </div>
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
  </div>
</template>

<script setup>
import {computed, onMounted, ref, watch} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {getProblemDetail, submitSolution} from '@/api/problem'
import {ElMessage} from 'element-plus'
import {VueMonacoEditor} from '@guolao/vue-monaco-editor'
import {ArrowLeft, Monitor, Setting, Timer, UploadFilled} from '@element-plus/icons-vue'

// Markdown and Highlighting
import MarkdownIt from 'markdown-it'
import mk from 'markdown-it-katex'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import 'katex/dist/katex.min.css'

const route = useRoute()
const router = useRouter()
const problemId = route.params.id
const examId = computed(() => route.query.exam_id)

const problem = ref({
  id: '',
  title: 'Loading...',
  content: '',
  time_limit: 0,
  memory_limit: 0,
  type: '',
  language: ''
})

const language = ref('python')
const code = ref('')
const submitting = ref(false)

// Editor Settings
const fontSize = ref(parseInt(localStorage.getItem('editorFontSize') || '16'))
const fontFamily = ref(localStorage.getItem('editorFontFamily') || "'Fira Code', 'Courier New', monospace")
const fontLigatures = ref(localStorage.getItem('editorFontLigatures') !== 'false')

const saveSettings = () => {
  localStorage.setItem('editorFontSize', fontSize.value)
  localStorage.setItem('editorFontFamily', fontFamily.value)
  localStorage.setItem('editorFontLigatures', fontLigatures.value)
}

// Kaggle specific refs
const fileList = ref([])
const selectedFile = ref(null)

const isKaggle = computed(() => {
  return problem.value.type && problem.value.type.toLowerCase() === 'kaggle'
})

const getTypeTag = (type) => {
  const map = {
    'acm': 'primary',
    'kaggle': 'success',
    'oop': 'warning'
  }
  return map[type?.toLowerCase()] || 'info'
}

const getTypeDescription = (type) => {
  const map = {
    'acm': '经典的算法竞赛模式，标准 I/O，严格文本比对。',
    'kaggle': '数据科学竞赛模式，提交 CSV 预测结果，基于 Metric 评分。',
    'oop': '面向对象编程模式，实现特定接口/类，运行单元测试。'
  }
  return map[type?.toLowerCase()] || '未知题目类型'
}

const editorOptions = computed(() => ({
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

const templates = {
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

// Configure MarkdownIt
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return '<pre class="hljs"><code>' +
            hljs.highlight(str, {language: lang, ignoreIllegals: true}).value +
            '</code></pre>';
      } catch (__) {
      }
    }

    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>';
  }
})

md.use(mk)

const renderedContent = computed(() => {
  return problem.value.content ? md.render(problem.value.content) : ''
})

const fetchProblem = async () => {
  try {
    const data = await getProblemDetail(problemId)
    if (data) {
      problem.value = data
      // Set default language from allowed list
      if (availableLanguageOptions.value.length > 0) {
        language.value = availableLanguageOptions.value[0].value
      }
    }
  } catch (error) {
    ElMessage.error('Failed to load problem')
  }
}

const backToExam = () => {
  router.push(`/exam/${examId.value}`)
}

// Standard Submission
const handleSubmit = async () => {
  if (!code.value.trim()) {
    ElMessage.warning('Code cannot be empty')
    return
  }

  submitting.value = true
  try {
    const res = await submitSolution({
      problem_id: parseInt(problemId),
      code: code.value,
      language: language.value,
      exam_id: examId.value || -1
    })
    ElMessage.success('Submission received!')
    router.push(`/submission/${res.submission_id}`)
  } catch (error) {
    ElMessage.error('Submission failed')
  } finally {
    submitting.value = false
  }
}

// Kaggle File Handling
const handleFileChange = (uploadFile, uploadFiles) => {
  if (uploadFiles.length > 1) {
    uploadFiles.splice(0, 1) // Keep only the latest
  }
  selectedFile.value = uploadFile.raw
  fileList.value = uploadFiles
}

const handleFileRemove = () => {
  selectedFile.value = null
  fileList.value = []
}

// Kaggle Submission
const handleSubmitKaggle = async () => {
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
    formData.append('problem_id', problemId)
    formData.append('file', selectedFile.value)
    formData.append('code', 'Kaggle Submission')
    formData.append('language', 'csv')
    formData.append('exam_id', examId.value || -1)

    const res = await submitSolution(formData)
    ElMessage.success('File uploaded successfully!')
    await router.push(`/submission/${res.submission_id}`)
  } catch (error) {
    ElMessage.error('Upload failed')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchProblem()
})
</script>

<style scoped>
.problem-detail-container {
  height: calc(100vh - 60px);
  background-color: #fff;
  overflow: hidden;
}

.scrollable-container {
  height: auto;
  min-height: calc(100vh - 60px);
  overflow-y: auto;
  padding: 20px;
  background-color: #f5f7fa;
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
  height: 100%;
}

.split-layout {
  border-top: 1px solid #e8e8e8;
}

.left-column {
  height: 100%;
  border-right: 1px solid #e8e8e8;
  overflow-y: auto;
  background-color: #fff;
}

.column-content {
  padding: 32px;
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

.right-column {
  height: 100%;
  background-color: #1e1e1e;
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

.editor-wrapper {
  flex: 1;
  min-height: 0;
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
</style>
