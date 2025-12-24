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
            <el-tag effect="plain" size="small">{{ targetUser.role || 'User' }}</el-tag>
            <span v-if="targetUser.created_at" class="join-date">
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
          <h3 class="header-title">
            <el-icon>
              <Calendar/>
            </el-icon>
            Activity
          </h3>
        </div>
      </template>
      <submission-heatmap v-loading="loading" :submissions="submissions"/>
    </el-card>

    <!-- Submissions Table -->
    <el-card class="submissions-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <h3 class="header-title">
            <el-icon>
              <List/>
            </el-icon>
            Submission History
          </h3>
        </div>
      </template>

      <el-table
          v-loading="loading"
          :data="submissions"
          :default-sort="{ prop: 'created_at', order: 'descending' }"
          stripe
          style="width: 100%"
      >
        <el-table-column align="center" label="#" prop="id" width="80"/>

        <el-table-column label="Problem" min-width="200" prop="problem_title">
          <template #default="scope">
            <el-link :underline="false" type="primary" @click="$router.push(`/problem/${scope.row.problem_id}`)">
              <span class="problem-link">{{ scope.row.problem_id }}. {{ scope.row.problem_title }}</span>
            </el-link>
          </template>
        </el-table-column>

        <el-table-column align="center" label="Status" prop="status" width="140">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)" class="status-tag" effect="light" size="small">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column align="center" label="Score" prop="score" width="80">
          <template #default="scope">
            <span :class="getScoreClass(scope.row.score)" class="score-text">{{ scope.row.score }}</span>
          </template>
        </el-table-column>

        <el-table-column align="center" label="Lang" prop="language" width="100"/>

        <el-table-column align="center" label="Exam" prop="exam_id" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.exam_id !== null && scope.row.exam_id !== -1" size="small" type="info">
              ID: {{ scope.row.exam_id }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column align="center" label="Time" min-width="160" prop="created_at">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column align="center" fixed="right" label="Action" width="100">
          <template #default="scope">
            <el-button plain size="small" type="primary" @click="$router.push(`/submission/${scope.row.id}`)">
              Details
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import {computed, onMounted, ref, watch} from 'vue'
import {useRoute} from 'vue-router'
import {useUserStore} from '@/stores/user'
import {getUserProfile, getUserSubmissions} from '@/api/user'
import {ElMessage} from 'element-plus'
import {Calendar, List} from '@element-plus/icons-vue'
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

.text-success {
  color: var(--el-color-success);
}

.text-warning {
  color: var(--el-color-warning);
}

.text-danger {
  color: var(--el-color-danger);
}

.problem-link {
  font-weight: 500;
}
</style>
