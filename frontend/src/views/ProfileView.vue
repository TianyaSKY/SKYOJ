<template>
  <div class="profile-container">
    <!-- User Info Card -->
    <el-card class="user-card mb-4" shadow="hover">
      <div class="user-profile">
        <div class="avatar-wrapper">
          <el-avatar :size="80" :src="userAvatar" class="user-avatar">
            {{ targetUser.username?.charAt(0).toUpperCase() }}
          </el-avatar>
          <el-upload
              v-if="isCurrentUser"
              class="avatar-uploader"
              action="#"
              :show-file-list="false"
              :http-request="handleAvatarUpload"
              :before-upload="beforeAvatarUpload"
              :disabled="uploadingAvatar"
          >
            <div class="avatar-edit-overlay">
              <el-icon><Camera /></el-icon>
            </div>
          </el-upload>
        </div>
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

    <template v-if="isPracticeMode || isTeacher">
      <!-- Wrong Book Card -->
      <el-card v-if="showWrongBook" class="wrongbook-card mb-4" shadow="hover">
        <template #header>
          <div class="card-header">
            <h3 class="header-title">
              <el-icon><Warning /></el-icon>
              错题本
            </h3>
            <div class="wrongbook-stats">
              <el-tag type="danger" effect="plain" size="small">未解决 {{ wbStats.unresolved }}</el-tag>
              <el-tag type="success" effect="plain" size="small">已掌握 {{ wbStats.accepted }}</el-tag>
              <el-tag type="warning" effect="plain" size="small">已复习 {{ wbStats.reviewed }}</el-tag>
            </div>
          </div>
        </template>
        <el-table v-loading="wbLoading" :data="wbItems" stripe style="width: 100%" :max-height="300">
          <el-table-column align="center" label="#" prop="problem_id" width="80"/>
          <el-table-column label="题目" min-width="200" prop="problem_title"/>
          <el-table-column align="center" label="首次出错" min-width="160">
            <template #default="scope">
              <span class="text-secondary">{{ formatTime(scope.row.first_wrong_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column align="center" label="最近出错" min-width="160">
            <template #default="scope">
              <span class="text-secondary">{{ formatTime(scope.row.latest_wrong_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column align="center" label="状态" width="120">
            <template #default="scope">
              <el-tag v-if="scope.row.accepted" type="success" size="small">已掌握</el-tag>
              <el-tag v-else type="danger" size="small">未解决</el-tag>
            </template>
          </el-table-column>
          <el-table-column align="center" label="复习" width="100">
            <template #default="scope">
              <el-button
                :type="scope.row.reviewed ? 'warning' : 'default'"
                size="small"
                :disabled="scope.row.accepted || pendingReviews.has(scope.row.id)"
                :loading="pendingReviews.has(scope.row.id)"
                @click="toggleReview(scope.row)"
              >
                {{ scope.row.reviewed ? '已复习' : '标记复习' }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column align="center" fixed="right" label="操作" width="90">
            <template #default="scope">
              <el-button plain size="small" type="primary" @click="$router.push(`/problem/${scope.row.problem_id}`)">
                去练
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-if="wbTotal > wbPageSize"
          :current-page="wbPage"
          :page-size="wbPageSize"
          :total="wbTotal"
          :disabled="wbLoading"
          layout="prev, pager, next"
          @current-change="fetchWrongBook"
        />
        <el-empty v-if="wbStats.total === 0 && !wbLoading" description="暂无错题记录，继续加油！" />
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
    </template>
    <el-empty v-else description="考试模式下隐藏提交历史" />
  </div>
</template>

<script setup lang="ts">
import {computed, onBeforeUnmount, ref, watch} from 'vue'
import {useRoute} from 'vue-router'
import { formatServerDateTime as formatTime, formatServerDate as formatDate } from '@/utils/date'
import {useUserStore} from '@/stores/user'
import {useSysStore} from '@/stores/sys'
import {getUserProfile, getUserSubmissions, uploadAvatar} from '@/api/user'
import {ElMessage} from 'element-plus'
import {Calendar, List, Camera, Warning} from '@element-plus/icons-vue'
import SubmissionHeatmap from '@/components/SubmissionHeatmap.vue'
import { getWrongBookStats, getWrongBook, toggleWrongBookReview } from '@/api/wrongBook'
import type { UserProfileResponse, UserSubmissionResponse } from '@/types/user'
import type { WrongBookItemResponse, WrongBookStatsResponse } from '@/types/wrongBook'
import type { UploadRequestOptions } from 'element-plus'
import { errorMessage } from '@/utils/error'
import { parseRouteId } from '@/utils/route'

const route = useRoute()
const userStore = useUserStore()
const sysStore = useSysStore()

const targetUser = ref<Partial<UserProfileResponse> & {created_at?: string | null}>({})
const submissions = ref<UserSubmissionResponse[]>([])
const loading = ref(false)
const uploadingAvatar = ref(false)
let profileVersion = 0
let disposed = false
const isCurrentProfile = (version: number) => !disposed && version === profileVersion
const wbItems = ref<WrongBookItemResponse[]>([])
const wbStats = ref({ total: 0, unresolved: 0, reviewed: 0, accepted: 0 })
const wbLoading = ref(false)
const wbPage = ref(1)
const wbPageSize = 10
const wbTotal = ref(0)
const pendingReviews = ref(new Set<number>())
let wbScopeVersion = 0
let wbRequestVersion = 0
let wbRequestedPage = 1
const isCurrentWrongBook = (version: number) => !disposed && version === wbScopeVersion

const userId = computed(() => route.params.id)
const userAvatar = computed(() => {
  if (!targetUser.value.avatar) return ''
  return targetUser.value.avatar
})
const isTeacher = computed(() => userStore.user?.role === 'teacher')
const isPracticeMode = computed(() => ![false, 'False'].includes(sysStore.practice))
const isCurrentUser = computed(() => !userId.value || parseRouteId(userId.value) === userStore.user?.id)
const showWrongBook = computed(() => Boolean(userStore.user?.id) && isCurrentUser.value && (isPracticeMode.value || isTeacher.value))

const getStatusType = (status: string) => {
  if (!status) return 'info'
  const s = status.toLowerCase()
  if (s === 'accepted') return 'success'
  if (s === 'pending' || s === 'judging') return 'warning'
  if (s.includes('error') || s === 'wrong answer') return 'danger'
  return 'info'
}

const getScoreClass = (score: number) => {
  if (score === 100) return 'text-success'
  if (score > 0) return 'text-warning'
  return 'text-danger'
}



const fetchWrongBook = async (pageNo = wbPage.value): Promise<void> => {
  if (!showWrongBook.value) return
  const scope = wbScopeVersion
  wbRequestedPage = pageNo
  const requestId = ++wbRequestVersion
  const isCurrent = () => isCurrentWrongBook(scope) && requestId === wbRequestVersion
  wbLoading.value = true
  try {
    const [statsRes, listRes] = await Promise.all([
      getWrongBookStats(),
      getWrongBook({ page: pageNo, page_size: wbPageSize }),
    ])
    if (!isCurrent()) return
    const lastPage = Math.max(1, Math.ceil((listRes.total || 0) / wbPageSize))
    if (pageNo > lastPage) return await fetchWrongBook(lastPage)
    wbPage.value = pageNo
    wbTotal.value = listRes.total || 0
    wbStats.value = statsRes
    wbItems.value = listRes.items || []
  } catch (error) {
    if (isCurrent()) ElMessage.error(errorMessage(error, '加载错题本失败'))
  } finally {
    if (isCurrent()) wbLoading.value = false
  }
}

const toggleReview = async (item: WrongBookItemResponse) => {
  if (!showWrongBook.value || item.accepted || pendingReviews.value.has(item.id)) return
  const scope = wbScopeVersion
  pendingReviews.value.add(item.id)
  try {
    const res = await toggleWrongBookReview(item.id)
    if (!isCurrentWrongBook(scope)) return
    item.reviewed = res.reviewed
    const current = wbItems.value.find(entry => entry.id === item.id)
    if (current) current.reviewed = res.reviewed
    // 重新读取服务端统计，并使较早的查询失效；保留正在翻到的页码。
    await fetchWrongBook(wbRequestedPage)
  } catch (error) {
    if (isCurrentWrongBook(scope)) ElMessage.error(errorMessage(error, '操作失败'))
  } finally {
    if (isCurrentWrongBook(scope)) pendingReviews.value.delete(item.id)
  }
}

const beforeAvatarUpload = (file: File) => {
  const isJPGorPNG = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif'].includes(file.type)
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isJPGorPNG) {
    ElMessage.error('Avatar picture must be JPG/PNG/GIF format!')
  }
  if (!isLt2M) {
    ElMessage.error('Avatar picture size can not exceed 2MB!')
  }
  return isJPGorPNG && isLt2M
}

const handleAvatarUpload = async (options: UploadRequestOptions) => {
  if (!isCurrentUser.value || !userStore.user?.id || uploadingAvatar.value) return
  const version = profileVersion
  const ownerId = userStore.user.id
  uploadingAvatar.value = true
  const formData = new FormData()
  formData.append('avatar', options.file)
  try {
    const res = await uploadAvatar(formData)
    // 头像属于上传时的账户；切换资料页后仍更新该账户缓存。
    if (userStore.user?.id === ownerId) {
      const updatedUser = { ...userStore.user, avatar: res.avatar }
      userStore.user = updatedUser
      localStorage.setItem('user', JSON.stringify(updatedUser))
    }
    if (!isCurrentProfile(version)) return
    targetUser.value.avatar = res.avatar
    ElMessage.success('Avatar uploaded successfully')
  } catch (error) {
    if (isCurrentProfile(version)) ElMessage.error('Failed to upload avatar')
  } finally {
    uploadingAvatar.value = false
  }
}

const fetchData = async () => {
  const version = ++profileVersion
  const id = userId.value ? parseRouteId(userId.value) : null
  const showHistory = isPracticeMode.value || isTeacher.value
  targetUser.value = id ? {} : { ...userStore.user }
  submissions.value = []
  loading.value = true
  try {
    if (userId.value && id === null) {
      ElMessage.error('用户 ID 无效')
      return
    }
    if (id) {
      const profile = await getUserProfile(id)
      if (!isCurrentProfile(version)) return
      targetUser.value = profile
    }
    if (!showHistory) return
    const subs = await getUserSubmissions(id)
    if (!isCurrentProfile(version)) return
    submissions.value = subs
  } catch (error) {
    if (isCurrentProfile(version)) ElMessage.error('Failed to load profile data')
  } finally {
    if (isCurrentProfile(version)) loading.value = false
  }
}

watch([userId, () => userStore.user?.id, isPracticeMode, isTeacher], fetchData, { immediate: true })
onBeforeUnmount(() => { disposed = true; profileVersion += 1 })

watch([userId, () => userStore.user?.id, showWrongBook], () => {
  wbScopeVersion += 1
  wbItems.value = []
  wbStats.value = { total: 0, unresolved: 0, reviewed: 0, accepted: 0 }
  wbPage.value = 1
  wbRequestedPage = 1
  wbTotal.value = 0
  wbLoading.value = false
  pendingReviews.value.clear()
  fetchWrongBook()
}, { immediate: true })
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

.avatar-wrapper {
  position: relative;
  width: 80px;
  height: 80px;
}

.avatar-uploader {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.avatar-edit-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  color: white;
  opacity: 0;
  transition: opacity 0.3s;
  font-size: 24px;
}

.avatar-wrapper:hover .avatar-edit-overlay {
  opacity: 1;
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

.wrongbook-stats {
  display: flex;
  gap: 8px;
}

.wrongbook-more {
  margin-top: 12px;
  text-align: center;
}

.text-secondary {
  color: #909399;
  font-size: 0.9rem;
}
</style>
