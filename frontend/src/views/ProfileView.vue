<template>
  <div class="profile-container">
    <!-- User Info Card -->
    <el-card class="user-card mb-4" shadow="hover">
      <div class="user-profile">
        <el-avatar :size="80" :src="userAvatar" class="user-avatar">
          {{ user.username?.charAt(0).toUpperCase() }}
        </el-avatar>
        <div class="user-details">
          <h2 class="username">{{ user.username }}</h2>
          <div class="user-meta">
            <el-tag size="small" effect="plain">{{ user.role || 'User' }}</el-tag>
            <!-- Add more user info here if available, e.g., email, join date -->
          </div>
        </div>
      </div>
    </el-card>

    <!-- Submissions Table -->
    <el-card class="submissions-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <h3 class="header-title"><el-icon><List /></el-icon> Submission History</h3>
        </div>
      </template>

      <el-table
        :data="submissions"
        style="width: 100%"
        v-loading="loading"
        stripe
        :default-sort="{ prop: 'created_at', order: 'descending' }"
      >
        <el-table-column prop="id" label="#" width="80" align="center" />

        <el-table-column prop="problem_title" label="Problem" min-width="200">
          <template #default="scope">
            <el-link type="primary" :underline="false" @click="$router.push(`/problem/${scope.row.problem_id}`)">
              <span class="problem-link">{{ scope.row.problem_id }}. {{ scope.row.problem_title }}</span>
            </el-link>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="Status" width="140" align="center">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)" effect="light" size="small" class="status-tag">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="score" label="Score" width="80" align="center">
          <template #default="scope">
            <span :class="getScoreClass(scope.row.score)" class="score-text">{{ scope.row.score }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="language" label="Lang" width="100" align="center" />

        <el-table-column prop="created_at" label="Time" min-width="160" align="center">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="Action" width="100" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" plain @click="$router.push(`/submission/${scope.row.id}`)">
              Details
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { getUserSubmissions } from '@/api/user'
import { ElMessage } from 'element-plus'
import { List } from '@element-plus/icons-vue'

const userStore = useUserStore()
const user = computed(() => userStore.user || {})
// Use empty string to trigger slot content if no avatar URL
const userAvatar = computed(() => userStore.user?.avatar || '')

const submissions = ref([])
const loading = ref(false)

const getStatusType = (status) => {
  if (!status) return 'info'
  const s = status.toLowerCase()
  if (s === 'accepted') return 'success'
  if (s === 'pending' || s === 'judging') return 'warning'
  if (s.includes('error') || s === 'wrong answer') return 'danger'
  return 'info'
}

const getScoreClass = (score) => {
  if (score === 100) return 'text-success'
  if (score > 0) return 'text-warning'
  return 'text-danger'
}

const formatTime = (isoString) => {
  if (!isoString) return ''
  return new Date(isoString).toLocaleString()
}

const fetchSubmissions = async () => {
  loading.value = true
  try {
    const data = await getUserSubmissions()
    submissions.value = data
  } catch (error) {
    ElMessage.error('Failed to load submissions')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSubmissions()
})
</script>

<style scoped>
.profile-container {
  max-width: 1000px;
  margin: 0 auto;
}

.mb-4 {
  margin-bottom: 20px;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.username {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 600;
}

.user-avatar {
  background-color: var(--el-color-primary);
  color: white;
  font-size: 32px;
}

.card-header {
  display: flex;
  align-items: center;
}

.header-title {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-tag {
  width: 100px;
}

.score-text {
  font-weight: bold;
}

.text-success { color: var(--el-color-success); }
.text-warning { color: var(--el-color-warning); }
.text-danger { color: var(--el-color-danger); }

.problem-link {
  font-weight: 500;
}
</style>
