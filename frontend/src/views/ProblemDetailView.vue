<template>
  <div class="problem-detail-container" :class="{ 'scrollable-container': isKaggle }">
    <!-- Exam Header (if in exam) -->
    <div v-if="examId" class="exam-status-bar">
      <el-button :icon="ArrowLeft" @click="backToExam" size="small">返回考试题单</el-button>
      <span class="exam-info-text">正在进行考试模式</span>
    </div>

    <!-- Kaggle Layout (Top-Bottom) -->
    <div v-if="isKaggle" class="kaggle-layout">
      <el-card class="problem-card mb-4" shadow="never">
        <template #header>
          <div class="card-header">
            <h2 class="problem-title">{{ problem.id }}. {{ problem.title }}</h2>
            <div class="problem-meta">
              <el-tag size="small" effect="plain" class="meta-tag">Type: Kaggle</el-tag>
              <el-tag size="small" effect="plain" class="meta-tag">Time: {{ problem.time_limit }}ms</el-tag>
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
            <span class="header-title">Submit Prediction</span>
          </div>
        </template>
        <div class="upload-area">
          <el-upload
            class="upload-demo"
            drag
            action="#"
            :auto-upload="false"
            :limit="1"
            accept=".csv"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :file-list="fileList"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              Drop CSV file here or <em>click to upload</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                Only CSV files are allowed. Please ensure your file matches the submission format.
              </div>
            </template>
          </el-upload>
          <div class="upload-actions">
            <el-button type="primary" size="large" :loading="submitting" @click="handleSubmitKaggle" :disabled="!selectedFile">
              Submit CSV
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Standard Layout (Left-Right) -->
    <el-row v-else :gutter="20" class="full-height">
      <!-- Left Column: Problem Description -->
      <el-col :span="12" class="left-column">
        <el-card class="problem-card" shadow="never">
          <template #header>
            <div class="card-header">
              <h2 class="problem-title">{{ problem.id }}. {{ problem.title }}</h2>
              <div class="problem-meta">
                <el-tag size="small" effect="plain" class="meta-tag">Time: {{ problem.time_limit }}ms</el-tag>
                <el-tag size="small" effect="plain" class="meta-tag">Memory: {{ problem.memory_limit }}MB</el-tag>
                <el-tag size="small" effect="plain" class="meta-tag">Type: {{ problem.type }}</el-tag>
              </div>
            </div>
          </template>
          <div class="problem-content">
            <div class="markdown-body" v-html="renderedContent"></div>
          </div>
        </el-card>
      </el-col>

      <!-- Right Column: Code Editor -->
      <el-col :span="12" class="right-column">
        <el-card class="editor-card" shadow="never" :body-style="{ padding: '0px', height: '100%', display: 'flex', flexDirection: 'column' }">
          <template #header>
            <div class="editor-header">
              <div class="header-controls">
                <el-select v-model="language" placeholder="Language" size="small" style="width: 120px">
                  <el-option label="Python" value="python" />
                  <el-option label="C++" value="cpp" />
                  <el-option label="C" value="c" />
                  <el-option label="Java" value="java" />
                </el-select>
                <el-select
                  v-model="fontSize"
                  placeholder="Size"
                  size="small"
                  style="width: 80px; margin-left: 10px"
                  @change="handleFontSizeChange"
                >
                  <el-option label="12px" :value="12" />
                  <el-option label="14px" :value="14" />
                  <el-option label="16px" :value="16" />
                  <el-option label="18px" :value="18" />
                  <el-option label="20px" :value="20" />
                  <el-option label="24px" :value="24" />
                </el-select>
              </div>
              <el-button type="primary" size="small" :loading="submitting" @click="handleSubmit">
                Submit
              </el-button>
            </div>
          </template>
          <div class="editor-wrapper">
            <vue-monaco-editor
              v-model:value="code"
              :language="language"
              theme="vs-dark"
              :options="editorOptions"
              class="monaco-editor"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProblemDetail, submitSolution } from '@/api/problem'
import { ElMessage } from 'element-plus'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { UploadFilled, ArrowLeft } from '@element-plus/icons-vue'

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
  type: ''
})

const language = ref('python')
const code = ref('')
const submitting = ref(false)
const fontSize = ref(parseInt(localStorage.getItem('editorFontSize') || '14'))

// Kaggle specific refs
const fileList = ref([])
const selectedFile = ref(null)

const isKaggle = computed(() => {
  return problem.value.type && problem.value.type.toLowerCase() === 'kaggle'
})

const editorOptions = computed(() => ({
  automaticLayout: true,
  minimap: { enabled: false },
  fontSize: fontSize.value,
  scrollBeyondLastLine: false
}))

const handleFontSizeChange = (val) => {
  localStorage.setItem('editorFontSize', val)
}

const templates = {
  python: 'print("Hello World")',
  cpp: '#include <iostream>\nusing namespace std;\n\nint main() {\n    return 0;\n}',
  c: '#include <stdio.h>\n\nint main() {\n    printf("Hello, World!\\n");\n    return 0;\n}',
  java: 'public class Main {\n    public static void main(String[] args) {\n        \n    }\n}'
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
               hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
               '</code></pre>';
      } catch (__) {}
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
    // exam_id is now handled by backend automatically
    const res = await submitSolution({
      problem_id: parseInt(problemId),
      code: code.value,
      language: language.value
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

  // Basic CSV validation (check extension)
  if (!selectedFile.value.name.endsWith('.csv')) {
    ElMessage.error('Only CSV files are allowed')
    return
  }

  submitting.value = true
  try {
    const formData = new FormData()
    formData.append('problem_id', problemId)
    formData.append('file', selectedFile.value)
    // exam_id is now handled by backend automatically

    const res = await submitSolution(formData)
    ElMessage.success('File uploaded successfully!')
    router.push(`/submission/${res.submission_id}`)
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
  height: calc(100vh - 120px);
  overflow: hidden;
}

.scrollable-container {
  height: auto;
  min-height: calc(100vh - 120px);
  overflow-y: auto;
  padding-bottom: 40px;
}

.exam-status-bar {
  background-color: #fdf6ec;
  border-bottom: 1px solid #faecd8;
  padding: 8px 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 10px;
}

.exam-info-text {
  color: #e6a23c;
  font-weight: bold;
  font-size: 14px;
}

.full-height {
  height: 100%;
}

.left-column, .right-column {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.problem-card {
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* Kaggle Layout Styles */
.kaggle-layout {
  max-width: 1200px;
  margin: 0 auto;
}

.kaggle-layout .problem-card {
  height: auto;
  min-height: 300px;
  overflow: visible;
}

.upload-card {
  margin-top: 20px;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

.upload-demo {
  width: 100%;
  max-width: 600px;
}

.upload-actions {
  margin-top: 20px;
}

.mb-4 {
  margin-bottom: 20px;
}

.editor-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.problem-title {
  margin: 0;
  font-size: 1.5rem;
}

.problem-meta {
  display: flex;
  gap: 10px;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-controls {
  display: flex;
  align-items: center;
}

.editor-wrapper {
  flex: 1;
  min-height: 0;
}

.monaco-editor {
  height: 100%;
  width: 100%;
}

/* Styles for rendered markdown content */
.markdown-body {
  line-height: 1.6;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
  border-bottom: 1px solid var(--el-border-color-lighter);
  padding-bottom: 0.3em;
}

.markdown-body :deep(h3) {
  font-size: 1.25em;
}

.markdown-body :deep(pre) {
  background-color: #f5f7fa;
  padding: 16px;
  border-radius: 6px;
  font-family: 'Courier New', Courier, monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.markdown-body :deep(code) {
  font-family: 'Courier New', Courier, monospace;
  background-color: rgba(27,31,35,.05);
  padding: .2em .4em;
  margin: 0;
  font-size: 85%;
  border-radius: 3px;
}

.markdown-body :deep(pre) > code {
  padding: 0;
  margin: 0;
  font-size: 100%;
  background-color: transparent;
  border: 0;
}

.markdown-body :deep(p) {
  margin-bottom: 16px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 2em;
  margin-bottom: 16px;
}
</style>
