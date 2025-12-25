<template>
  <div class="submission-admin-container">
    <el-page-header class="mb-4" @back="$router.back()">
      <template #content>
        <span class="text-large font-600 mr-3"> 提交记录管理 </span>
      </template>
      <template #extra>
        <div class="flex items-center">
          <el-button :icon="Refresh" :loading="loading" circle @click="fetchSubmissions"/>
        </div>
      </template>
    </el-page-header>

    <el-card shadow="never" class="mb-4">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="题目 ID">
          <el-input v-model="filterForm.problem_id" placeholder="题目 ID" clearable style="width: 120px" @change="handleFilter"/>
        </el-form-item>
        <el-form-item label="用户 ID">
          <el-input v-model="filterForm.user_id" placeholder="用户 ID" clearable style="width: 120px" @change="handleFilter"/>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="filterForm.username" placeholder="用户名模糊搜索" clearable style="width: 150px" @change="handleFilter"/>
        </el-form-item>
        <el-form-item label="考试 ID">
          <el-input v-model="filterForm.exam_id" placeholder="考试 ID" clearable style="width: 120px" @change="handleFilter"/>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="选择状态" clearable style="width: 150px" @change="handleFilter">
            <el-option label="Accepted" value="Accepted" />
            <el-option label="Wrong Answer" value="Wrong Answer" />
            <el-option label="Time Limit Exceeded" value="Time Limit Exceeded" />
            <el-option label="Memory Limit Exceeded" value="Memory Limit Exceeded" />
            <el-option label="Runtime Error" value="Runtime Error" />
            <el-option label="Compilation Error" value="Compilation Error" />
            <el-option label="Pending" value="Pending" />
            <el-option label="Judging" value="Judging" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleFilter">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <div class="table-actions mb-4">
        <el-button type="success" :disabled="!selectedSubmissions.length" @click="handleBatchPlagiarism">
          对选中提交进行查重 ({{ selectedSubmissions.length }})
        </el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="submissions"
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" align="center"/>
        <el-table-column label="用户" min-width="150">
          <template #default="scope">
            <div class="user-info">
              <span class="username">{{ scope.row.username }}</span>
              <span class="user-id">ID: {{ scope.row.user_id }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="problem_id" label="题目 ID" width="100" align="center">
          <template #default="scope">
            <el-link type="primary" @click="$router.push({ name: 'problem-detail', params: { id: scope.row.problem_id } })">
              #{{ scope.row.problem_id }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="exam_id" label="考试 ID" width="100" align="center">
          <template #default="scope">
            <span v-if="scope.row.exam_id">#{{ scope.row.exam_id }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="150">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="分数" width="80" align="center">
          <template #default="scope">
            <span :class="getScoreClass(scope.row.score)">{{ scope.row.score }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="language" label="语言" width="100" align="center"/>
        <el-table-column prop="created_at" label="提交时间" width="180">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="120" align="center">
          <template #default="scope">
            <el-button link type="primary" @click="viewDetail(scope.row.id)">详情</el-button>
            <el-button link type="warning" @click="checkPlagiarism(scope.row.id)">查重</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container mt-4">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.per_page"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="pagination.total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getSubmissions } from '@/api/submission'
import { checkPlagiarismBatch } from '@/api/plagiarism'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const submissions = ref([])
const selectedSubmissions = ref([])

const STORAGE_KEY = 'skyoj_submission_filter'

// 从 localStorage 加载初始值
const savedFilter = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')

const filterForm = reactive({
  problem_id: savedFilter.problem_id || '',
  user_id: savedFilter.user_id || '',
  username: savedFilter.username || '',
  exam_id: savedFilter.exam_id || '',
  status: savedFilter.status || ''
})

const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0
})

// 监听表单变化并保存到 localStorage
watch(filterForm, (newVal) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(newVal))
}, { deep: true })

const fetchSubmissions = async () => {
  loading.value = true
  try {
    const params = {
      ...filterForm,
      page: pagination.page,
      per_page: pagination.per_page
    }
    // 移除空字符串参数
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null) delete params[key]
    })

    const res = await getSubmissions(params)

    if (res) {
      const list = res.items || res.submissions || res.data || (Array.isArray(res) ? res : [])
      const total = res.total !== undefined ? res.total : (Array.isArray(res) ? res.length : 0)

      submissions.value = list
      pagination.total = total
    } else {
      submissions.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('Fetch submissions error:', error)
    ElMessage.error('获取提交记录失败')
  } finally {
    loading.value = false
  }
}

const handleFilter = () => {
  pagination.page = 1
  fetchSubmissions()
}

const resetFilter = () => {
  Object.keys(filterForm).forEach(key => filterForm[key] = '')
  localStorage.removeItem(STORAGE_KEY)
  handleFilter()
}

const handleSizeChange = (val) => {
  pagination.per_page = val
  pagination.page = 1
  fetchSubmissions()
}

const handleCurrentChange = (val) => {
  pagination.page = val
  fetchSubmissions()
}

const handleSelectionChange = (val) => {
  selectedSubmissions.value = val
}

const viewDetail = (id) => {
  router.push({ name: 'submission-detail', params: { id } })
}

const checkPlagiarism = async (id) => {
  try {
    await ElMessageBox.confirm('确定要对该提交进行查重吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })

    await checkPlagiarismBatch({ submission_ids: [id] })
    ElMessage.success('查重任务已提交')
    router.push({ name: 'plagiarism-admin' })
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('提交查重任务失败')
    }
  }
}

const handleBatchPlagiarism = async () => {
  if (!selectedSubmissions.value.length) return

  try {
    await ElMessageBox.confirm(
      `确定要对选中的 ${selectedSubmissions.value.length} 条提交进行查重吗？`,
      '批量查重',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const ids = selectedSubmissions.value.map(s => s.id)
    await checkPlagiarismBatch({ submission_ids: ids })
    ElMessage.success('批量查重任务已提交')
    router.push({ name: 'plagiarism-admin' })
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('提交查重任务失败')
    }
  }
}

const getStatusType = (status) => {
  const map = {
    'Accepted': 'success',
    'Wrong Answer': 'danger',
    'Pending': 'info',
    'Judging': 'warning',
    'Compilation Error': 'info',
    'Runtime Error': 'danger',
    'Time Limit Exceeded': 'warning',
    'Memory Limit Exceeded': 'warning'
  }
  return map[status] || 'info'
}

const getScoreClass = (score) => {
  if (score === 100) return 'text-success'
  if (score > 0) return 'text-warning'
  return 'text-danger'
}

const formatTime = (time) => time ? new Date(time).toLocaleString() : ''

onMounted(() => {
  fetchSubmissions()
})
</script>

<style scoped>
.submission-admin-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.mb-4 {
  margin-bottom: 20px;
}

.mt-4 {
  margin-top: 20px;
}

.user-info {
  display: flex;
  flex-direction: column;
}

.username {
  font-weight: 600;
  color: #303133;
}

.user-id {
  font-size: 12px;
  color: #909399;
}

.text-success { color: #67C23A; }
.text-warning { color: #E6A23C; }
.text-danger { color: #F56C6C; }
.text-gray { color: #909399; }

.pagination-container {
  display: flex;
  justify-content: flex-end;
}
</style>
