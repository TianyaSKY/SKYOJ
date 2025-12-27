<template>
  <div class="exam-detail-container">
    <!-- Exam Header Banner -->
    <div class="exam-header-banner">
      <div class="header-main">
        <h1 class="exam-title">{{ exam.title }}</h1>
        <div class="exam-description">
          <el-icon><InfoFilled /></el-icon>
          <span>{{ exam.description || '暂无考试说明' }}</span>
        </div>
      </div>
      <div class="header-timer">
        <div :class="['timer-box', timerStatus.type]">
          <div class="timer-label">{{ timerStatus.label }}</div>
          <div class="timer-value">{{ remainingTimeStr }}</div>
        </div>
      </div>
    </div>

    <el-row :gutter="24">
      <!-- Left: Problems -->
      <el-col :lg="17" :md="16" :sm="24">
        <el-card class="problem-list-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="title-with-icon">
                <el-icon><List /></el-icon>题目列表
              </span>
              <el-tag type="info" effect="plain">{{ problemStatus.length }} 道题目</el-tag>
            </div>
          </template>

          <el-table v-loading="statusLoading" :data="problemStatus" stripe style="width: 100%">
            <el-table-column align="center" label="#" prop="display_id" width="70">
              <template #default="scope">
                <span class="index-num">{{ scope.row.display_id }}</span>
              </template>
            </el-table-column>
            <el-table-column label="题目名称" min-width="200">
              <template #default="scope">
                <div class="problem-name-cell">
                  <el-link :underline="false" class="problem-link" @click="goToProblem(scope.row.problem_id)">
                    {{ scope.row.title }}
                  </el-link>
                </div>
              </template>
            </el-table-column>
            <el-table-column align="center" label="得分 / 总分" width="150">
              <template #default="scope">
                <span :class="['score-text', { 'has-score': scope.row.current_score > 0 }]">
                  {{ scope.row.current_score }}
                </span>
                <span class="score-sep">/</span>
                <span class="max-score">{{ scope.row.max_score }}</span>
              </template>
            </el-table-column>
            <el-table-column align="center" label="状态" width="140">
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)" effect="light" round size="small">
                  {{ getStatusLabel(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column align="center" label="操作" width="120">
              <template #default="scope">
                <el-button
                  :type="scope.row.status === 'Not Attempted' ? 'primary' : 'success'"
                  plain
                  size="small"
                  @click="goToProblem(scope.row.problem_id)"
                >
                  {{ scope.row.status === 'Not Attempted' ? '开始' : '继续' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- Right: Sidebar -->
      <el-col :lg="7" :md="8" :sm="24">
        <el-card class="info-sidebar-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="title-with-icon">
                <el-icon><DataAnalysis /></el-icon>考试概览
              </span>
            </div>
          </template>

          <div class="progress-section">
            <div class="progress-info">
              <span>当前总分</span>
              <span class="score-ratio">{{ totalCurrentScore }} / {{ totalMaxScore }}</span>
            </div>
            <el-progress
              :percentage="totalMaxScore > 0 ? Math.round((totalCurrentScore / totalMaxScore) * 100) : 0"
              :stroke-width="12"
              :color="customColors"
            />
          </div>

          <div class="info-details">
            <div class="info-row">
              <span class="label">开始时间</span>
              <span class="value">{{ formatTime(exam.start_time) }}</span>
            </div>
            <div class="info-row">
              <span class="label">结束时间</span>
              <span class="value">{{ formatTime(exam.end_time) }}</span>
            </div>
            <div class="info-row">
              <span class="label">题目数量</span>
              <span class="value">{{ exam.problems?.length || 0 }}</span>
            </div>
          </div>

          <div class="action-buttons">
            <el-button class="action-btn" type="primary" @click="goToRank">
              <el-icon><Trophy /></el-icon>查看实时排名
            </el-button>
            <el-button class="action-btn" @click="fetchStatus">
              <el-icon><Refresh /></el-icon>刷新题目状态
            </el-button>
            <el-divider />
            <el-button class="action-btn" type="danger" plain @click="handleExitExam">
              <el-icon><SwitchButton /></el-icon>退出考试模式
            </el-button>
          </div>
        </el-card>

        <el-alert
            :closable="false"
            class="mt-4"
            show-icon
            title="考试守则"
            type="warning"
        >
          <div class="rules-content">
            <p>1. 严禁任何形式的作弊行为。</p>
            <p>2. 考试期间请保持网络连接稳定。</p>
            <p>3. 遇到技术问题请及时联系监考人员。</p>
          </div>
        </el-alert>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import {computed, onMounted, onUnmounted, ref} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {exitExam, getExamDetail, getMyExamStatus} from '@/api/exam'
import {ElMessage, ElMessageBox} from 'element-plus'
import {
  DataAnalysis,
  InfoFilled,
  List,
  Refresh,
  SwitchButton,
  Trophy
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const examId = route.params.id

const exam = ref({
  title: '加载中...',
  description: '',
  start_time: '',
  end_time: '',
  problems: []
})

const problemStatus = ref([])
const statusLoading = ref(false)
const remainingTime = ref(0)
let timer = null

const customColors = [
  { color: '#f56c6c', percentage: 20 },
  { color: '#e6a23c', percentage: 40 },
  { color: '#5cb87a', percentage: 60 },
  { color: '#1989fa', percentage: 80 },
  { color: '#6f7ad3', percentage: 100 },
]

const fetchExamData = async () => {
  try {
    const data = await getExamDetail(examId)
    exam.value = data
    startTimer()
    fetchStatus()
  } catch (error) {
    ElMessage.error('获取考试详情失败')
    router.push('/exam')
  }
}

const fetchStatus = async () => {
  statusLoading.value = true
  try {
    const data = await getMyExamStatus()
    problemStatus.value = data
  } catch (error) {
    console.error('Failed to fetch exam status', error)
  } finally {
    statusLoading.value = false
  }
}

const totalCurrentScore = computed(() => {
  return problemStatus.value.reduce((sum, p) => sum + (p.current_score || 0), 0)
})

const totalMaxScore = computed(() => {
  return problemStatus.value.reduce((sum, p) => sum + (p.max_score || 0), 0)
})

const getStatusType = (status) => {
  if (status === 'Accepted') return 'success'
  if (status === 'Not Attempted') return 'info'
  if (status === 'Pending' || status === 'Judging') return 'warning'
  return 'danger'
}

const getStatusLabel = (status) => {
  const map = {
    'Accepted': '已通过',
    'Not Attempted': '未尝试',
    'Pending': '评测中',
    'Judging': '评测中',
    'Wrong Answer': '答案错误',
    'Runtime Error': '运行错误',
    'Time Limit Exceeded': '超时',
    'Memory Limit Exceeded': '超内存',
    'Compile Error': '编译错误'
  }
  return map[status] || status
}

const startTimer = () => {
  updateRemainingTime()
  timer = setInterval(updateRemainingTime, 1000)
}

const updateRemainingTime = () => {
  const now = dayjs()
  const end = dayjs(exam.value.end_time)
  const start = dayjs(exam.value.start_time)

  if (now.isBefore(start)) {
    remainingTime.value = start.diff(now, 'second')
  } else if (now.isBefore(end)) {
    remainingTime.value = end.diff(now, 'second')
  } else {
    remainingTime.value = 0
    if (timer) {
      clearInterval(timer)
      timer = null
      handleExamEnd()
    }
  }
}

const handleExamEnd = async () => {
  ElMessageBox.alert('考试已结束，系统将自动退出考试模式。', '提示', {
    confirmButtonText: '确定',
    callback: async () => {
      await performExit()
    }
  })
}

const handleExitExam = () => {
  ElMessageBox.confirm('确定要退出考试吗？退出后将无法继续在考试模式下提交。', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    await performExit()
  })
}

const performExit = async () => {
  try {
    const res = await exitExam()
    if (res.token) {
      localStorage.setItem('token', res.token)
    }
    ElMessage.success('已退出考试')
    router.push('/exam')
  } catch (error) {
    ElMessage.error('退出考试失败')
  }
}

const remainingTimeStr = computed(() => {
  const seconds = remainingTime.value
  if (seconds <= 0) return '00:00:00'

  const h = Math.floor(seconds / 3600).toString().padStart(2, '0')
  const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0')
  const s = (seconds % 60).toString().padStart(2, '0')

  return `${h}:${m}:${s}`
})

const timerStatus = computed(() => {
  const now = dayjs()
  const start = dayjs(exam.value.start_time)
  const end = dayjs(exam.value.end_time)

  if (now.isBefore(start)) {
    return {label: '距离开始', type: 'info'}
  } else if (now.isBefore(end)) {
    return {label: '剩余时间', type: 'danger'}
  } else {
    return {label: '已结束', type: 'info'}
  }
})

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const goToProblem = (problemId) => {
  router.push({
    path: `/problem/${problemId}`,
    query: {exam_id: examId}
  })
}

const goToRank = () => {
  router.push(`/exam/${examId}/rank`)
}

onMounted(() => {
  fetchExamData()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.exam-detail-container {
  max-width: 1300px;
  margin: 0 auto;
  padding: 24px;
}

/* Header Banner */
.exam-header-banner {
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  border-radius: 12px;
  padding: 32px;
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: white;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.exam-title {
  margin: 0 0 12px 0;
  font-size: 28px;
  font-weight: 600;
}

.exam-description {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #cbd5e1;
  font-size: 15px;
}

.timer-box {
  background: rgba(255, 255, 255, 0.1);
  padding: 16px 24px;
  border-radius: 12px;
  text-align: center;
  min-width: 160px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.timer-box.danger {
  border-color: #f87171;
  background: rgba(248, 113, 113, 0.1);
}

.timer-label {
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 4px;
  color: #94a3b8;
}

.timer-value {
  font-size: 32px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-weight: bold;
}

.timer-box.danger .timer-value {
  color: #f87171;
}

/* Cards */
.problem-list-card, .info-sidebar-card {
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.title-with-icon {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}

/* Table Styling */
.index-num {
  font-weight: bold;
  color: #64748b;
}

.problem-link {
  font-size: 16px;
  font-weight: 500;
  color: #2563eb;
}

.score-text {
  font-weight: bold;
  font-size: 16px;
  color: #94a3b8;
}

.score-text.has-score {
  color: #10b981;
}

.score-sep {
  margin: 0 4px;
  color: #cbd5e1;
}

.max-score {
  color: #64748b;
}

/* Sidebar Info */
.progress-section {
  margin-bottom: 24px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
  color: #64748b;
}

.score-ratio {
  font-weight: bold;
  color: #334155;
}

.info-details {
  background: #f8fafc;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 24px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 14px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-row .label {
  color: #64748b;
}

.info-row .value {
  color: #334155;
  font-weight: 500;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-btn {
  width: 100%;
  margin-left: 0 !important;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.mt-4 {
  margin-top: 16px;
}

.rules-content {
  font-size: 13px;
  line-height: 1.6;
}

.rules-content p {
  margin: 4px 0;
}
</style>
