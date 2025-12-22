<template>
  <div class="problem-list-container">
    <el-card shadow="never">
      <div class="filter-container">
        <el-input
          v-model="searchQuery"
          placeholder="Search problems..."
          style="width: 300px"
          class="filter-item"
          clearable
        >
          <template #append>
            <el-button :icon="Search" />
          </template>
        </el-input>
        <el-select v-model="difficultyFilter" placeholder="Difficulty" clearable style="width: 120px; margin-left: 10px">
          <el-option label="Easy" value="Easy" />
          <el-option label="Medium" value="Medium" />
          <el-option label="Hard" value="Hard" />
        </el-select>
      </div>

      <el-table
        v-loading="loading"
        :data="paginatedProblems"
        style="width: 100%"
        stripe
      >
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="title" label="Title" min-width="200">
          <template #default="scope">
            <el-link type="primary" :underline="false" @click="$router.push(`/problem/${scope.row.id}`)">
              {{ scope.row.title }}
            </el-link>
            <el-tag v-if="scope.row.type" size="small" type="info" class="ml-2">{{ scope.row.type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Tags" min-width="150">
          <template #default>
            <el-tag size="small" effect="plain" class="mr-1">Math</el-tag> <!-- Mock tag -->
          </template>
        </el-table-column>
        <el-table-column label="Difficulty" width="100" align="center">
          <template #default>
            <el-tag type="success" size="small">Easy</el-tag> <!-- Mock difficulty -->
          </template>
        </el-table-column>
        <el-table-column label="Acceptance" width="100" align="center">
          <template #default>
            <span>65%</span> <!-- Mock acceptance -->
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
import { Search } from '@element-plus/icons-vue'
import { getProblemList } from '@/api/problem'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const allProblems = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const difficultyFilter = ref('')

// Filter problems based on search query
const filteredProblems = computed(() => {
  let result = allProblems.value
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p =>
      (p.title && p.title.toLowerCase().includes(query)) ||
      (p.id && String(p.id).includes(query))
    )
  }
  // Note: Difficulty filter is mocked in UI, so we can't really filter by it unless data has it
  // If data has difficulty, uncomment below:
  // if (difficultyFilter.value) {
  //   result = result.filter(p => p.difficulty === difficultyFilter.value)
  // }
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
  // If current page is out of bounds, reset to 1
  if (currentPage.value > Math.ceil(total.value / pageSize.value)) {
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
    ElMessage.error('Failed to load problems')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  // Search is handled by computed property, just ensure we are on page 1
  currentPage.value = 1
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
  /* Padding handled by layout */
}

.filter-container {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.ml-2 {
  margin-left: 8px;
}

.mr-1 {
  margin-right: 4px;
}
</style>
