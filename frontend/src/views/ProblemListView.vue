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
          <el-select
            v-model="typeFilter"
            @change="handleTypeChange"
            clearable
            placeholder="题目类型"
            style="width: 140px"
          >
            <el-option label="ACM" value="acm" />
            <el-option label="Kaggle" value="kaggle" />
            <el-option label="OOP" value="oop" />
          </el-select>
          <el-select
            v-model="tagFilter"
            clearable
            filterable
            placeholder="知识点"
            style="width: 160px"
            @change="handleTagChange"
          >
            <el-option
              v-for="tag in allTags"
              :key="tag.id"
              :label="tag.name + (tag.category ? ' (' + tag.category + ')' : '')"
              :value="tag.id"
            />
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
              <span title="时间限制"
                ><el-icon><Timer /></el-icon> {{ scope.row.time_limit }}ms</span
              >
              <span title="内存限制"
                ><el-icon><Monitor /></el-icon> {{ scope.row.memory_limit }}MB</span
              >
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
          :current-page="currentPage"
          :page-size="pageSize"
          :disabled="loading || !!searchQuery"
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

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Monitor, Search, Timer } from '@element-plus/icons-vue'
import { getProblemList, searchProblems } from '@/api/problem'
import { ElMessage } from 'element-plus'
import { getTags } from '@/api/tag'
import type {
  ProblemListResponse,
  SearchProblemResponse,
  ProblemQuery,
  SearchQuery,
} from '@/types/problem'
import type { TagResponse } from '@/types/community'
import type { TagProps } from 'element-plus'

const loading = ref(false)
const problems = ref<ProblemListResponse[]>([])
const searchResults = ref<SearchProblemResponse[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const typeFilter = ref<'' | 'acm' | 'oop' | 'kaggle'>('')
const tagFilter = ref<number | ''>('')
const allTags = ref<TagResponse[]>([])
let requestVersion = 0
let disposed = false

const capitalize = (str: string | null | undefined) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

const getLanguages = (langStr: string | null | undefined) => {
  if (!langStr) return []
  return langStr
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s)
}

const getTypeTag = (type: string) => {
  const map: Record<string, TagProps['type']> = {
    acm: 'primary',
    kaggle: 'success',
    oop: 'warning',
  }
  return map[type.toLowerCase()] || 'info'
}

const handleSearch = async () => {
  if (disposed) return
  if (!searchQuery.value) {
    searchResults.value = []
    await fetchProblems()
    return
  }
  const version = ++requestVersion
  searchResults.value = []
  total.value = 0
  const query = searchQuery.value
  const tag = tagFilter.value
  const type = typeFilter.value
  const isCurrent = () =>
    !disposed &&
    version === requestVersion &&
    query === searchQuery.value &&
    tag === tagFilter.value &&
    type === typeFilter.value
  loading.value = true
  try {
    const params: SearchQuery = { query, top_k: 50 }
    if (tag) params.tag_id = tag
    if (type) params.problem_type = type
    const data = await searchProblems(params)
    if (!isCurrent()) return
    searchResults.value = data
    // 更新总数，使分页组件显示正确的搜索结果数量
    total.value = data.length
    currentPage.value = 1
  } catch (error) {
    if (isCurrent()) {
      console.error(error)
      ElMessage.error('搜索失败')
    }
  } finally {
    if (isCurrent()) loading.value = false
  }
}

// 类型和知识点过滤均由服务端在计数和分页前完成。
const filteredProblems = computed(() => (searchQuery.value ? searchResults.value : problems.value))

let debounceTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, (newVal) => {
  requestVersion += 1
  searchResults.value = []
  total.value = 0
  if (debounceTimer) clearTimeout(debounceTimer)
  if (newVal) {
    loading.value = true
    debounceTimer = setTimeout(() => {
      debounceTimer = null
      handleSearch()
    }, 500)
  } else {
    searchResults.value = []
    fetchProblems()
  }
})

const fetchProblems = async (page = currentPage.value, size = pageSize.value): Promise<void> => {
  if (disposed || searchQuery.value) return
  const version = ++requestVersion
  const tag = tagFilter.value,
    type = typeFilter.value
  const isCurrent = () =>
    !disposed &&
    version === requestVersion &&
    !searchQuery.value &&
    tag === tagFilter.value &&
    type === typeFilter.value
  loading.value = true
  try {
    const params: ProblemQuery = {
      page,
      page_size: size,
    }
    if (type) params.problem_type = type
    if (tag) {
      params.tag_id = tag
    }
    const res = await getProblemList(params)
    if (!isCurrent()) return
    const items = Array.isArray(res) ? res : res.problems
    const count = Array.isArray(res) ? items.length : res.total
    const lastPage = Math.max(1, Math.ceil(count / size))
    if (page > lastPage) return await fetchProblems(lastPage, size)
    problems.value = items
    total.value = count
    currentPage.value = page
    pageSize.value = size
  } catch (error) {
    if (isCurrent()) {
      console.error(error)
      ElMessage.error('获取题目列表失败')
    }
  } finally {
    if (isCurrent()) loading.value = false
  }
}

const fetchTags = async () => {
  try {
    const res = await getTags()
    if (!disposed) allTags.value = res || []
  } catch {
    // 标签加载失败不影响题目列表
  }
}

const handleTagChange = () => {
  problems.value = []
  total.value = 0
  currentPage.value = 1
  if (searchQuery.value) return handleSearch()
  return fetchProblems()
}

const handleTypeChange = () => {
  problems.value = []
  total.value = 0
  currentPage.value = 1
  if (searchQuery.value) return handleSearch()
  return fetchProblems()
}

const handleSizeChange = (val: number) => fetchProblems(1, val)
const handleCurrentChange = (val: number) => fetchProblems(val, pageSize.value)

onBeforeUnmount(() => {
  disposed = true
  requestVersion += 1
  if (debounceTimer !== null) clearTimeout(debounceTimer)
})

onMounted(() => {
  fetchTags()
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
