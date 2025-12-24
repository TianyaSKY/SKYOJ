<template>
  <div class="exam-admin-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h2>考试管理</h2>
          <el-button type="primary" :icon="Plus" @click="handleCreate">新增考试</el-button>
        </div>
      </template>

      <el-table :data="exams" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="考试名称" min-width="200" />
        <el-table-column prop="start_time" label="开始时间" width="180" />
        <el-table-column prop="end_time" label="结束时间" width="180" />
        <el-table-column label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getExamStatus(scope.row).type">{{ getExamStatus(scope.row).label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="是否可见" width="100" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.is_visible ? 'success' : 'info'">
              {{ scope.row.is_visible ? '可见' : '隐藏' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" type="success" :icon="Monitor" @click="$router.push({ name: 'exam-monitor', params: { id: scope.row.id } })">监控</el-button>
            <el-button size="small" :icon="Edit" @click="handleEdit(scope.row)">编辑</el-button>
            <el-popconfirm
              title="确定要删除这场考试吗？"
              @confirm="handleDelete(scope.row.id)"
            >
              <template #reference>
                <el-button size="small" type="danger" :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Edit/Create Dialog -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="800px" @close="resetForm">
      <el-form :model="form" label-position="top" ref="formRef" v-loading="dialogLoading">
        <el-form-item label="考试名称" prop="title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="考试描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="开始时间" prop="start_time">
              <el-date-picker
                v-model="form.start_time"
                type="datetime"
                placeholder="选择开始时间"
                style="width: 100%"
                value-format="YYYY-MM-DD HH:mm:ss"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间" prop="end_time">
              <el-date-picker
                v-model="form.end_time"
                type="datetime"
                placeholder="选择结束时间"
                style="width: 100%"
                value-format="YYYY-MM-DD HH:mm:ss"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="考试密码 (可选)" prop="password">
              <el-input v-model="form.password" placeholder="留空则无需密码" show-password />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="对学生可见" prop="is_visible">
              <el-switch v-model="form.is_visible" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="题目选择">
          <div class="problem-selector">
            <div class="selector-header">
              <el-input
                v-model="problemSearchQuery"
                placeholder="搜索题目..."
                style="width: 200px"
                size="small"
                clearable
              />
            </div>
            <el-transfer
              v-model="selectedProblemIds"
              :data="allProblems"
              :titles="['可选题目', '已选题目']"
              :button-texts="['移除', '添加']"
              :props="{
                key: 'id',
                label: 'label'
              }"
              filterable
              :filter-method="filterMethod"
              filter-placeholder="输入关键词搜索"
            >
              <template #default="{ option }">
                <span>{{ option.id }} - {{ option.title }}</span>
              </template>
            </el-transfer>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { getExamList, createExam, updateExam, deleteExam, getExamDetail, addExamProblem, removeExamProblem } from '@/api/exam'
import { getProblemList } from '@/api/problem'
import { ElMessage } from 'element-plus'
import { Plus, Edit, Delete, Monitor } from '@element-plus/icons-vue'

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
const originalProblemIds = ref([]) // To track changes
const problemSearchQuery = ref('')

const form = ref({
  title: '',
  description: '',
  start_time: '',
  end_time: '',
  password: '',
  is_visible: true, // Default to visible
  problem_ids: '' // Will be updated from selectedProblemIds before submit
})

const dialogTitle = computed(() => (isEdit.value ? '编辑考试' : '新增考试'))

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
  const now = new Date()
  const start = new Date(exam.start_time)
  const end = new Date(exam.end_time)

  if (now < start) return { label: '未开始', type: 'info' }
  if (now > end) return { label: '已结束', type: 'danger' }
  return { label: '进行中', type: 'success' }
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
    form.value = { ...detail }

    // Parse problem_ids to selectedProblemIds array
    if (detail.problems && Array.isArray(detail.problems)) {
      selectedProblemIds.value = detail.problems.map(p => p.problem_id || p.id)
    } else if (form.value.problem_ids) {
      if (typeof form.value.problem_ids === 'string') {
        selectedProblemIds.value = form.value.problem_ids.split(',').map(id => Number(id.trim())).filter(id => !isNaN(id))
      }
    } else {
      selectedProblemIds.value = []
    }

    // Store original IDs to calculate diff later
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
    fetchExams() // Refresh list
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const handleSubmit = async () => {
  submitting.value = true
  try {
    // 1. Update basic exam info
    form.value.problem_ids = selectedProblemIds.value.join(',')

    let examId = currentExamId.value

    if (isEdit.value) {
      await updateExam(examId, form.value)

      // 2. Handle Problem Changes for Edit Mode
      const currentIds = new Set(selectedProblemIds.value)
      const originalIds = new Set(originalProblemIds.value)

      const toAdd = [...currentIds].filter(id => !originalIds.has(id))
      const toRemove = [...originalIds].filter(id => !currentIds.has(id))

      const promises = []

      for (const pid of toAdd) {
        promises.push(addExamProblem(examId, { problem_id: pid, score: 100 }))
      }

      for (const pid of toRemove) {
        promises.push(removeExamProblem(examId, pid))
      }

      await Promise.all(promises)

      ElMessage.success('考试及题目更新成功')
    } else {
      const res = await createExam(form.value)
      ElMessage.success('考试创建成功')
    }

    dialogVisible.value = false
    fetchExams() // Refresh list
  } catch (error) {
    console.error(error)
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
  max-width: 1200px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.problem-selector {
  width: 100%;
}
.selector-header {
  margin-bottom: 10px;
}
/* Adjust transfer panel width */
:deep(.el-transfer-panel) {
  width: 300px;
}
</style>
