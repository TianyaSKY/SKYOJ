<template>
  <div class="exam-admin-container">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">考试管理中心</h2>
        <p class="page-subtitle">创建、编辑及监控所有在线考试</p>
      </div>
      <el-button :icon="Plus" size="large" type="primary" @click="handleCreate">
        创建新考试
      </el-button>
    </div>

    <el-card class="table-card" shadow="never">
      <el-table v-loading="loading" :data="exams" border stripe style="width: 100%">
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column label="考试名称" min-width="220">
          <template #default="scope">
            <div class="exam-title-cell">
              <span class="exam-name">{{ scope.row.title }}</span>
              <div class="exam-time-range">
                <el-icon><Calendar /></el-icon>
                {{ formatTimeShort(scope.row.start_time) }} ~ {{ formatTimeShort(scope.row.end_time) }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column align="center" label="状态" width="110">
          <template #default="scope">
            <el-tag :type="getExamStatus(scope.row).type" effect="dark" size="small">
              {{ getExamStatus(scope.row).label }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column align="center" label="可见性" width="90">
          <template #default="scope">
            <el-tooltip :content="scope.row.is_visible ? '学生可见' : '学生不可见'" placement="top">
              <el-icon :class="scope.row.is_visible ? 'visible-icon' : 'hidden-icon'">
                <View v-if="scope.row.is_visible" />
                <Hide v-else />
              </el-icon>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column align="center" label="统计数据" width="160">
          <template #default="scope">
            <div class="stats-cell">
              <el-tooltip content="题目总数" placement="top">
                <el-tag size="small" type="info" effect="plain">
                  题: {{ scope.row.problem_count || 0 }}
                </el-tag>
              </el-tooltip>
              <el-tooltip content="总提交次数" placement="top">
                <el-tag size="small" type="success" effect="plain">
                  交: {{ scope.row.submission_count || 0 }}
                </el-tag>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>

        <el-table-column align="center" fixed="right" label="管理操作" width="380">
          <template #default="scope">
            <div class="operation-buttons">
              <el-button :icon="Monitor" plain size="small" type="success"
                         @click="$router.push({ name: 'exam-monitor', params: { id: scope.row.id } })">
                监控
              </el-button>
              <el-button :icon="Download" plain size="small" type="warning" @click="handleExport(scope.row)">
                成绩
              </el-button>
              <el-button :icon="Edit" plain size="small" type="primary" @click="handleEdit(scope.row)">
                编辑
              </el-button>
              <el-divider direction="vertical" />
              <el-popconfirm
                  title="确定要删除这场考试吗？此操作不可恢复。"
                  @confirm="handleDelete(scope.row.id)"
              >
                <template #reference>
                  <el-button :icon="Delete" link size="small" type="danger">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Edit/Create Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="900px"
      class="exam-dialog"
      @close="resetForm"
    >
      <el-form ref="formRef" v-loading="dialogLoading" :model="form" label-position="top">
        <el-row :gutter="30">
          <!-- Left Side: Basic Info -->
          <el-col :span="10">
            <div class="form-section-title">基本信息</div>
            <el-form-item label="考试名称" prop="title" required>
              <el-input v-model="form.title" placeholder="请输入考试名称"/>
            </el-form-item>
            <el-form-item label="考试描述" prop="description">
              <el-input v-model="form.description" :rows="4" type="textarea" placeholder="考试规则、注意事项等..."/>
            </el-form-item>

            <div class="form-section-title mt-4">时间与安全</div>
            <el-form-item label="考试时间范围" required>
              <el-date-picker
                v-model="timeRange"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                value-format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                @change="handleTimeChange"
              />
            </el-form-item>

            <el-row :gutter="20">
              <el-col :span="14">
                <el-form-item label="考试密码" prop="password">
                  <el-input v-model="form.password" placeholder="留空则公开" show-password/>
                </el-form-item>
              </el-col>
              <el-col :span="10">
                <el-form-item label="学生可见">
                  <el-switch v-model="form.is_visible" active-text="可见" inactive-text="隐藏" inline-prompt />
                </el-form-item>
              </el-col>
            </el-row>
          </el-col>

          <!-- Right Side: Problem Selection -->
          <el-col :span="14">
            <div class="form-section-title">题目配置</div>
            <div class="problem-selector-container">
              <div class="selector-header">
                <el-input
                    v-model="problemSearchQuery"
                    clearable
                    placeholder="搜索题目库..."
                    prefix-icon="Search"
                />
              </div>
              <el-transfer
                  v-model="selectedProblemIds"
                  :data="allProblems"
                  :filter-method="filterMethod"
                  :props="{ key: 'id', label: 'label' }"
                  :titles="['题库', '已选题目']"
                  filterable
              >
                <template #default="{ option }">
                  <div class="problem-option">
                    <span class="p-id">#{{ option.id }}</span>
                    <span class="p-title">{{ option.title }}</span>
                  </div>
                </template>
              </el-transfer>
              <div class="selector-footer">
                已选择 <span class="highlight">{{ selectedProblemIds.length }}</span> 道题目
              </div>
            </div>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button :loading="submitting" type="primary" size="large" @click="handleSubmit">
            {{ isEdit ? '保存修改' : '立即创建' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {computed, onMounted, ref} from 'vue'
import {
  addExamProblem,
  createExam,
  deleteExam,
  exportExamScores,
  getExamDetail,
  getExamList,
  removeExamProblem,
  updateExam
} from '@/api/exam'
import {getProblemList} from '@/api/problem'
import {ElMessage} from 'element-plus'
import {
  Calendar,
  Delete,
  Download,
  Edit,
  Hide,
  Monitor,
  Plus,
  Search,
  View
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const exams = ref([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const dialogLoading = ref(false)
const isEdit = ref(false)
const currentExamId = ref(null)

// Problem Selection
const allProblems = ref([])
const selectedProblemIds = ref([])
const originalProblemIds = ref([])
const problemSearchQuery = ref('')
const timeRange = ref([])

const form = ref({
  title: '',
  description: '',
  start_time: '',
  end_time: '',
  password: '',
  is_visible: true,
  problem_ids: ''
})

const dialogTitle = computed(() => (isEdit.value ? '编辑考试配置' : '创建新考试'))

const fetchExams = async () => {
  loading.value = true
  try {
    exams.value = await getExamList()
  } catch (error) {
    ElMessage.error('获取考试列表失败')
  } finally {
    loading.value = false
  }
}

const fetchProblems = async () => {
  try {
    const data = await getProblemList()
    allProblems.value = data.map(p => ({
      id: p.id,
      title: p.title,
      label: `${p.id} - ${p.title}`,
      disabled: false
    }))
  } catch (error) {
    ElMessage.error('获取题目列表失败')
  }
}

const getExamStatus = (exam) => {
  const now = dayjs()
  const start = dayjs(exam.start_time)
  const end = dayjs(exam.end_time)

  if (now.isBefore(start)) return {label: '未开始', type: 'info'}
  if (now.isAfter(end)) return {label: '已结束', type: 'danger'}
  return {label: '进行中', type: 'success'}
}

const formatTimeShort = (time) => {
  return dayjs(time).format('MM-DD HH:mm')
}

const handleTimeChange = (val) => {
  if (val) {
    form.value.start_time = val[0]
    form.value.end_time = val[1]
  } else {
    form.value.start_time = ''
    form.value.end_time = ''
  }
}

const resetForm = () => {
  form.value = {
    title: '',
    description: '',
    start_time: '',
    end_time: '',
    password: '',
    is_visible: true,
    problem_ids: ''
  }
  timeRange.value = []
  selectedProblemIds.value = []
  originalProblemIds.value = []
  currentExamId.value = null
}

const handleCreate = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

const handleEdit = async (row) => {
  isEdit.value = true
  currentExamId.value = row.id
  dialogVisible.value = true
  dialogLoading.value = true

  try {
    const detail = await getExamDetail(row.id)
    form.value = {...detail}
    timeRange.value = [detail.start_time, detail.end_time]

    if (detail.problems && Array.isArray(detail.problems)) {
      selectedProblemIds.value = detail.problems.map(p => p.problem_id || p.id)
    } else {
      selectedProblemIds.value = []
    }
    originalProblemIds.value = [...selectedProblemIds.value]
  } catch (error) {
    ElMessage.error('获取考试详情失败')
    dialogVisible.value = false
  } finally {
    dialogLoading.value = false
  }
}

const handleDelete = async (id) => {
  try {
    await deleteExam(id)
    ElMessage.success('删除成功')
    fetchExams()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const handleExport = async (row) => {
  try {
    const blob = await exportExamScores(row.id)
    const url = window.URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `成绩单_${row.title}_${dayjs().format('YYYYMMDD')}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('成绩单导出成功')
  } catch (error) {
    ElMessage.error('导出成绩失败')
  }
}

const handleSubmit = async () => {
  if (!form.value.title || !form.value.start_time) {
    ElMessage.warning('请填写必填项')
    return
  }

  submitting.value = true
  try {
    form.value.problem_ids = selectedProblemIds.value.join(',')
    let examId = currentExamId.value

    if (isEdit.value) {
      await updateExam(examId, form.value)
      const currentIds = new Set(selectedProblemIds.value)
      const originalIds = new Set(originalProblemIds.value)
      const toAdd = [...currentIds].filter(id => !originalIds.has(id))
      const toRemove = [...originalIds].filter(id => !currentIds.has(id))
      const promises = []
      for (const pid of toAdd) {
        promises.push(addExamProblem(examId, {problem_id: pid, score: 100}))
      }
      for (const pid of toRemove) {
        promises.push(removeExamProblem(examId, pid))
      }
      await Promise.all(promises)
      ElMessage.success('更新成功')
    } else {
      await createExam(form.value)
      ElMessage.success('创建成功')
    }

    dialogVisible.value = false
    fetchExams()
  } catch (error) {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

const filterMethod = (query, item) => {
  return item.label.toLowerCase().includes(query.toLowerCase())
}

onMounted(() => {
  fetchExams()
  fetchProblems()
})
</script>

<style scoped>
.exam-admin-container {
  max-width: 1300px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
}

.page-subtitle {
  margin: 4px 0 0 0;
  color: #666;
  font-size: 14px;
}

.table-card {
  border-radius: 8px;
}

/* Table Styling */
.exam-title-cell {
  display: flex;
  flex-direction: column;
}

.exam-name {
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.exam-time-range {
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 4px;
}

.visible-icon {
  color: #67c23a;
  font-size: 18px;
}

.hidden-icon {
  color: #909399;
  font-size: 18px;
}

.stats-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
}

.operation-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

/* Dialog Styling */
.form-section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-left: 10px;
  border-left: 4px solid #409eff;
}

.mt-4 {
  margin-top: 24px;
}

.problem-selector-container {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  background: #fcfcfc;
}

.selector-header {
  margin-bottom: 16px;
}

.problem-option {
  display: flex;
  gap: 8px;
  font-size: 13px;
}

.p-id {
  color: #909399;
  font-family: monospace;
}

.selector-footer {
  margin-top: 16px;
  text-align: right;
  font-size: 13px;
  color: #606266;
}

.highlight {
  color: #409eff;
  font-weight: bold;
  font-size: 15px;
}

:deep(.el-transfer-panel) {
  width: 240px;
  height: 400px;
}

:deep(.el-transfer-panel__list) {
  height: 320px;
}

.dialog-footer {
  padding-top: 20px;
  border-top: 1px solid #f0f2f5;
}
</style>
