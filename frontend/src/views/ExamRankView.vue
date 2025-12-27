<template>
  <div class="exam-rank-container">
    <!-- Fullscreen Balloon Overlay -->
    <div class="balloon-overlay" v-if="showFullscreenBalloons">
      <div
        v-for="b in balloons"
        :key="b.id"
        class="floating-balloon"
        :style="{
          left: b.x + '%',
          backgroundColor: b.color,
          animationDuration: b.duration + 's',
          animationDelay: b.delay + 's'
        }"
      >
        <div class="balloon-string"></div>
        <div class="balloon-text" v-if="b.text">{{ b.text }}</div>
      </div>
    </div>

    <div class="rank-header-section">
      <el-page-header @back="$router.back()">
        <template #content>
          <div class="header-content">
            <h2 class="exam-title">{{ examTitle }}</h2>
            <div class="header-tags">
              <el-tag :type="autoRefresh ? 'success' : 'info'" effect="dark" round size="small">
                {{ autoRefresh ? '实时同步中' : '静态模式' }}
              </el-tag>
              <span class="last-update" v-if="lastUpdateTime">最后更新: {{ lastUpdateTime }}</span>
            </div>
          </div>
        </template>
        <template #extra>
          <div class="header-actions">
            <div class="refresh-control">
              <span class="control-label">自动刷新</span>
              <el-switch v-model="autoRefresh" @change="handleAutoRefreshChange" />
            </div>
            <el-button :icon="Refresh" :loading="loading" plain type="primary" @click="fetchRankData">
              手动刷新
            </el-button>
          </div>
        </template>
      </el-page-header>

      <!-- Podium for Top 3 -->
      <div v-if="rankData.length >= 3" class="podium-container">
        <div class="podium-item silver">
          <div class="rank-badge">2</div>
          <div class="user-avatar-wrapper">
            <el-avatar :size="64" :src="rankData[1].avatar ? `/api${rankData[1].avatar}` : ''" class="user-avatar">
              {{ rankData[1].username?.charAt(0).toUpperCase() }}
            </el-avatar>
          </div>
          <div class="user-name">{{ rankData[1].username }}</div>
          <div class="user-stats">
            <span class="solved">{{ rankData[1].solved }} 题</span>
            <span class="penalty">{{ formatDuration(rankData[1].penalty) }}</span>
          </div>
          <div class="podium-base"></div>
        </div>

        <div class="podium-item gold">
          <div class="crown">
            <el-icon><Trophy /></el-icon>
          </div>
          <div class="rank-badge">1</div>
          <div class="user-avatar-wrapper">
            <el-avatar :size="80" :src="rankData[0].avatar ? `/api${rankData[0].avatar}` : ''" class="user-avatar">
              {{ rankData[0].username?.charAt(0).toUpperCase() }}
            </el-avatar>
          </div>
          <div class="user-name">{{ rankData[0].username }}</div>
          <div class="user-stats">
            <span class="solved">{{ rankData[0].solved }} 题</span>
            <span class="penalty">{{ formatDuration(rankData[0].penalty) }}</span>
          </div>
          <div class="podium-base"></div>
        </div>

        <div class="podium-item bronze">
          <div class="rank-badge">3</div>
          <div class="user-avatar-wrapper">
            <el-avatar :size="64" :src="rankData[2].avatar ? `/api${rankData[2].avatar}` : ''" class="user-avatar">
              {{ rankData[2].username?.charAt(0).toUpperCase() }}
            </el-avatar>
          </div>
          <div class="user-name">{{ rankData[2].username }}</div>
          <div class="user-stats">
            <span class="solved">{{ rankData[2].solved }} 题</span>
            <span class="penalty">{{ formatDuration(rankData[2].penalty) }}</span>
          </div>
          <div class="podium-base"></div>
        </div>
      </div>
    </div>

    <el-card class="rank-card" shadow="never">
      <el-table
        v-loading="loading"
        :data="rankData"
        border
        style="width: 100%"
        header-cell-class-name="rank-header-cell"
        cell-class-name="rank-cell"
        :row-class-name="tableRowClassName"
      >
        <el-table-column align="center" label="排名" width="80" fixed>
          <template #default="scope">
            <div class="rank-num-cell">
              <el-icon v-if="scope.$index === 0" class="rank-icon gold-icon"><Trophy /></el-icon>
              <el-icon v-else-if="scope.$index === 1" class="rank-icon silver-icon"><Trophy /></el-icon>
              <el-icon v-else-if="scope.$index === 2" class="rank-icon bronze-icon"><Trophy /></el-icon>
              <span v-else class="rank-num">{{ scope.$index + 1 }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="参赛者" prop="username" width="220" fixed>
          <template #default="scope">
            <div class="user-info-cell">
              <el-avatar :size="28" :src="scope.row.avatar ? `/api${scope.row.avatar}` : ''" class="table-avatar">
                {{ scope.row.username?.charAt(0).toUpperCase() }}
              </el-avatar>
              <span class="username-text">{{ scope.row.username }}</span>
              <transition name="balloon-pop">
                <div v-if="rankChangedUsers.has(scope.row.username)" class="rank-up-tag">
                  <el-icon><Top /></el-icon>
                  <span>UP!</span>
                </div>
              </transition>
            </div>
          </template>
        </el-table-column>

        <el-table-column
            v-for="(problem, index) in problems"
            :key="problem.problem_id"
            :label="getProblemLabel(problem, index)"
            align="center"
            min-width="100"
        >
          <template #default="scope">
            <div v-if="getProblemStatus(scope.row, problem.problem_id)" class="status-wrapper">
              <div :class="getStatusClass(getProblemStatus(scope.row, problem.problem_id))" class="status-box">
                <div class="main-info">
                  <span v-if="getProblemStatus(scope.row, problem.problem_id).solved">
                    {{ formatTime(getProblemStatus(scope.row, problem.problem_id).time) }}
                  </span>
                  <span v-else-if="getProblemStatus(scope.row, problem.problem_id).failed_attempts > 0">
                    -{{ getProblemStatus(scope.row, problem.problem_id).failed_attempts }}
                  </span>
                </div>
                <div v-if="getProblemStatus(scope.row, problem.problem_id).solved && getProblemStatus(scope.row, problem.problem_id).failed_attempts > 0" class="sub-info">
                  (+{{ getProblemStatus(scope.row, problem.problem_id).failed_attempts }})
                </div>
              </div>
            </div>
            <span v-else class="empty-cell">-</span>
          </template>
        </el-table-column>

        <el-table-column align="center" label="解题" prop="solved" width="90" fixed="right">
          <template #default="scope">
            <span class="solved-count">{{ scope.row.solved }}</span>
          </template>
        </el-table-column>

        <el-table-column align="center" label="罚时" prop="penalty" width="120" fixed="right">
          <template #default="scope">
            <span class="penalty-text">{{ formatDuration(scope.row.penalty) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import {onMounted, onUnmounted, ref, watch} from 'vue'
import {useRoute} from 'vue-router'
import {getExamRank} from '@/api/exam'
import {Refresh, Top, Trophy} from '@element-plus/icons-vue'
import {ElMessage} from 'element-plus'
import dayjs from 'dayjs'

const route = useRoute()
const examId = route.params.id
const examTitle = ref('加载中...')
const loading = ref(false)
const rankData = ref([])
const problems = ref([])
const autoRefresh = ref(localStorage.getItem('exam_rank_auto_refresh') === 'true')
const lastUpdateTime = ref('')
const rankChangedUsers = ref(new Set())
const showFullscreenBalloons = ref(false)
const balloons = ref([])

let refreshTimer = null
let previousRankMap = new Map()

const BALLOON_COLORS = ['#ff4d4f', '#1890ff', '#52c41a', '#fadb14', '#722ed1', '#eb2f96']

const triggerFullscreenBalloons = (users) => {
  const newBalloons = []
  const userList = Array.from(users)

  for (let i = 0; i < 15; i++) {
    newBalloons.push({
      id: Date.now() + i,
      x: Math.random() * 90 + 5,
      color: BALLOON_COLORS[Math.floor(Math.random() * BALLOON_COLORS.length)],
      duration: 4 + Math.random() * 3,
      delay: Math.random() * 2,
      text: i < userList.length ? userList[i] : ''
    })
  }

  balloons.value = newBalloons
  showFullscreenBalloons.value = true

  setTimeout(() => {
    showFullscreenBalloons.value = false
    balloons.value = []
  }, 8000)
}

const fetchRankData = async (isAuto = false) => {
  if (!isAuto) loading.value = true
  try {
    const data = await getExamRank(examId)
    examTitle.value = data.exam_title
    problems.value = data.problems

    const newRankData = data.rank
    const currentRankMap = new Map()
    const improvedUsers = new Set()

    newRankData.forEach((user, index) => {
      currentRankMap.set(user.username, index)
      if (previousRankMap.has(user.username)) {
        const oldRank = previousRankMap.get(user.username)
        if (index < oldRank) {
          improvedUsers.add(user.username)
        }
      }
    })

    rankData.value = newRankData
    previousRankMap = currentRankMap
    lastUpdateTime.value = dayjs().format('HH:mm:ss')

    if (improvedUsers.size > 0) {
      rankChangedUsers.value = improvedUsers
      triggerFullscreenBalloons(improvedUsers)
      setTimeout(() => {
        rankChangedUsers.value = new Set()
      }, 6000)
    }
  } catch (error) {
    ElMessage.error('获取排名数据失败')
  } finally {
    if (!isAuto) loading.value = false
  }
}

const handleAutoRefreshChange = (val) => {
  localStorage.setItem('exam_rank_auto_refresh', val)
}

const getProblemLabel = (problem, index) => {
  return problem.display_id ? `P${problem.display_id}` : String.fromCharCode(65 + index)
}

const getProblemStatus = (row, problemId) => {
  return row.problems?.[problemId] || null
}

const getStatusClass = (status) => {
  if (status.solved) return 'status-ac'
  if (status.failed_attempts > 0) return 'status-wa'
  return ''
}

const formatTime = (seconds) => {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}:${m.toString().padStart(2, '0')}`
}

const formatDuration = (seconds) => {
  if (!seconds) return '0'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

const tableRowClassName = ({ row, rowIndex }) => {
  let classes = []
  if (rowIndex === 0) classes.push('gold-row')
  else if (rowIndex === 1) classes.push('silver-row')
  else if (rowIndex === 2) classes.push('bronze-row')

  if (rankChangedUsers.value.has(row.username)) {
    classes.push('rank-up-row')
  }

  return classes.join(' ')
}

watch(autoRefresh, (val) => {
  if (val) refreshTimer = setInterval(() => fetchRankData(true), 30000)
  else clearInterval(refreshTimer)
}, { immediate: true })

onMounted(fetchRankData)
onUnmounted(() => clearInterval(refreshTimer))
</script>

<style scoped>
.exam-rank-container {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  background-color: #fcfcfd;
  min-height: calc(100vh - 60px);
  position: relative;
}

/* Fullscreen Balloon Overlay */
.balloon-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  pointer-events: none;
  z-index: 9999;
  overflow: hidden;
}

.floating-balloon {
  position: absolute;
  bottom: -150px;
  width: 60px;
  height: 75px;
  border-radius: 50% 50% 50% 50% / 40% 40% 60% 60%;
  animation: float-up linear forwards;
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: inset -5px -5px 10px rgba(0,0,0,0.1);
}

.balloon-string {
  position: absolute;
  bottom: -40px;
  width: 2px;
  height: 40px;
  background: rgba(0,0,0,0.1);
}

.balloon-text {
  color: white;
  font-size: 12px;
  font-weight: bold;
  text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
  text-align: center;
  padding: 0 5px;
  word-break: break-all;
}

@keyframes float-up {
  0% { transform: translateY(0) rotate(0deg); opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { transform: translateY(-120vh) rotate(20deg); opacity: 0; }
}

/* Original Styles */
.rank-header-section {
  margin-bottom: 32px;
}

.header-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.exam-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
}

.header-tags {
  display: flex;
  align-items: center;
  gap: 12px;
}

.last-update {
  font-size: 12px;
  color: #94a3b8;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

.refresh-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-label {
  font-size: 14px;
  color: #64748b;
}

/* Podium Styles */
.podium-container {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  margin: 40px 0 20px;
  gap: 20px;
  height: 240px;
}

.podium-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 180px;
  position: relative;
}

.user-avatar-wrapper {
  margin-bottom: 12px;
  border: 4px solid white;
  border-radius: 50%;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  overflow: hidden;
  display: flex;
}

.user-avatar {
  background-color: #f1f5f9;
  color: #94a3b8;
}

.user-name {
  font-weight: 700;
  font-size: 16px;
  color: #1e293b;
  margin-bottom: 4px;
}

.user-stats {
  font-size: 13px;
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.user-stats .solved {
  color: #10b981;
  font-weight: 600;
}

.user-stats .penalty {
  color: #64748b;
}

.podium-base {
  width: 100%;
  border-radius: 8px 8px 0 0;
  position: relative;
}

.rank-badge {
  position: absolute;
  top: -10px;
  right: 45px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  font-weight: bold;
  font-size: 12px;
  color: white;
  z-index: 2;
}

/* Gold */
.gold .podium-base { height: 100px; background: linear-gradient(to bottom, #fbbf24, #d97706); }
.gold .user-avatar-wrapper { border-color: #fbbf24; }
.gold .rank-badge { background: #d97706; right: 40px; }
.crown { position: absolute; top: -35px; font-size: 32px; color: #fbbf24; animation: float 2s infinite ease-in-out; }

/* Silver */
.silver .podium-base { height: 70px; background: linear-gradient(to bottom, #cbd5e1, #64748b); }
.silver .rank-badge { background: #64748b; }

/* Bronze */
.bronze .podium-base { height: 50px; background: linear-gradient(to bottom, #d97706, #92400e); }
.bronze .rank-badge { background: #92400e; }

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

/* Table Styles */
.rank-card {
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

:deep(.rank-header-cell) {
  background-color: #f8fafc !important;
  color: #475569;
  font-weight: 600;
  height: 56px;
}

.rank-num-cell {
  display: flex;
  justify-content: center;
  align-items: center;
}

.rank-icon {
  font-size: 20px;
}

.gold-icon { color: #fbbf24; }
.silver-icon { color: #94a3b8; }
.bronze-icon { color: #d97706; }

.rank-num {
  font-weight: 600;
  color: #64748b;
}

.user-info-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
}

.table-avatar {
  background-color: var(--el-color-primary);
  color: white;
  flex-shrink: 0;
}

.username-text {
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rank-up-tag {
  display: flex;
  align-items: center;
  gap: 2px;
  background: #10b981;
  color: white;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: bold;
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
}

@keyframes balloon-pop {
  0% { transform: scale(0) translateY(10px); opacity: 0; }
  100% { transform: scale(1) translateY(0); opacity: 1; }
}

.balloon-pop-enter-active {
  animation: balloon-pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.balloon-pop-leave-active {
  transition: all 0.5s ease;
}
.balloon-pop-leave-to {
  transform: translateY(-20px);
  opacity: 0;
}

.status-box {
  width: 85%;
  height: 44px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border-radius: 6px;
}

.status-ac {
  background-color: #10b981;
  color: #fff;
}

.status-wa {
  background-color: #ef4444;
  color: #fff;
}

.solved-count {
  font-weight: 800;
  color: #10b981;
  font-size: 18px;
}

.penalty-text {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 13px;
  color: #64748b;
}

/* Row Highlighting */
:deep(.gold-row) { background-color: rgba(251, 191, 36, 0.05) !important; }
:deep(.silver-row) { background-color: rgba(148, 163, 184, 0.05) !important; }
:deep(.bronze-row) { background-color: rgba(217, 119, 6, 0.05) !important; }

:deep(.rank-up-row) {
  animation: highlight-fade 5s ease-out;
}

@keyframes highlight-fade {
  0% { background-color: rgba(16, 185, 129, 0.15) !important; }
  100% { background-color: transparent; }
}

@media screen and (max-width: 768px) {
  .podium-container { display: none; }
}
</style>
