<template>
  <div class="exam-monitor-container">
    <!-- L1: 监控大屏主界面 -->
    <el-page-header class="mb-4" @back="$router.back()">
      <template #content>
        <span class="text-large font-600 mr-3"> 考试监控: {{ examTitle }} </span>
      </template>
      <template #extra>
        <div class="flex items-center">
          <el-button :icon="Refresh" :loading="loading" circle @click="fetchMonitorData"/>
          <el-tag :type="autoRefresh ? 'success' : 'info'" class="ml-2">
            {{ autoRefresh ? '自动刷新中' : '自动刷新关闭' }}
          </el-tag>
          <el-switch v-model="autoRefresh" class="ml-2"/>
        </div>
      </template>
    </el-page-header>

    <el-row :gutter="20" class="mb-4">
      <el-col :span="6">
        <el-card class="stat-card" shadow="never">
          <el-statistic :value="participants?.length || 0" title="已参加人数"/>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" shadow="never">
          <el-statistic :value="totalSubmissions" title="总提交数"/>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" shadow="never">
          <el-statistic :value="fullScoreCount" title="满分人数"/>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="participants || []" border stripe style="width: 100%">
        <el-table-column fixed label="考生" prop="username" width="150"/>

        <el-table-column
            v-for="(problem, index) in problems"
            :key="problem.problem_id"
            :label="getProblemLabel(problem, index)"
            align="center"
            min-width="120"
        >
          <template #default="scope">
            <div v-if="getSubmission(scope.row.user_id, problem.problem_id)" class="score-cell">
              <el-tag
                  :type="getScoreTagType(getSubmission(scope.row.user_id, problem.problem_id).score)"
                  class="score-tag"
                  @click="openLevel2(scope.row.user_id, problem.problem_id)"
              >
                {{ getSubmission(scope.row.user_id, problem.problem_id).score }}
              </el-tag>
            </div>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>

        <el-table-column align="center" fixed="right" label="总分" prop="total_score" sortable width="100">
          <template #default="scope">
            <span class="font-bold text-primary">{{ scope.row.total_score }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- L2: 二级界面 - 详细得分侧边栏 -->
    <el-drawer
        v-model="drawerVisible"
        destroy-on-close
        size="450px"
        title="提交详细得分"
    >
      <div v-if="detailLoading" v-loading="true" style="height: 200px"></div>
      <div v-else-if="currentSubmission">
        <div class="detail-section">
          <h4>基本信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusType(currentSubmission.status)">{{ currentSubmission.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="最终得分">
              <span :class="getScoreClass(currentSubmission.score)" class="score-large">{{
                  currentSubmission.score
                }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="编程语言">{{ currentSubmission.language }}</el-descriptions-item>
            <el-descriptions-item label="提交时间">{{ formatTime(currentSubmission.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="detail-section mt-6">
          <h4>得分分析</h4>
          <el-alert
              v-if="currentSubmission.status === 'Accepted'"
              :closable="false"
              show-icon
              title="所有测试点已通过"
              type="success"
          />
          <el-alert
              v-else
              :closable="false"
              :title="`未完全通过: ${currentSubmission.status}`"
              show-icon
              type="error"
          />
          <!-- 这里预留给未来对接具体的测试点列表 -->
          <div class="mt-4 text-center">
            <el-button :icon="View" type="primary" @click="openLevel3">查看解题代码</el-button>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- L3: 三级界面 - 源代码查看器 -->
    <el-dialog
        v-model="codeDialogVisible"
        append-to-body
        title="解题代码查看"
        top="5vh"
        width="80%"
    >
      <el-row :gutter="20">
        <el-col :span="16">
          <div class="code-container">
            <div class="code-toolbar">
              <div class="toolbar-left">
                <el-tag size="small">{{ currentSubmission?.language }}</el-tag>

                <!-- Settings Popover -->
                <el-popover :width="300" placement="bottom" popper-class="editor-settings-popover" trigger="click">
                  <template #reference>
                    <el-button :icon="Setting" circle class="settings-btn" size="small"/>
                  </template>
                  <div class="settings-panel">
                    <h4 class="settings-title">查看器设置</h4>
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
              <el-button size="small" @click="copyCode">复制代码</el-button>
            </div>
            <div class="code-viewer-wrapper">
              <pre :style="viewerStyle" class="hljs" v-html="highlightedCode"></pre>
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <el-card class="ai-analysis-card" shadow="never">
            <template #header>
              <div class="flex justify-between items-center">
                <span>AI 代码分析</span>
                <el-button
                    :loading="aiLoading"
                    size="small"
                    type="primary"
                    @click="analyzeCode"
                >
                  开始分析
                </el-button>
              </div>
            </template>
            <div v-if="aiResult" class="ai-result">
              <div class="ai-section">
                <div class="ai-label">代码评价:</div>
                <el-tag :type="getAiTagType(aiResult.rating)">{{ aiResult.rating }}</el-tag>
              </div>
              <div class="ai-section">
                <div class="ai-label">核心思路:</div>
                <p>{{ aiResult.logic }}</p>
              </div>
              <div class="ai-section">
                <div class="ai-label">改进建议:</div>
                <p>{{ aiResult.suggestion }}</p>
              </div>
            </div>
            <el-empty v-else description="点击按钮开始 AI 分析"/>
          </el-card>
        </el-col>
      </el-row>
    </el-dialog>
  </div>
</template>

<script setup>
import {computed, onMounted, onUnmounted, ref, watch} from 'vue'
import {useRoute} from 'vue-router'
import {getExamMonitor, getSubmissionDetail} from '@/api/exam'
import {getProblemDetail} from '@/api/problem'
import {askLLM} from '@/api/llm'
import {Refresh, Setting, View} from '@element-plus/icons-vue'
import {ElMessage} from 'element-plus'
import hljs from 'highlight.js'
import 'highlight.js/styles/vs2015.css'

const route = useRoute()
const examId = route.params.id
const examTitle = ref('加载中...')
const loading = ref(false)
const participants = ref([])
const problems = ref([])
const totalSubmissions = ref(0)

// L2 & L3 State
const drawerVisible = ref(false)
const codeDialogVisible = ref(false)
const detailLoading = ref(false)
const currentSubmission = ref(null)
const currentProblem = ref(null)

// Viewer Settings (Sync with ProblemDetailView)
const fontSize = ref(parseInt(localStorage.getItem('editorFontSize') || '16'))
const fontFamily = ref(localStorage.getItem('editorFontFamily') || "'Fira Code', 'Courier New', monospace")
const fontLigatures = ref(localStorage.getItem('editorFontLigatures') !== 'false')

const saveSettings = () => {
  localStorage.setItem('editorFontSize', fontSize.value)
  localStorage.setItem('editorFontFamily', fontFamily.value)
  localStorage.setItem('editorFontLigatures', fontLigatures.value)
}

const viewerStyle = computed(() => ({
  fontSize: fontSize.value + 'px',
  fontFamily: fontFamily.value,
  fontVariantLigatures: fontLigatures.value ? 'normal' : 'none'
}))

const autoRefresh = ref(false)
let refreshTimer = null

// AI Analysis State
const aiLoading = ref(false)
const aiResult = ref(null)

const fullScoreCount = computed(() => {
  if (!participants.value.length || !problems.value.length) return 0
  const maxPossible = problems.value.reduce((sum, p) => sum + (p.max_score || 0), 0)
  return participants.value.filter(u => u.total_score >= maxPossible).length
})

const highlightedCode = computed(() => {
  if (!currentSubmission.value?.code) return ''
  const lang = currentSubmission.value.language?.toLowerCase() || 'plaintext'
  try {
    return hljs.highlight(currentSubmission.value.code, {language: lang}).value
  } catch (e) {
    return hljs.highlightAuto(currentSubmission.value.code).value
  }
})

const fetchMonitorData = async () => {
  loading.value = true
  try {
    const data = await getExamMonitor(examId)
    if (data) {
      examTitle.value = data.exam_title || '未知考试'
      participants.value = data.users || []
      problems.value = data.problems || []
      let count = 0
      participants.value.forEach(user => {
        if (user.submissions) count += Object.keys(user.submissions).length
      })
      totalSubmissions.value = count
    }
  } catch (error) {
    ElMessage.error('获取监控数据失败')
  } finally {
    loading.value = false
  }
}

const getProblemLabel = (problem, index) => {
  return problem.display_id ? `P${problem.display_id}` : `题目 ${problem.problem_id}`
}

const getSubmission = (userId, problemId) => {
  const user = participants.value.find(u => u.user_id === userId)
  return user?.submissions?.[problemId] || null
}

const getScoreTagType = (score) => {
  if (score >= 100) return 'success'
  if (score > 0) return 'warning'
  return 'danger'
}

const getScoreClass = (score) => {
  if (score >= 100) return 'text-success'
  if (score > 0) return 'text-warning'
  return 'text-danger'
}

// 进入二级界面
const openLevel2 = async (userId, problemId) => {
  const sub = getSubmission(userId, problemId)
  if (!sub || !sub.submission_id) return

  drawerVisible.value = true
  detailLoading.value = true
  try {
    // 同时获取提交详情和题目详情
    const [subDetail, probDetail] = await Promise.all([
      getSubmissionDetail(sub.submission_id),
      getProblemDetail(problemId)
    ])
    currentSubmission.value = subDetail
    currentProblem.value = probDetail
  } catch (error) {
    ElMessage.error('获取详情失败')
    drawerVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

// 进入三级界面
const openLevel3 = () => {
  aiResult.value = null
  codeDialogVisible.value = true
}

const analyzeCode = async () => {
  if (!currentSubmission.value?.code || !currentProblem.value) return

  aiLoading.value = true
  try {
    const res = await askLLM({
      system_setting: "你是一个专业的编程导师，负责分析学生的解题代码。请结合题目内容和学生的得分情况，分析代码的逻辑、质量并给出改进建议。",
      prompt: `题目名称: ${currentProblem.value.title}\n题目内容: ${currentProblem.value.content}\n编程语言: ${currentSubmission.value.language}\n判题状态: ${currentSubmission.value.status}\n得分: ${currentSubmission.value.score}\n学生代码:\n${currentSubmission.value.code}`,
      output_format: {
        rating: "优秀/良好/及格/需改进",
        logic: "代码核心逻辑简述",
        suggestion: "结合得分情况给出具体的改进建议（如：为什么没拿满分，或者如何优化性能）"
      }
    })
    aiResult.value = res
  } catch (error) {
    ElMessage.error('AI 分析失败')
  } finally {
    aiLoading.value = false
  }
}

const getAiTagType = (rating) => {
  if (rating === '优秀') return 'success'
  if (rating === '良好') return 'primary'
  if (rating === '及格') return 'warning'
  return 'danger'
}

const getStatusType = (status) => {
  if (!status) return 'info'
  const s = status.toLowerCase()
  if (s === 'accepted') return 'success'
  if (s === 'pending' || s === 'judging') return 'warning'
  return 'danger'
}

const formatTime = (time) => time ? new Date(time).toLocaleString() : ''

const copyCode = () => {
  if (currentSubmission.value?.code) {
    navigator.clipboard.writeText(currentSubmission.value.code)
    ElMessage.success('代码已复制')
  }
}

watch(autoRefresh, (val) => {
  if (val) refreshTimer = setInterval(fetchMonitorData, 10000)
  else clearInterval(refreshTimer)
})

onMounted(fetchMonitorData)
onUnmounted(() => clearInterval(refreshTimer))
</script>

<style scoped>
.exam-monitor-container {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.mb-4 {
  margin-bottom: 20px;
}

.mt-6 {
  margin-top: 24px;
}

.stat-card {
  text-align: center;
}

.score-cell {
  display: flex;
  justify-content: center;
}

.score-tag {
  cursor: pointer;
  width: 60px;
  font-weight: bold;
}

.font-bold {
  font-weight: bold;
}

.text-primary {
  color: var(--el-color-primary);
}

.text-success {
  color: var(--el-color-success);
}

.text-warning {
  color: var(--el-color-warning);
}

.text-danger {
  color: var(--el-color-danger);
}

/* L2 Styles */
.detail-section h4 {
  margin-bottom: 12px;
  padding-left: 8px;
  border-left: 4px solid var(--el-color-primary);
}

.score-large {
  font-size: 24px;
  font-weight: 800;
}

/* L3 Styles */
.code-container {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  overflow: hidden;
}

.code-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f8f9fa;
  border-bottom: 1px solid var(--el-border-color);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.settings-btn {
  background-color: transparent;
  border: none;
  color: #888;
  transition: color 0.3s;
}

.settings-btn:hover {
  color: var(--el-color-primary);
  background-color: #ecf5ff;
}

.code-viewer-wrapper {
  background: #1e1e1e;
  max-height: 65vh;
  overflow: auto;
}

.hljs {
  margin: 0;
  padding: 16px;
  line-height: 1.5;
  background: transparent;
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

.ai-analysis-card {
  height: 100%;
}

.ai-section {
  margin-bottom: 16px;
}

.ai-label {
  font-weight: bold;
  margin-bottom: 4px;
  color: #606266;
}

.ai-result p {
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  margin: 0;
  white-space: pre-wrap;
}
</style>
