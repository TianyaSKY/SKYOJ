<template>
  <div class="exam-container">
    <div class="exam-header">
      <h1>在线考试</h1>
      <p class="exam-info">查看所有进行中或未开始的考试</p>
    </div>

    <el-card class="exam-content" shadow="never">
      <el-table
          v-loading="loading"
          :data="filteredExams"
          stripe
          style="width: 100%"
      >
        <el-table-column label="考试名称" min-width="200" prop="title">
          <template #default="scope">
            <el-link :underline="false" type="primary" @click="handleEnterExam(scope.row)">
              {{ scope.row.title }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column align="center" label="开始时间" prop="start_time" width="200"/>
        <el-table-column align="center" label="结束时间" prop="end_time" width="200"/>
        <el-table-column align="center" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="getExamStatus(scope.row).type" size="small">{{ getExamStatus(scope.row).text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column align="center" label="操作" width="120">
          <template #default="scope">
            <el-button size="small" type="primary" @click="handleEnterExam(scope.row)">进入考试</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

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
  const now = new Date()
  const start = new Date(exam.start_time)
  const end = new Date(exam.end_time)

  if (now < start) {
    return {text: '未开始', type: 'info'}
  } else if (now >= start && now <= end) {
    return {text: '进行中', type: 'success'}
  } else {
    return {text: '已结束', type: 'danger'}
  }
}

const filteredExams = computed(() => {
  if (!allExams.value) return []
  return allExams.value.filter(exam => {
    const status = getExamStatus(exam).text
    return status === '进行中' || status === '未开始'
  })
})

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
    if (error.response && error.response.status === 401) {
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
  max-width: 1000px;
  margin: 0 auto;
  padding-top: 40px;
}

.exam-header {
  text-align: center;
  margin-bottom: 40px;
}

.exam-header h1 {
  font-size: 32px;
  color: #303133;
  margin-bottom: 10px;
}

.exam-info {
  color: #909399;
  font-size: 16px;
}
</style>
