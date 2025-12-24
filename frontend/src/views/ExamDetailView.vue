<template>
  <div class="exam-detail-container">
    <el-row :gutter="20">
      <!-- Left: Exam Info & Problems -->
      <el-col :span="18">
        <el-card shadow="never" class="mb-4">
          <template #header>
            <div class="exam-header">
              <h2 class="exam-title">{{ exam.title }}</h2>
              <div class="exam-meta">
                <el-tag :type="timerStatus.type" effect="dark" class="timer-tag">
                  {{ timerStatus.label }}: {{ remainingTimeStr }}
                </el-tag>
              </div>
            </div>
          </template>
          <div class="exam-description">
            <p>{{ exam.description }}</p>
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>题目列表</span>
            </div>
          </template>
          <el-table :data="problemStatus" v-loading="statusLoading" stripe style="width: 100%">
            <el-table-column prop="display_id" label="#" width="80" align="center" />
            <el-table-column label="题目名称" min-width="200">
              <template #default="scope">
                <el-link type="primary" :underline="false" @click="goToProblem(scope.row.problem_id)">
                  {{ scope.row.title }}
                </el-link>
              </template>
            </el-table-column>
            <el-table-column label="分值" width="120" align="center">
              <template #default="scope">
                {{ scope.row.current_score }} / {{ scope.row.max_score }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="150" align="center">
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)" size="small">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" align="center">
              <template #default="scope">
                <el-button type="primary" size="small" @click="goToProblem(scope.row.problem_id)">
                  {{ scope.row.status === 'Not Attempted' ? '开始作答' : '继续作答' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- Right: Sidebar Info -->
      <el-col :span="6">
        <el-card shadow="never" class="mb-4">
          <template #header>
            <div class="card-header">
              <span>考试信息</span>
            </div>
          </template>
          <div class="info-item">
            <span class="label">当前总分:</span>
            <span class="value total-score">{{ totalCurrentScore }} / {{ totalMaxScore }}</span>
          </div>
          <div class="info-item">
            <span class="label">开始时间:</span>
            <span class="value">{{ formatTime(exam.start_time) }}</span>
          </div>
          <div class="info-item">
            <span class="label">结束时间:</span>
            <span class="value">{{ formatTime(exam.end_time) }}</span>
          </div>
          <div class="info-item">
            <span class="label">题目数量:</span>
            <span class="value">{{ exam.problems?.length || 0 }}</span>
          </div>
          <el-button type="info" plain style="width: 100%; margin-top: 10px" @click="fetchStatus">
            刷新状态
          </el-button>
          <el-button type="danger" plain style="width: 100%; margin-top: 10px" @click="handleExitExam">
            退出考试
          </el-button>
        </el-card>

        <el-alert
          title="考试注意事项"
          type="warning"
          :closable="false"
          show-icon
        >
          <p>1. 请在规定时间内完成作答并提交。</p>
          <p>2. 考试期间请勿频繁刷新页面。</p>
          <p>3. 提交代码后请及时查看评测状态。</p>
        </el-alert>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getExamDetail, getMyExamStatus, exitExam } from '@/api/exam'
import { ElMessage, ElMessageBox } from 'element-plus'
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
    return { label: '距离开始', type: 'info' }
  } else if (now.isBefore(end)) {
    return { label: '剩余时间', type: 'danger' }
  } else {
    return { label: '已结束', type: 'info' }
  }
})

const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

const goToProblem = (problemId) => {
  router.push({
    path: `/problem/${problemId}`,
    query: { exam_id: examId }
  })
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
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.exam-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.exam-title {
  margin: 0;
  font-size: 24px;
}

.timer-tag {
  font-size: 18px;
  padding: 10px 20px;
  height: auto;
  font-family: monospace;
}

.exam-description {
  color: #606266;
  line-height: 1.6;
}

.mb-4 {
  margin-bottom: 20px;
}

.info-item {
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.info-item .label {
  color: #909399;
}

.info-item .value {
  color: #303133;
  font-weight: 500;
}

.total-score {
  color: #409eff !important;
  font-size: 16px;
}
</style>
