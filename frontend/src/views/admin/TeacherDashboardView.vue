<template>
  <div class="teacher-dashboard-container">
    <div class="dashboard-header">
      <div class="header-left">
        <h1 class="page-title">教师工作台</h1>
        <p class="page-desc">欢迎回来，这里是您的教学管理中心。</p>
      </div>
      <div class="header-right">
        <el-button :icon="Plus" type="primary" @click="$router.push({ name: 'problem-admin' })">新增题目</el-button>
        <el-button :icon="Timer" type="success" @click="$router.push({ name: 'exam-admin' })">创建考试</el-button>
      </div>
    </div>

    <!-- Stats Overview -->
    <el-row :gutter="20" class="stats-row">
      <el-col v-for="(stat, index) in stats" :key="stat.label" :span="6">
        <div
            :class="{ 'clickable-stat': index === 3 }"
            class="stat-card"
            @click="index === 3 ? userListVisible = true : null"
        >
          <div :style="{ color: stat.color, backgroundColor: stat.color + '15' }" class="stat-icon">
            <el-icon :size="24">
              <component :is="stat.icon"/>
            </el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <h3 class="section-title">核心管理</h3>
    <el-row :gutter="20" class="dashboard-cards">
      <!-- 题目管理卡片 -->
      <el-col :lg="6" :md="8" :sm="12" :xs="24">
        <div class="nav-card" @click="$router.push({ name: 'problem-admin' })">
          <div class="nav-icon" style="color: #409EFF; background-color: #ecf5ff">
            <el-icon :size="32">
              <List/>
            </el-icon>
          </div>
          <h3>题目管理</h3>
          <p>创建、编辑和删除题目，管理测试数据与 SPJ 脚本。</p>
          <div class="nav-footer">
            <span>进入管理 <el-icon><ArrowRight/></el-icon></span>
          </div>
        </div>
      </el-col>

      <!-- 考试管理卡片 -->
      <el-col :lg="6" :md="8" :sm="12" :xs="24">
        <div class="nav-card" @click="$router.push({ name: 'exam-admin' })">
          <div class="nav-icon" style="color: #F56C6C; background-color: #fef0f0">
            <el-icon :size="32">
              <Timer/>
            </el-icon>
          </div>
          <h3>考试管理</h3>
          <p>组织在线考试、设置访问权限及监控实时进度。</p>
          <div class="nav-footer">
            <span>进入管理 <el-icon><ArrowRight/></el-icon></span>
          </div>
        </div>
      </el-col>

      <!-- 系统设置卡片 -->
      <el-col :lg="6" :md="8" :sm="12" :xs="24">
        <div class="nav-card" @click="openSysSettings">
          <div class="nav-icon" style="color: #E6A23C; background-color: #fdf6ec">
            <el-icon :size="32">
              <Setting/>
            </el-icon>
          </div>
          <h3>系统设置</h3>
          <p>配置网站公告、练习模式及 LLM 智能体 API 密钥。</p>
          <div class="nav-footer">
            <span>打开设置 <el-icon><ArrowRight/></el-icon></span>
          </div>
        </div>
      </el-col>

      <!-- 教师手册卡片 -->
      <el-col :lg="6" :md="8" :sm="12" :xs="24">
        <div class="nav-card" @click="$router.push({ name: 'doc-teacher-manual' })">
          <div class="nav-icon" style="color: #67C23A; background-color: #f0f9eb">
            <el-icon :size="32">
              <Document/>
            </el-icon>
          </div>
          <h3>教师手册</h3>
          <p>查阅录入指南、AICase 使用说明及评分示例。</p>
          <div class="nav-footer">
            <span>查看文档 <el-icon><ArrowRight/></el-icon></span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- User List Dialog -->
    <el-dialog v-model="userListVisible" title="所有用户" width="800px">
      <el-table v-loading="usersLoading" :data="users" stripe>
        <el-table-column align="center" label="ID" prop="id" width="80"/>
        <el-table-column label="用户名" min-width="150" prop="username">
          <template #default="scope">
            <div class="user-cell">
              <el-avatar :size="24" class="mr-2">{{ scope.row.username.charAt(0).toUpperCase() }}</el-avatar>
              <span>{{ scope.row.username }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" prop="role" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.role === 'admin' ? 'danger' : 'info'" size="small">
              {{ scope.row.role }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column align="center" label="操作" width="150">
          <template #default="scope">
            <el-button link type="primary" @click="viewUserProfile(scope.row.id)">查看主页</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- System Settings Dialog -->
    <el-dialog v-model="sysDialogVisible" class="settings-dialog" title="系统全局配置" width="700px">
      <el-tabs class="settings-tabs" type="border-card">
        <el-tab-pane label="基础设置">
          <el-form :model="sysForm" class="mt-4" label-position="top">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="网站标题">
                  <el-input v-model="sysForm.title" placeholder="例如: SKYOJ"/>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="运行模式">
                  <div class="mode-switches">
                    <el-switch v-model="sysForm.practice" active-text="练习模式"/>
                    <el-tooltip content="关闭后学生只能访问考试，无法自由练习" placement="top">
                      <el-icon class="info-icon">
                        <InfoFilled/>
                      </el-icon>
                    </el-tooltip>
                  </div>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="公告内容">
              <el-input v-model="sysForm.info" :rows="3" placeholder="顶部滚动显示的公告内容" type="textarea"/>
            </el-form-item>
            <el-form-item label="公告样式">
              <el-radio-group v-model="sysForm.warning">
                <el-radio :label="false">普通 (蓝色)</el-radio>
                <el-radio :label="true">警告 (红色)</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="AI 智能体 (LLM)">
          <el-alert :closable="false" class="mb-4" show-icon
                    title="配置后可启用 AI 辅助出题、AICase 自动生成测试数据等功能。" type="info"/>
          <el-form :model="sysForm" class="mt-4" label-position="top">
            <el-form-item label="API Endpoint">
              <el-input v-model="sysForm.llm_api_url" placeholder="https://api.openai.com/v1"/>
            </el-form-item>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="模型名称">
                  <el-input v-model="sysForm.llm_model_name" placeholder="gpt-4o"/>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="API Key">
                  <el-input v-model="sysForm.llm_api_key" placeholder="sk-..." show-password type="password"/>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="sysDialogVisible = false">取消</el-button>
          <el-button :loading="sysSubmitting" type="primary" @click="handleSaveSysSettings">保存全局配置</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {onMounted, ref, watch} from 'vue'
import {useRouter} from 'vue-router'
import {ArrowRight, Document, InfoFilled, List, Plus, Setting, Timer} from '@element-plus/icons-vue'
import {getSysInfo, getSysStatistics, updateSysInfo} from '@/api/sys'
import {getAllUsers} from '@/api/user'
import {useSysStore} from '@/stores/sys'
import {ElMessage} from 'element-plus'

const router = useRouter()
const sysStore = useSysStore()
const sysDialogVisible = ref(false)
const sysSubmitting = ref(false)
const sysForm = ref({
  title: '',
  info: '',
  warning: false,
  practice: true,
  llm_api_url: '',
  llm_model_name: '',
  llm_api_key: ''
})

const userListVisible = ref(false)
const users = ref([])
const usersLoading = ref(false)

const stats = ref([
  {label: '总题目数', value: '0', icon: 'Collection', color: '#409EFF'},
  {label: '活跃考试', value: '0', icon: 'Timer', color: '#F56C6C'},
  {label: '今日提交', value: '0', icon: 'Monitor', color: '#67C23A'},
  {label: '总用户数', value: '0', icon: 'User', color: '#E6A23C'}
])

const fetchStats = async () => {
  try {
    const data = await getSysStatistics()
    if (data) {
      stats.value[0].value = data.total_problems || 0
      stats.value[1].value = data.exams_in_period || 0
      stats.value[2].value = data.today_submissions || 0
      stats.value[3].value = data.total_users || 0
    }
  } catch (error) {
    console.error('Failed to fetch stats')
  }
}

const fetchUsers = async () => {
  usersLoading.value = true
  try {
    users.value = await getAllUsers()
  } catch (error) {
    ElMessage.error('获取用户列表失败')
  } finally {
    usersLoading.value = false
  }
}

const viewUserProfile = (userId) => {
  userListVisible.value = false
  router.push(`/profile/${userId}`)
}

watch(userListVisible, (newVal) => {
  if (newVal) fetchUsers()
})

const openSysSettings = async () => {
  sysDialogVisible.value = true
  try {
    const res = await getSysInfo()
    if (res) {
      sysForm.value = {
        title: res.title || 'SKYOJ',
        info: res.info || '',
        warning: res.warning === 'True' || res.warning === true,
        practice: res.practice === 'True' || res.practice === true,
        llm_api_url: res.llm_api_url || '',
        llm_model_name: res.llm_model_name || '',
        llm_api_key: res.llm_api_key || ''
      }
    }
  } catch (error) {
    ElMessage.error('获取系统配置失败')
  }
}

const handleSaveSysSettings = async () => {
  sysSubmitting.value = true
  try {
    await updateSysInfo(sysForm.value)
    ElMessage.success('系统配置已更新')
    sysDialogVisible.value = false
    sysStore.fetchSysInfo()
  } catch (error) {
    ElMessage.error('更新失败')
  } finally {
    sysSubmitting.value = false
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
.teacher-dashboard-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 40px;
}

.page-title {
  font-size: 2.2rem;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 8px;
}

.page-desc {
  color: #888;
  font-size: 1.1rem;
}

.header-right {
  display: flex;
  gap: 12px;
}

/* Stats Row */
.stats-row {
  margin-bottom: 40px;
}

.stat-card {
  background: #fff;
  padding: 24px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
  border: 1px solid #f0f0f0;
  transition: all 0.3s;
}

.clickable-stat {
  cursor: pointer;
}

.clickable-stat:hover {
  transform: translateY(-5px);
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 700;
  color: #1a1a1a;
  line-height: 1.2;
}

.stat-label {
  font-size: 0.9rem;
  color: #888;
  font-weight: 500;
}

.section-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 24px;
}

/* Nav Cards */
.dashboard-cards {
  margin-bottom: 40px;
}

.nav-card {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 20px;
  padding: 32px;
  height: 100%;
  transition: all 0.3s;
  cursor: pointer;
  display: flex;
  flex-direction: column;
}

.nav-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
  transform: translateY(-5px);
}

.nav-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}

.nav-card h3 {
  font-size: 1.3rem;
  margin: 0 0 12px;
  color: #1a1a1a;
}

.nav-card p {
  color: #666;
  line-height: 1.6;
  margin: 0 0 24px;
  font-size: 0.95rem;
  flex-grow: 1;
}

.nav-footer {
  padding-top: 20px;
  border-top: 1px solid #f5f5f5;
  color: var(--el-color-primary);
  font-weight: 600;
  font-size: 0.9rem;
}

.nav-footer span {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* User List Cell */
.user-cell {
  display: flex;
  align-items: center;
}

.mr-2 {
  margin-right: 8px;
}

/* Settings Dialog */
.settings-tabs {
  border-radius: 8px;
  overflow: hidden;
}

.mode-switches {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.info-icon {
  color: #909399;
  cursor: help;
}

.mb-4 {
  margin-bottom: 16px;
}

.mt-4 {
  margin-top: 16px;
}

.dialog-footer {
  padding-top: 10px;
}
</style>
