<template>
  <div class="problem-list-container">
    <div class="list-header">
      <h1 class="page-title">题目列表</h1>
      <p class="page-desc">探索各种类型的编程挑战，提升你的技能。</p>
    </div>

    <el-card class="table-card" shadow="never">
      <div class="filter-container">
        <el-input
            v-model="searchQuery"
            :prefix-icon="Search"
            class="search-input"
            clearable
            placeholder="搜索题目名称或内容..."
            style="width: 350px"
        />
        <div class="filter-group">
          <el-switch
              v-model="isSemanticSearch"
              active-text="语义搜索"
              style="margin-right: 15px"
          />
          <el-select v-model="typeFilter" clearable placeholder="题目类型" style="width: 140px">
            <el-option label="ACM" value="acm"/>
            <el-option label="Kaggle" value="kaggle"/>
            <el-option label="OOP" value="oop"/>
          </el-select>
        </div>
      </div>

      <el-table
          v-loading="loading"
          :data="filteredProblems"
          :header-cell-style="{ background: '#f8f9fa', color: '#606266', fontWeight: 'bold' }"
          class="problem-table"
          style="width: 100%"
      >
        <el-table-column align="center" label="ID" prop="id" width="100">
          <template #default="scope">
            <span class="problem-id">#{{ scope.row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="题目名称" min-width="250" prop="title">
          <template #default="scope">
            <div class="title-cell">
              <el-link
                  :underline="false"
                  class="problem-link"
                  type="primary"
                  @click="$router.push(`/problem/${scope.row.id}`)"
              >
                {{ scope.row.title }}
              </el-link>
              <el-tag
                  v-if="scope.row.type"
                  :type="getTypeTag(scope.row.type)"
                  class="type-tag"
                  effect="light"
                  size="small"
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
                  class="lang-tag"
                  effect="plain"
                  size="small"
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
              <span title="时间限制"><el-icon><Timer/></el-icon> {{ scope.row.time_limit }}ms</span>
              <span title="内存限制"><el-icon><Monitor/></el-icon> {{ scope.row.memory_limit }}MB</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column align="center" label="操作" width="120">
          <template #default="scope">
            <el-button
                plain
                round
                size="small"
                type="primary"
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
            :disabled="!!searchQuery"
            :page-sizes="[10, 20, 50]"
            :total="total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import {computed, onMounted, ref, watch} from 'vue'
import {Monitor, Search, Timer} from '@element-plus/icons-vue'
import {getProblemList, searchProblems} from '@/api/problem'
import {ElMessage} from 'element-plus'

const loading = ref(false)
const problems = ref([])
const searchResults = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const typeFilter = ref('')
const isSemanticSearch = ref(false)

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

const handleSearch = async () => {
  if (!searchQuery.value) {
    searchResults.value = []
    fetchProblems()
    return
  }
  loading.value = true
  try {
    const data = await searchProblems({
      query: searchQuery.value,
      mode: isSemanticSearch.value ? 'semantic' : 'normal',
      top_k: 50
    })
    searchResults.value = data
    // 更新总数，使分页组件显示正确的搜索结果数量
    total.value = data.length
    currentPage.value = 1
  } catch (error) {
    console.error(error)
    ElMessage.error('搜索失败')
  } finally {
    loading.value = false
  }
}

// Filter problems based on search query and type
const filteredProblems = computed(() => {
  let result = searchQuery.value ? searchResults.value : problems.value

  if (typeFilter.value) {
    result = result.filter(p => p.type && p.type.toLowerCase() === typeFilter.value.toLowerCase())
  }

  return result
})

let debounceTimer = null
watch(searchQuery, (newVal) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  if (newVal) {
    loading.value = true
    debounceTimer = setTimeout(() => {
      handleSearch()
    }, 500)
  } else {
    searchResults.value = []
    fetchProblems()
    loading.value = false
  }
})

watch(isSemanticSearch, () => {
  if (searchQuery.value) {
    handleSearch()
  }
})

const fetchProblems = async () => {
  loading.value = true
  try {
    const res = await getProblemList({
      page: currentPage.value,
      page_size: pageSize.value
    })
    if (res.problems) {
      problems.value = res.problems
      total.value = res.total
    } else {
      problems.value = res
      total.value = res.length
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('获取题目列表失败')
  } finally {
    loading.value = false
  }
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchProblems()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchProblems()
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
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.filter-container {
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-group {
  display: flex;
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
