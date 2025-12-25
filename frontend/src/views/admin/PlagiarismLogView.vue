<template>
  <div class="plagiarism-log-container">
    <el-page-header class="mb-4" @back="$router.back()">
      <template #content>
        <span class="text-large font-600 mr-3"> 查重日志管理 </span>
      </template>
      <template #extra>
        <div class="flex items-center">
          <el-button :icon="Refresh" :loading="loading" circle @click="fetchLogs"/>
        </div>
      </template>
    </el-page-header>

    <el-card shadow="never" class="mb-4">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="题目 ID">
          <el-input v-model="filterForm.problem_id" placeholder="题目 ID" clearable style="width: 120px" @change="handleFilter"/>
        </el-form-item>
        <el-form-item label="考试 ID">
          <el-input v-model="filterForm.exam_id" placeholder="考试 ID" clearable style="width: 120px" @change="handleFilter"/>
        </el-form-item>
        <el-form-item label="最低相似度">
          <el-input-number v-model="filterForm.min_score" :min="0" :max="100" style="width: 130px" @change="handleFilter"/>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleFilter">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="logs" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" align="center"/>
        <el-table-column label="用户" min-width="150">
          <template #default="scope">
            <div class="user-info">
              <span class="username">{{ scope.row.username }}</span>
              <span class="user-id">ID: {{ scope.row.user_id }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="submission_id" label="提交 ID" width="100" align="center">
          <template #default="scope">
            <el-link type="primary" @click="$router.push({ name: 'submission-detail', params: { id: scope.row.submission_id } })">
              #{{ scope.row.submission_id }}
            </el-link>
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
        <el-table-column label="相似度" width="150" sortable prop="similarity_score">
          <template #default="scope">
            <el-progress
              :percentage="Math.round(scope.row.similarity_score * 100)"
              :status="getSimilarityStatus(scope.row.similarity_score)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="target_submission_id" label="目标提交 ID" width="120" align="center">
          <template #default="scope">
            <el-link type="info" @click="$router.push({ name: 'submission-detail', params: { id: scope.row.target_submission_id } })">
              #{{ scope.row.target_submission_id }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="查重时间" width="180">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="150" align="center">
          <template #default="scope">
            <el-button link type="primary" @click="viewDetail(scope.row)">详情</el-button>
            <el-popconfirm title="确定要删除这条日志吗？" @confirm="handleDelete(scope.row.id)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container mt-4">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="pagination.total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="查重详情" width="600px">
      <div v-if="currentLog" class="plagiarism-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="查重记录 ID">{{ currentLog.id }}</el-descriptions-item>
          <el-descriptions-item label="用户">{{ currentLog.username }} (ID: {{ currentLog.user_id }})</el-descriptions-item>
          <el-descriptions-item label="提交 ID">
            <el-link type="primary" @click="$router.push({ name: 'submission-detail', params: { id: currentLog.submission_id } })">
              #{{ currentLog.submission_id }}
            </el-link>
          </el-descriptions-item>
          <el-descriptions-item label="题目 ID">{{ currentLog.problem_id }}</el-descriptions-item>
          <el-descriptions-item label="考试 ID">{{ currentLog.exam_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="目标提交 ID">
            <el-link type="info" @click="$router.push({ name: 'submission-detail', params: { id: currentLog.target_submission_id } })">
              #{{ currentLog.target_submission_id }}
            </el-link>
          </el-descriptions-item>
          <el-descriptions-item label="相似度得分">
            <el-tag :type="getSimilarityTagType(currentLog.similarity_score)">
              {{ (currentLog.similarity_score * 100).toFixed(2) }}%
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="查重时间">{{ formatTime(currentLog.created_at) }}</el-descriptions-item>
        </el-descriptions>

        <div class="mt-6 flex justify-center">
          <el-button type="primary" @click="compareSubmissions">对比代码</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getPlagiarismLogs, deletePlagiarismLog } from '@/api/plagiarism'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const logs = ref([])

const STORAGE_KEY = 'skyoj_plagiarism_filter'

// 从 localStorage 加载初始值
const savedFilter = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')

const filterForm = reactive({
  problem_id: savedFilter.problem_id || '',
  exam_id: savedFilter.exam_id || '',
  min_score: savedFilter.min_score !== undefined ? savedFilter.min_score : 70
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// 监听表单变化并保存到 localStorage
watch(filterForm, (newVal) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(newVal))
}, { deep: true })

const detailVisible = ref(false)
const currentLog = ref(null)

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = {
      problem_id: filterForm.problem_id || undefined,
      exam_id: filterForm.exam_id || undefined,
      min_score: filterForm.min_score / 100,
      page: pagination.page,
      page_size: pagination.page_size
    }
    const res = await getPlagiarismLogs(params)

    // 适配新的分页返回格式
    if (res && res.data) {
      logs.value = res.data
      pagination.total = res.total
    } else if (Array.isArray(res)) {
      logs.value = res
      pagination.total = res.length
    }
  } catch (error) {
    ElMessage.error('获取查重日志失败')
  } finally {
    loading.value = false
  }
}

const handleFilter = () => {
  pagination.page = 1
  fetchLogs()
}

const resetFilter = () => {
  filterForm.problem_id = ''
  filterForm.exam_id = ''
  filterForm.min_score = 70
  localStorage.removeItem(STORAGE_KEY)
  handleFilter()
}

const handleSizeChange = (val) => {
  pagination.page_size = val
  pagination.page = 1
  fetchLogs()
}

const handleCurrentChange = (val) => {
  pagination.page = val
  fetchLogs()
}

const handleDelete = async (id) => {
  try {
    await deletePlagiarismLog(id)
    ElMessage.success('删除成功')
    fetchLogs()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const viewDetail = (log) => {
  currentLog.value = log
  detailVisible.value = true
}

const compareSubmissions = () => {
  if (!currentLog.value) return
  router.push({
    name: 'code-compare',
    query: {
      id1: currentLog.value.submission_id,
      id2: currentLog.value.target_submission_id,
      similarity: currentLog.value.similarity_score
    }
  })
}

const getSimilarityStatus = (similarity) => {
  if (similarity >= 0.9) return 'exception'
  if (similarity >= 0.7) return 'warning'
  return 'success'
}

const getSimilarityTagType = (similarity) => {
  if (similarity >= 0.9) return 'danger'
  if (similarity >= 0.7) return 'warning'
  return 'success'
}

const formatTime = (time) => time ? new Date(time).toLocaleString() : ''

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.plagiarism-log-container {
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

.mt-6 {
  margin-top: 24px;
}

.plagiarism-detail {
  padding: 10px;
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

.text-gray {
  color: #909399;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
}

.flex {
  display: flex;
}

.justify-center {
  justify-content: center;
}
</style>
