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
                <el-button class="enter-btn" type="primary"
                           :loading="entering && currentExamId === exam.id && !submittingPassword"
                           :disabled="entering || passwordDialogVisible">进入考试</el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-empty v-if="!loading && filteredExams.length === 0" description="暂无进行中或未开始的考试"/>
    </div>

    <!-- Password Dialog -->
    <el-dialog v-model="passwordDialogVisible" title="请输入考试密码" width="350px"
               :before-close="handlePasswordClose" :show-close="!submittingPassword"
               :close-on-click-modal="!submittingPassword" :close-on-press-escape="!submittingPassword">
      <el-input
          v-model="passwordInput"
          placeholder="请输入密码"
          show-password
          type="password"
          @keyup.enter="handlePasswordSubmit"
      />
      <template #footer>
        <el-button :disabled="submittingPassword" @click="passwordDialogVisible = false">取消</el-button>
        <el-button :loading="submittingPassword" :disabled="submittingPassword" type="primary" @click="handlePasswordSubmit">
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import {computed, onMounted, onUnmounted, ref} from 'vue'
import type { ExamListResponse } from '@/types/exam'
import { isRecord } from '@/types/http'
import { errorMessage } from '@/utils/error'
import {enterExam, getExamList} from '@/api/exam'
import {useUserStore} from '@/stores/user'
import {ElMessage} from 'element-plus'
import {useRouter} from 'vue-router'
import {Calendar, Clock, Timer} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { parseServerDate } from '@/utils/date'
import { getExamTiming } from '@/utils/examTime'
import { useNow } from '@/composables/useNow'
import duration from 'dayjs/plugin/duration'

dayjs.extend(duration)

const now = useNow()
const loading = ref(false)
const allExams = ref<ExamListResponse[]>([])
const router = useRouter()
const userStore = useUserStore()

// 进入请求串行执行，密码弹窗在请求完成前保持所属考试不变。
const entering = ref(false)
let disposed = false
const passwordDialogVisible = ref(false)
const submittingPassword = ref(false)
const passwordInput = ref('')
const currentExamId = ref<number | null>(null)

const fetchExams = async () => {
  loading.value = true
  try {
    const data = await getExamList()
    if (!disposed) allExams.value = data
  } catch (error) {
    if (!disposed) ElMessage.error('获取考试列表失败')
  } finally {
    if (!disposed) loading.value = false
  }
}

const getExamStatus = (exam: ExamListResponse) => {
  const phase = getExamTiming(exam, now.value).phase
  return ({
    upcoming: {text: '未开始', type: 'info'},
    ongoing: {text: '进行中', type: 'success'},
    ended: {text: '已结束', type: 'danger'},
    unknown: {text: '时间无效', type: 'info'},
  } as const)[phase]
}

const filteredExams = computed(() => {
  if (!allExams.value) return []
  return allExams.value.filter(exam => {
    const status = getExamStatus(exam).text
    return status === '进行中' || status === '未开始'
  })
})

const formatTime = (time: unknown) => {
  const date = parseServerDate(time)
  return date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'
}

const getDuration = (start: unknown, end: unknown) => {
  const diff = (parseServerDate(end)?.getTime() ?? 0) - (parseServerDate(start)?.getTime() ?? 0)
  const dur = dayjs.duration(diff)
  const hours = Math.floor(dur.asHours())
  const minutes = dur.minutes()
  return `${hours}小时${minutes}分钟`
}

const handlePasswordClose = (done: () => void) => {
  if (!submittingPassword.value) done()
}

const requestEntry = async (examId: number, password: string, passwordAttempt: boolean) => {
  entering.value = true
  submittingPassword.value = passwordAttempt
  let expectedToken = localStorage.getItem('token')
  const isCurrentSession = () => !disposed && localStorage.getItem('token') === expectedToken
  try {
    const res = await enterExam(examId, password)
    if (!isCurrentSession()) return
    if (res.token) {
      userStore.setToken(res.token)
      expectedToken = res.token
    }
    passwordDialogVisible.value = false
    await router.push(`/exam/${examId}`)
  } catch (error) {
    if (!isCurrentSession()) return
    const response = isRecord(error) && isRecord(error.response) ? error.response : null
    const payload = response && isRecord(response.data) ? response.data : null
    const message = payload?.error || errorMessage(error, '')
    if (!passwordAttempt && response?.status === 403 && message === '考试密码错误') {
      passwordInput.value = ''
      passwordDialogVisible.value = true
    } else {
      ElMessage.error(typeof message === 'string' && message ? message : '进入考试失败，请稍后重试')
    }
  } finally {
    if (!disposed) {
      entering.value = false
      submittingPassword.value = false
    }
  }
}

const handleEnterExam = async (exam: ExamListResponse) => {
  if (disposed || entering.value || passwordDialogVisible.value) return
  const phase = getExamTiming(exam, Date.now()).phase
  if (phase !== 'ongoing') {
    ElMessage.warning(phase === 'upcoming' ? '考试尚未开始' : '考试已结束或时间无效')
    return
  }
  currentExamId.value = exam.id
  await requestEntry(exam.id, '', false)
}

const handlePasswordSubmit = async () => {
  if (disposed || entering.value || !passwordDialogVisible.value || currentExamId.value == null) return
  if (!passwordInput.value) {
    ElMessage.warning('请输入密码')
    return
  }
  await requestEntry(currentExamId.value, passwordInput.value, true)
}

onUnmounted(() => { disposed = true })

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
