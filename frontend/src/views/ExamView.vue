<template>
  <div class="exam-container">
    <div class="exam-header">
      <h1>考试中心</h1>
      <p class="exam-info">查看所有进行中或未开始的考试，点击卡片进入考试</p>
    </div>

    <div v-loading="loading" class="exam-list">
      <el-row :gutter="20">
        <el-col
            v-for="exam in filteredExams"
            :key="exam.id"
            :lg="8"
            :md="12"
            :sm="12"
            :xs="24"
            class="exam-col"
        >
          <el-card
              :body-style="{ padding: '0px' }"
              class="exam-card"
              shadow="hover"
              @click="handleEnterExam(exam)"
          >
            <div :class="['status-banner', getExamStatus(exam).type]">
              {{ getExamStatus(exam).text }}
            </div>
            <div class="card-content">
              <h3 class="exam-title">{{ exam.title }}</h3>
              <p class="exam-desc">{{ exam.description || '暂无考试描述' }}</p>

              <div class="exam-meta">
                <div class="meta-item">
                  <el-icon>
                    <Calendar/>
                  </el-icon>
                  <span>开始: {{ formatTime(exam.start_time) }}</span>
                </div>
                <div class="meta-item">
                  <el-icon>
                    <Timer/>
                  </el-icon>
                  <span>结束: {{ formatTime(exam.end_time) }}</span>
                </div>
                <div class="meta-item duration">
                  <el-icon>
                    <Clock/>
                  </el-icon>
                  <span>时长: {{ getDuration(exam.start_time, exam.end_time) }}</span>
                </div>
              </div>

              <div class="card-footer">
                <el-button class="enter-btn" type="primary">进入考试</el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-empty v-if="!loading && filteredExams.length === 0" description="暂无进行中或未开始的考试"/>
    </div>

    <!-- Password Dialog -->
    <el-dialog v-model="passwordDialogVisible" title="请输入考试密码" width="350px">
      <el-input
          v-model="passwordInput"
          placeholder="请输入密码"
          show-password
          type="password"
          @keyup.enter="handlePasswordSubmit"
      />
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button :loading="submittingPassword" type="primary" @click="handlePasswordSubmit">
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {computed, onMounted, ref} from 'vue'
import {enterExam, getExamList} from '@/api/exam'
import {ElMessage} from 'element-plus'
import {useRouter} from 'vue-router'
import {Calendar, Clock, Timer} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import duration from 'dayjs/plugin/duration'

dayjs.extend(duration)

const loading = ref(false)
const allExams = ref([])
const router = useRouter()

// Password verification state
const passwordDialogVisible = ref(false)
const submittingPassword = ref(false)
const passwordInput = ref('')
const currentExamId = ref(null)

const fetchExams = async () => {
  loading.value = true
  try {
    const data = await getExamList()
    allExams.value = data
  } catch (error) {
    ElMessage.error('获取考试列表失败')
  } finally {
    loading.value = false
  }
}

const getExamStatus = (exam) => {
  const now = dayjs()
  const start = dayjs(exam.start_time)
  const end = dayjs(exam.end_time)

  if (now.isBefore(start)) {
    return {text: '未开始', type: 'info'}
  } else if (now.isAfter(end)) {
    return {text: '已结束', type: 'danger'}
  } else {
    return {text: '进行中', type: 'success'}
  }
}

const filteredExams = computed(() => {
  if (!allExams.value) return []
  return allExams.value.filter(exam => {
    const status = getExamStatus(exam).text
    return status === '进行中' || status === '未开始'
  })
})

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}

const getDuration = (start, end) => {
  const diff = dayjs(end).diff(dayjs(start))
  const dur = dayjs.duration(diff)
  const hours = Math.floor(dur.asHours())
  const minutes = dur.minutes()
  return `${hours}小时${minutes}分钟`
}

const handleEnterExam = async (exam) => {
  currentExamId.value = exam.id
  try {
    // Try to enter without password first
    const res = await enterExam(exam.id, '')
    // If successful, update token and navigate
    if (res.token) {
      localStorage.setItem('token', res.token)
    }
    router.push(`/exam/${exam.id}`)
  } catch (error) {
    if (error.response && error.response.status === 403) {
      // Password required or incorrect
      passwordInput.value = ''
      passwordDialogVisible.value = true
    } else {
      ElMessage.error('进入考试失败，请稍后重试')
    }
  }
}

const handlePasswordSubmit = async () => {
  if (!passwordInput.value) {
    ElMessage.warning('请输入密码')
    return
  }
  submittingPassword.value = true
  try {
    const res = await enterExam(currentExamId.value, passwordInput.value)
    if (res.token) {
      localStorage.setItem('token', res.token)
    }
    passwordDialogVisible.value = false
    router.push(`/exam/${currentExamId.value}`)
  } catch (error) {
    ElMessage.error('密码错误')
  } finally {
    submittingPassword.value = false
  }
}

onMounted(() => {
  fetchExams()
})
</script>

<style scoped>
.exam-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
}

.exam-header {
  text-align: center;
  margin-bottom: 40px;
}

.exam-header h1 {
  font-size: 32px;
  color: #303133;
  margin-bottom: 10px;
  font-weight: 600;
}

.exam-info {
  color: #909399;
  font-size: 16px;
}

.exam-list {
  min-height: 400px;
}

.exam-col {
  margin-bottom: 24px;
}

.exam-card {
  height: 100%;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid #ebeef5;
  position: relative;
  overflow: hidden;
}

.exam-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 20px 0 rgba(0, 0, 0, 0.1);
}

.status-banner {
  position: absolute;
  top: 12px;
  right: -30px;
  transform: rotate(45deg);
  width: 120px;
  text-align: center;
  font-size: 12px;
  font-weight: bold;
  padding: 2px 0;
  color: white;
  z-index: 1;
}

.status-banner.success {
  background-color: #67c23a;
}

.status-banner.info {
  background-color: #909399;
}

.status-banner.danger {
  background-color: #f56c6c;
}

.card-content {
  padding: 24px;
}

.exam-title {
  margin: 0 0 12px 0;
  font-size: 20px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.exam-desc {
  color: #606266;
  font-size: 14px;
  height: 40px;
  margin-bottom: 20px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.exam-meta {
  border-top: 1px solid #f0f2f5;
  padding-top: 16px;
  margin-bottom: 20px;
}

.meta-item {
  display: flex;
  align-items: center;
  color: #909399;
  font-size: 13px;
  margin-bottom: 8px;
}

.meta-item .el-icon {
  margin-right: 8px;
  font-size: 16px;
}

.duration {
  color: #409eff;
  font-weight: 500;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
}

.enter-btn {
  width: 100%;
}
</style>
