<template>
  <div class="exam-monitor-container">
    <!-- Fullscreen Balloon Overlay -->
    <div class="balloon-overlay" v-if="showFullscreenBalloons">
      <div
        v-for="b in balloons"
        :key="b.id"
        class="floating-balloon"
        :style="{
          left: b.x + '%',
          backgroundColor: b.color,
          animationDuration: b.duration + 's',
          animationDelay: b.delay + 's'
        }"
      >
        <div class="balloon-string"></div>
        <div class="balloon-text" v-if="b.text">{{ b.text }}</div>
      </div>
    </div>

    <!-- L1: 监控大屏主界面 -->
    <div class="monitor-header">
      <el-page-header @back="$router.back()">
        <template #content>
          <div class="header-main">
            <span class="exam-title">考试监控: {{ examTitle }}</span>
            <div class="header-stats">
              <el-tag type="info" effect="plain" round>
                <el-icon><User /></el-icon> {{ participants?.length || 0 }} 考生
              </el-tag>
              <el-tag type="success" effect="plain" round>
                <el-icon><Upload /></el-icon> {{ totalSubmissions }} 提交
              </el-tag>
              <el-tag type="warning" effect="plain" round>
                <el-icon><Star /></el-icon> {{ fullScoreCount }} 满分
              </el-tag>
            </div>
          </div>
        </template>
        <template #extra>
          <div class="header-actions">
            <div class="refresh-control">
              <span class="control-label">自动刷新</span>
              <el-switch v-model="autoRefresh" @change="handleAutoRefreshChange" />
            </div>
            <el-button :icon="Refresh" :loading="loading" circle @click="fetchMonitorData"/>
            <el-button type="warning" :loading="plagiarismLoading" @click="handleCheckExamPlagiarism">
              全场查重
            </el-button>
          </div>
        </template>
      </el-page-header>
    </div>

    <!-- Integrated Rank Section (Expanded Mini Rank) -->
    <div class="rank-integration-section">
      <el-card class="mini-rank-card" shadow="never">
        <template #header>
          <div class="card-header">
            <div class="title-with-icon">
              <el-icon class="rank-icon"><Trophy /></el-icon>
              <span>实时滚榜 (Top 10)</span>
            </div>
            <el-button link type="primary" @click="$router.push(`/exam/${examId}/rank`)">
              查看完整榜单 <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
        </template>
        <el-table :data="rankData.slice(0, 10)" size="small" style="width: 100%">
          <el-table-column label="排名" width="70" align="center">
            <template #default="scope">
              <div class="rank-num-wrapper">
                <el-icon v-if="scope.$index === 0" class="medal gold"><Trophy /></el-icon>
                <el-icon v-else-if="scope.$index === 1" class="medal silver"><Trophy /></el-icon>
                <el-icon v-else-if="scope.$index === 2" class="medal bronze"><Trophy /></el-icon>
                <span v-else class="rank-num">{{ scope.$index + 1 }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="选手" prop="username" min-width="180">
            <template #default="scope">
              <div class="user-cell">
                <el-avatar :size="24" :src="scope.row.avatar ? `/api${scope.row.avatar}` : ''" class="mini-avatar">
                  {{ scope.row.username?.charAt(0).toUpperCase() }}
                </el-avatar>
                <span class="username-text">{{ scope.row.username }}</span>
                <transition name="balloon-pop">
                  <div v-if="rankChangedUsers.has(scope.row.username)" class="up-tag">UP!</div>
                </transition>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="解题进度" min-width="200">
            <template #default="scope">
              <el-progress
                :percentage="problems.length > 0 ? Math.round((scope.row.solved / problems.length) * 100) : 0"
                :stroke-width="8"
                :format="() => `${scope.row.solved} / ${problems.length}`"
                :color="getProgressColor(scope.row.solved)"
              />
            </template>
          </el-table-column>
          <el-table-column label="罚时" width="120" align="right">
            <template #default="scope">
              <span class="penalty-mini">{{ formatDuration(scope.row.penalty) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- Monitor Table -->
    <el-card class="monitor-table-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-with-icon">
            <el-icon><Grid /></el-icon>
            <span>详细监控矩阵</span>
          </div>
          <div class="legend">
            <span class="legend-item"><span class="dot success"></span> 满分</span>
            <span class="legend-item"><span class="dot warning"></span> 部分通过</span>
            <span class="legend-item"><span class="dot danger"></span> 未通过</span>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="participants || []" border stripe style="width: 100%">
        <el-table-column fixed label="考生" prop="username" width="180">
          <template #default="scope">
            <div class="participant-cell">
              <div class="user-info">
                <el-avatar :size="24" :src="scope.row.avatar ? `/api${scope.row.avatar}` : ''" class="mini-avatar">
                  {{ scope.row.username?.charAt(0).toUpperCase() }}
                </el-avatar>
                <span class="username">{{ scope.row.username }}</span>
              </div>
              <el-tag v-if="scope.row.total_score >= maxPossibleScore" size="small" type="success" effect="dark">AC</el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column
            v-for="(problem, index) in problems"
            :key="problem.problem_id"
            :label="getProblemLabel(problem, index)"
            align="center"
            min-width="100"
        >
          <template #default="scope">
            <div v-if="getSubmission(scope.row.user_id, problem.problem_id)" class="score-cell">
              <div
                :class="['score-box', getScoreStatusClass(getSubmission(scope.row.user_id, problem.problem_id).score)]"
                @click="openLevel2(scope.row.user_id, problem.problem_id)"
              >
                {{ getSubmission(scope.row.user_id, problem.problem_id).score }}
              </div>
            </div>
            <span v-else class="empty-score">-</span>
          </template>
        </el-table-column>

        <el-table-column align="center" fixed="right" label="总分" prop="total_score" sortable width="100">
          <template #default="scope">
            <span class="total-score-text">{{ scope.row.total_score }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- L2 & L3 Drawers/Dialogs -->
    <el-drawer v-model="drawerVisible" destroy-on-close size="500px" title="提交详细得分">
      <div v-if="detailLoading" v-loading="true" style="height: 200px"></div>
      <div v-else-if="currentSubmission" class="drawer-content">
        <div class="detail-section">
          <div class="section-header">
            <h4>基本信息</h4>
            <el-button :loading="singlePlagiarismLoading" size="small" type="warning" plain @click="handleCheckSinglePlagiarism">
              单次查重
            </el-button>
          </div>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusType(currentSubmission.status)">{{ currentSubmission.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="最终得分">
              <span :class="['score-display', getScoreStatusClass(currentSubmission.score)]">{{ currentSubmission.score }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="编程语言">{{ currentSubmission.language }}</el-descriptions-item>
            <el-descriptions-item label="提交时间">{{ formatTime(currentSubmission.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="detail-section mt-6">
          <h4>得分分析</h4>
          <el-alert :closable="false" show-icon :title="currentSubmission.status === 'Accepted' ? '所有测试点已通过' : `未完全通过: ${currentSubmission.status}`" :type="currentSubmission.status === 'Accepted' ? 'success' : 'error'" />
          <div class="mt-6 text-center">
            <el-button :icon="View" type="primary" size="large" @click="openLevel3">查看解题代码</el-button>
          </div>
        </div>
      </div>
    </el-drawer>

    <el-dialog v-model="codeDialogVisible" append-to-body title="解题代码查看" top="5vh" width="85%">
      <el-row :gutter="20">
        <el-col :span="17">
          <div class="code-container">
            <div class="code-toolbar">
              <div class="toolbar-left">
                <el-tag size="small" effect="dark">{{ currentSubmission?.language }}</el-tag>
                <el-divider direction="vertical" />
                <span class="code-info">提交 ID: {{ currentSubmission?.id }}</span>
              </div>
              <el-button size="small" @click="copyCode">复制代码</el-button>
            </div>
            <div class="code-viewer-wrapper">
              <pre :style="viewerStyle" class="hljs" v-html="highlightedCode"></pre>
            </div>
          </div>
        </el-col>
        <el-col :span="7">
          <el-card class="ai-analysis-card" shadow="never">
            <template #header>
              <div class="flex justify-between items-center">
                <span>AI 代码分析</span>
                <el-button :loading="aiLoading" size="small" type="primary" @click="analyzeCode">开始分析</el-button>
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
import {
  checkExamPlagiarism,
  checkSubmissionPlagiarism,
  getExamMonitor,
  getExamRank,
  getSubmissionDetail
} from '@/api/exam'
import {getProblemDetail} from '@/api/problem'
import {askLLM} from '@/api/llm'
import {
  ArrowRight,
  Grid,
  Refresh,
  Star,
  Trophy,
  Upload,
  User,
  View
} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from 'element-plus'
import hljs from 'highlight.js'
import 'highlight.js/styles/vs2015.css'
import dayjs from 'dayjs'

const route = useRoute()
const examId = route.params.id
const examTitle = ref('加载中...')
const loading = ref(false)
const participants = ref([])
const problems = ref([])
const totalSubmissions = ref(0)
const rankData = ref([])

// L2 & L3 State
const drawerVisible = ref(false)
const codeDialogVisible = ref(false)
const detailLoading = ref(false)
const currentSubmission = ref(null)
const currentProblem = ref(null)

// Plagiarism State
const plagiarismLoading = ref(false)
const singlePlagiarismLoading = ref(false)

// AI Analysis State
const aiLoading = ref(false)
const aiResult = ref(null)

// Balloon State
const showFullscreenBalloons = ref(false)
const balloons = ref([])
const rankChangedUsers = ref(new Set())
let previousRankMap = new Map()
const BALLOON_COLORS = ['#ff4d4f', '#1890ff', '#52c41a', '#fadb14', '#722ed1', '#eb2f96']

// Viewer Settings
const fontSize = ref(parseInt(localStorage.getItem('editorFontSize') || '16'))
const fontFamily = ref(localStorage.getItem('editorFontFamily') || "'Fira Code', 'Courier New', monospace")
const fontLigatures = ref(localStorage.getItem('editorFontLigatures') !== 'false')

const viewerStyle = computed(() => ({
  fontSize: fontSize.value + 'px',
  fontFamily: fontFamily.value,
  fontVariantLigatures: fontLigatures.value ? 'normal' : 'none'
}))

const autoRefresh = ref(localStorage.getItem('exam_monitor_auto_refresh') === 'true')
const lastUpdateTime = ref('')
let refreshTimer = null

const maxPossibleScore = computed(() => {
  return problems.value.reduce((sum, p) => sum + (p.max_score || 100), 0)
})

const fullScoreCount = computed(() => {
  if (!participants.value.length) return 0
  const max = maxPossibleScore.value
  return participants.value.filter(u => u.total_score >= max).length
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

const triggerFullscreenBalloons = (users) => {
  const newBalloons = []
  const userList = Array.from(users)
  for (let i = 0; i < 12; i++) {
    newBalloons.push({
      id: Date.now() + i,
      x: Math.random() * 90 + 5,
      color: BALLOON_COLORS[Math.floor(Math.random() * BALLOON_COLORS.length)],
      duration: 4 + Math.random() * 3,
      delay: Math.random() * 1.5,
      text: i < userList.length ? userList[i] : ''
    })
  }
  balloons.value = newBalloons
  showFullscreenBalloons.value = true
  setTimeout(() => { showFullscreenBalloons.value = false }, 7000)
}

const fetchMonitorData = async (isAuto = false) => {
  if (!isAuto) loading.value = true
  try {
    const [monitorRes, rankRes] = await Promise.all([
      getExamMonitor(examId),
      getExamRank(examId)
    ])

    if (monitorRes) {
      examTitle.value = monitorRes.exam_title || '未知考试'
      participants.value = monitorRes.users || []
      problems.value = monitorRes.problems || []
      let count = 0
      participants.value.forEach(user => {
        if (user.submissions) count += Object.keys(user.submissions).length
      })
      totalSubmissions.value = count
    }

    if (rankRes) {
      const newRankData = rankRes.rank
      const currentRankMap = new Map()
      const improvedUsers = new Set()

      newRankData.forEach((user, index) => {
        currentRankMap.set(user.username, index)
        if (previousRankMap.has(user.username)) {
          const oldRank = previousRankMap.get(user.username)
          if (index < oldRank) improvedUsers.add(user.username)
        }
      })

      rankData.value = newRankData
      previousRankMap = currentRankMap

      if (improvedUsers.size > 0) {
        rankChangedUsers.value = improvedUsers
        triggerFullscreenBalloons(improvedUsers)
        setTimeout(() => { rankChangedUsers.value = new Set() }, 5000)
      }
    }

    lastUpdateTime.value = dayjs().format('HH:mm:ss')
  } catch (error) {
    console.error(error)
  } finally {
    if (!isAuto) loading.value = false
  }
}

const handleAutoRefreshChange = (val) => {
  localStorage.setItem('exam_monitor_auto_refresh', val)
}

const getProblemLabel = (problem, index) => {
  return problem.display_id ? `P${problem.display_id}` : `T${index + 1}`
}

const getSubmission = (userId, problemId) => {
  const user = participants.value.find(u => u.user_id === userId)
  return user?.submissions?.[problemId] || null
}

const getScoreStatusClass = (score) => {
  if (score >= 100) return 'score-success'
  if (score > 0) return 'score-warning'
  return 'score-danger'
}

const getProgressColor = (solved) => {
  const total = problems.value.length
  if (total === 0) return '#94a3b8'
  const ratio = solved / total
  if (ratio >= 0.8) return '#10b981'
  if (ratio >= 0.5) return '#3b82f6'
  if (ratio >= 0.2) return '#f59e0b'
  return '#ef4444'
}

const openLevel2 = async (userId, problemId) => {
  const sub = getSubmission(userId, problemId)
  if (!sub || !sub.submission_id) return
  drawerVisible.value = true
  detailLoading.value = true
  try {
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
        suggestion: "结合得分情况给出具体的改进建议"
      }
    })
    aiResult.value = res
  } catch (error) {
    ElMessage.error('AI 分析失败')
  } finally {
    aiLoading.value = false
  }
}

const handleCheckExamPlagiarism = async () => {
  try {
    await ElMessageBox.confirm('确定要对整场考试进行查重吗？', '全场查重确认', { type: 'warning' })
    plagiarismLoading.value = true
    await checkExamPlagiarism(examId)
    ElMessage.success('查重任务已提交')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('查重失败')
  } finally { plagiarismLoading.value = false }
}

const handleCheckSinglePlagiarism = async () => {
  if (!currentSubmission.value?.id) return
  try {
    singlePlagiarismLoading.value = true
    await checkSubmissionPlagiarism(currentSubmission.value.id)
    ElMessage.success('单次查重任务已提交')
  } catch (error) { ElMessage.error('查重失败') }
  finally { singlePlagiarismLoading.value = false }
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

const formatTime = (time) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : ''

const formatDuration = (seconds) => {
  if (!seconds) return '0'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

const copyCode = () => {
  if (currentSubmission.value?.code) {
    navigator.clipboard.writeText(currentSubmission.value.code)
    ElMessage.success('代码已复制')
  }
}

watch(autoRefresh, (val) => {
  if (val) refreshTimer = setInterval(() => fetchMonitorData(true), 10000)
  else clearInterval(refreshTimer)
}, { immediate: true })

onMounted(fetchMonitorData)
onUnmounted(() => clearInterval(refreshTimer))
</script>

<style scoped>
.exam-monitor-container {
  padding: 24px;
  background-color: #f8fafc;
  min-height: calc(100vh - 60px);
  position: relative;
}

/* Fullscreen Balloon Overlay */
.balloon-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  pointer-events: none;
  z-index: 9999;
  overflow: hidden;
}

.floating-balloon {
  position: absolute;
  bottom: -150px;
  width: 50px;
  height: 65px;
  border-radius: 50% 50% 50% 50% / 40% 40% 60% 60%;
  animation: float-up linear forwards;
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: inset -5px -5px 10px rgba(0,0,0,0.1);
}

.balloon-string {
  position: absolute;
  bottom: -30px;
  width: 1px;
  height: 30px;
  background: rgba(0,0,0,0.1);
}

.balloon-text {
  color: white;
  font-size: 10px;
  font-weight: bold;
  text-align: center;
  padding: 0 4px;
}

@keyframes float-up {
  0% { transform: translateY(0) rotate(0deg); opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { transform: translateY(-120vh) rotate(15deg); opacity: 0; }
}

/* Header */
.monitor-header {
  background: white;
  padding: 16px 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  margin-bottom: 24px;
}

.header-main {
  display: flex;
  align-items: center;
  gap: 16px;
}

.exam-title {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
}

.header-stats {
  display: flex;
  gap: 8px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.refresh-control {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #64748b;
}

/* Rank Integration */
.rank-integration-section {
  margin-bottom: 24px;
}

.mini-rank-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-with-icon {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #334155;
}

.rank-num-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
}

.medal {
  font-size: 18px;
}

.medal.gold { color: #fbbf24; }
.medal.silver { color: #94a3b8; }
.medal.bronze { color: #d97706; }

.rank-num {
  font-weight: bold;
  color: #64748b;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mini-avatar {
  background-color: var(--el-color-primary);
  color: white;
  flex-shrink: 0;
}

.username-text {
  font-weight: 600;
  color: #334155;
}

.up-tag {
  background: #10b981;
  color: white;
  font-size: 10px;
  padding: 0 4px;
  border-radius: 4px;
  font-weight: bold;
  animation: balloon-pop 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.penalty-mini {
  font-family: monospace;
  color: #64748b;
}

/* Monitor Table */
.monitor-table-card {
  border-radius: 12px;
}

.legend {
  display: flex;
  gap: 16px;
  font-size: 12px;
  font-weight: normal;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.success { background: #10b981; }
.dot.warning { background: #f59e0b; }
.dot.danger { background: #ef4444; }

.participant-cell {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.username {
  font-weight: 600;
  color: #334155;
}

.score-box {
  width: 40px;
  height: 28px;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 4px;
  font-weight: bold;
  font-size: 13px;
  cursor: pointer;
  margin: 0 auto;
  transition: transform 0.2s;
}

.score-box:hover {
  transform: scale(1.1);
}

.score-success { background: #ecfdf5; color: #10b981; border: 1px solid #10b981; }
.score-warning { background: #fffbeb; color: #f59e0b; border: 1px solid #f59e0b; }
.score-danger { background: #fef2f2; color: #ef4444; border: 1px solid #ef4444; }

.empty-score { color: #cbd5e1; }

.total-score-text {
  font-weight: 800;
  color: #3b82f6;
}

/* Drawer & Dialog */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.score-display {
  font-size: 24px;
  font-weight: 800;
  padding: 4px 12px;
  border-radius: 8px;
}

.code-container {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.code-toolbar {
  background: #f8fafc;
  padding: 8px 16px;
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid #e2e8f0;
}

.code-info {
  font-size: 12px;
  color: #64748b;
}

.code-viewer-wrapper {
  background: #1e1e1e;
  max-height: 60vh;
  overflow: auto;
}

.hljs { padding: 20px; }

@keyframes balloon-pop {
  0% { transform: scale(0); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}
</style>
