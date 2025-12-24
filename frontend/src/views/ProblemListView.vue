<template>
  <div class="problem-list-container">
    <div class="list-header">
      <h1 class="page-title">题目列表</h1>
      <p class="page-desc">探索各种类型的编程挑战，提升你的技能。</p>
    </div>

    <el-card shadow="never" class="table-card">
      <div class="filter-container">
        <el-input
          v-model="searchQuery"
          placeholder="搜索题目名称或 ID..."
          style="width: 350px"
          class="search-input"
          clearable
          :prefix-icon="Search"
        />
        <div class="filter-group">
          <el-select v-model="typeFilter" placeholder="题目类型" clearable style="width: 140px">
            <el-option label="ACM" value="acm" />
            <el-option label="Kaggle" value="kaggle" />
            <el-option label="OOP" value="oop" />
          </el-select>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="paginatedProblems"
        style="width: 100%"
        class="problem-table"
        :header-cell-style="{ background: '#f8f9fa', color: '#606266', fontWeight: 'bold' }"
      >
        <el-table-column prop="id" label="ID" width="100" align="center">
          <template #default="scope">
            <span class="problem-id">#{{ scope.row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="title" label="题目名称" min-width="250">
          <template #default="scope">
            <div class="title-cell">
              <el-link
                type="primary"
                :underline="false"
                class="problem-link"
                @click="$router.push(`/problem/${scope.row.id}`)"
              >
                {{ scope.row.title }}
              </el-link>
              <el-tag
                v-if="scope.row.type"
                size="small"
                :type="getTypeTag(scope.row.type)"
                effect="light"
                class="type-tag"
              >
                {{ scope.row.type.toUpperCase() }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="允许语言" min-width="180">
          <template #default="scope">
            <div class="language-tags">
              <el-tag
                v-for="lang in getLanguages(scope.row.language)"
                :key="lang"
                size="small"
                effect="plain"
                class="lang-tag"
              >
                {{ capitalize(lang) }}
              </el-tag>
              <span v-if="!scope.row.language" class="text-secondary">All</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="限制" width="200">
          <template #default="scope">
            <div class="limit-info">
              <span title="时间限制"><el-icon><Timer /></el-icon> {{ scope.row.time_limit }}ms</span>
              <span title="内存限制"><el-icon><Monitor /></el-icon> {{ scope.row.memory_limit }}MB</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" align="center">
          <template #default="scope">
            <el-button
              type="primary"
              plain
              size="small"
              round
              @click="$router.push(`/problem/${scope.row.id}`)"
            >
              去挑战
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { Search, Timer, Monitor } from '@element-plus/icons-vue'
import { getProblemList } from '@/api/problem'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const allProblems = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const typeFilter = ref('')

const capitalize = (str) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

const getLanguages = (langStr) => {
  if (!langStr) return []
  return langStr.split(',').map(s => s.trim()).filter(s => s)
}

const getTypeTag = (type) => {
  const map = {
    'acm': 'primary',
    'kaggle': 'success',
    'oop': 'warning'
  }
  return map[type.toLowerCase()] || 'info'
}

// Filter problems based on search query and type
const filteredProblems = computed(() => {
  let result = allProblems.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p =>
      (p.title && p.title.toLowerCase().includes(query)) ||
      (p.id && String(p.id).includes(query))
    )
  }

  if (typeFilter.value) {
    result = result.filter(p => p.type && p.type.toLowerCase() === typeFilter.value.toLowerCase())
  }

  return result
})

// Paginate the filtered results
const paginatedProblems = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredProblems.value.slice(start, end)
})

// Update total when filter changes
watch(filteredProblems, (newVal) => {
  total.value = newVal.length
  if (currentPage.value > Math.ceil(total.value / pageSize.value) && total.value > 0) {
    currentPage.value = 1
  }
})

const fetchProblems = async () => {
  loading.value = true
  try {
    const data = await getProblemList()
    allProblems.value = data
    total.value = data.length
  } catch (error) {
    console.error(error)
    ElMessage.error('获取题目列表失败')
  } finally {
    loading.value = false
  }
}

const handleSizeChange = (val) => {
  pageSize.value = val
}

const handleCurrentChange = (val) => {
  currentPage.value = val
}

onMounted(() => {
  fetchProblems()
})
</script>

<style scoped>
.problem-list-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 0;
}

.list-header {
  margin-bottom: 30px;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.page-desc {
  color: #888;
  font-size: 1.1rem;
}

.table-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.filter-container {
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 8px;
}

.problem-table {
  border-radius: 8px;
  overflow: hidden;
}

.problem-id {
  color: #909399;
  font-family: 'Courier New', Courier, monospace;
  font-weight: bold;
}

.title-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.problem-link {
  font-size: 1.05rem;
  font-weight: 600;
}

.type-tag {
  font-weight: bold;
  border-radius: 4px;
}

.language-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.lang-tag {
  border-radius: 4px;
  background-color: #f0f2f5;
  color: #606266;
  border: none;
}

.limit-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.85rem;
  color: #606266;
}

.limit-info span {
  display: flex;
  align-items: center;
  gap: 5px;
}

.limit-info .el-icon {
  color: #909399;
}

.pagination-container {
  margin-top: 30px;
  display: flex;
  justify-content: center;
}

.text-secondary {
  color: #909399;
  font-size: 0.9rem;
}

:deep(.el-table__row) {
  height: 70px;
}
</style>
