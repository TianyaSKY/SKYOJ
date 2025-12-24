<template>
  <div class="profile-container">
    <!-- User Info Card -->
    <el-card class="user-card mb-4" shadow="hover">
      <div class="user-profile">
        <el-avatar :size="80" :src="userAvatar" class="user-avatar">
          {{ targetUser.username?.charAt(0).toUpperCase() }}
        </el-avatar>
        <div class="user-details">
          <h2 class="username">{{ targetUser.username }}</h2>
          <div class="user-meta">
            <el-tag size="small" effect="plain">{{ targetUser.role || 'User' }}</el-tag>
            <span class="join-date" v-if="targetUser.created_at">
              Joined on {{ formatDate(targetUser.created_at) }}
            </span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- Heatmap Card -->
    <el-card class="heatmap-card mb-4" shadow="hover">
      <template #header>
        <div class="card-header">
          <h3 class="header-title"><el-icon><Calendar /></el-icon> Activity</h3>
        </div>
      </template>
      <submission-heatmap :submissions="submissions" v-loading="loading" />
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

        <el-table-column prop="exam_id" label="Exam" width="100" align="center">
          <template #default="scope">
            <el-tag v-if="scope.row.exam_id !== null && scope.row.exam_id !== -1" size="small" type="info">
              ID: {{ scope.row.exam_id }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>

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
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getUserSubmissions, getUserProfile } from '@/api/user'
import { ElMessage } from 'element-plus'
import { List, Calendar } from '@element-plus/icons-vue'
import SubmissionHeatmap from '@/components/SubmissionHeatmap.vue'

const route = useRoute()
const userStore = useUserStore()

const targetUser = ref({})
const submissions = ref([])
const loading = ref(false)

const userId = computed(() => route.params.id)
const userAvatar = computed(() => targetUser.value.avatar || '')

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

const formatDate = (isoString) => {
  if (!isoString) return ''
  return new Date(isoString).toLocaleDateString()
}

const fetchData = async () => {
  loading.value = true
  try {
    const id = userId.value
    if (id) {
      // Fetch specific user profile and submissions
      const profile = await getUserProfile(id)
      targetUser.value = profile
      const subs = await getUserSubmissions(id)
      submissions.value = subs
    } else {
      // Fetch current user profile and submissions
      targetUser.value = userStore.user || {}
      const subs = await getUserSubmissions()
      submissions.value = subs
    }
  } catch (error) {
    ElMessage.error('Failed to load profile data')
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, () => {
  fetchData()
})

onMounted(() => {
  fetchData()
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

.user-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.join-date {
  font-size: 0.9rem;
  color: #909399;
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
