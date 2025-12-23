<template>
  <div class="teacher-dashboard-container">
    <div class="dashboard-header">
      <h2>教师工作台</h2>
      <p class="subtitle">欢迎回来，这里是您的教学管理中心。</p>
    </div>

    <el-row :gutter="20" class="dashboard-cards">
      <!-- 题目管理卡片 -->
      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="hover" class="dashboard-card" @click="$router.push({ name: 'problem-admin' })">
          <div class="card-content">
            <el-icon class="card-icon" :size="40" color="#409EFF"><List /></el-icon>
            <h3>题目管理</h3>
            <p>创建、编辑和删除题目，管理测试数据。</p>
          </div>
        </el-card>
      </el-col>

      <!-- 考试管理卡片 -->
      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="hover" class="dashboard-card" @click="$router.push({ name: 'exam-admin' })">
          <div class="card-content">
            <el-icon class="card-icon" :size="40" color="#F56C6C"><Timer /></el-icon>
            <h3>考试管理</h3>
            <p>创建考试、设置密码及管理考试题目。</p>
          </div>
        </el-card>
      </el-col>

      <!-- 系统设置卡片 -->
      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="hover" class="dashboard-card" @click="openSysSettings">
          <div class="card-content">
            <el-icon class="card-icon" :size="40" color="#E6A23C"><Setting /></el-icon>
            <h3>系统设置</h3>
            <p>修改网站标题、公告栏信息及 LLM 智能体配置。</p>
          </div>
        </el-card>
      </el-col>

      <!-- 教师手册卡片 -->
      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="hover" class="dashboard-card" @click="$router.push({ name: 'doc-teacher-manual' })">
          <div class="card-content">
            <el-icon class="card-icon" :size="40" color="#67C23A"><Document /></el-icon>
            <h3>教师手册</h3>
            <p>查看题目录入指南、SPJ 编写示例及推荐代码。</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <div class="quick-actions">
      <h3>快捷入口</h3>
      <el-button type="primary" plain @click="$router.push({ name: 'problem-admin' })">新增题目</el-button>
      <el-button type="danger" plain @click="$router.push({ name: 'exam-admin' })">新增考试</el-button>
      <el-button type="warning" plain @click="openSysSettings">系统设置</el-button>
      <el-button type="success" plain @click="$router.push({ name: 'doc-teacher-manual' })">查看 SPJ 示例</el-button>
    </div>

    <!-- System Settings Dialog -->
    <el-dialog v-model="sysDialogVisible" title="系统设置" width="600px">
      <el-tabs type="border-card">
        <el-tab-pane label="基础设置">
          <el-form :model="sysForm" label-width="100px" class="mt-4">
            <el-form-item label="网站标题">
              <el-input v-model="sysForm.title" placeholder="例如: SKYOJ" />
            </el-form-item>
            <el-form-item label="公告信息">
              <el-input v-model="sysForm.info" type="textarea" :rows="3" placeholder="顶部滚动显示的公告内容" />
            </el-form-item>
            <el-form-item label="警告模式">
              <el-switch v-model="sysForm.warning" active-text="开启" inactive-text="关闭" />
              <div class="form-tip">开启后公告栏将显示为红色警告样式</div>
            </el-form-item>
            <el-form-item label="练习模式">
              <el-switch v-model="sysForm.practice" active-text="开启" inactive-text="关闭" />
              <div class="form-tip">关闭后学生只能进行考试 限制访问功能</div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="智能体配置 (LLM)">
          <el-form :model="sysForm" label-width="100px" class="mt-4">
            <el-form-item label="API 接口">
              <el-input v-model="sysForm.api_url" placeholder="https://api.openai.com/v1" />
              <div class="form-tip">LLM 服务的基础 URL</div>
            </el-form-item>
            <el-form-item label="API 模型">
              <el-input v-model="sysForm.api_model" placeholder="gpt-3.5-turbo" />
              <div class="form-tip">使用的模型名称</div>
            </el-form-item>
            <el-form-item label="API 密钥">
              <el-input v-model="sysForm.api_key" type="password" show-password placeholder="sk-..." />
              <div class="form-tip">用于身份验证的 API Key</div>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="sysDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveSysSettings" :loading="sysSubmitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { List, Document, User, Setting, Timer } from '@element-plus/icons-vue'
import { getSysInfo, updateSysInfo } from '@/api/sys'
import { useSysStore } from '@/stores/sys'
import { ElMessage } from 'element-plus'

const sysStore = useSysStore()
const sysDialogVisible = ref(false)
const sysSubmitting = ref(false)
const sysForm = ref({
  title: '',
  info: '',
  warning: false,
  practice: true,
  api_url: '',
  api_model: '',
  api_key: ''
})

const openSysSettings = async () => {
  sysDialogVisible.value = true
  try {
    // Fetch latest info to populate form
    const res = await getSysInfo()
    if (res) {
      sysForm.value = {
        title: res.title || 'SKYOJ',
        info: res.info || '',
        warning: res.warning === 'True' || res.warning === true,
        practice: res.practice === 'True' || res.practice === true,
        api_url: res.api_url || '',
        api_model: res.api_model || '',
        api_key: res.api_key || ''
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
    // Refresh global store
    sysStore.fetchSysInfo()
  } catch (error) {
    ElMessage.error('更新失败')
  } finally {
    sysSubmitting.value = false
  }
}
</script>

<style scoped>
.teacher-dashboard-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.dashboard-header {
  margin-bottom: 30px;
}

.dashboard-header h2 {
  font-size: 28px;
  color: #303133;
  margin-bottom: 10px;
}

.subtitle {
  color: #909399;
  font-size: 16px;
}

.dashboard-cards {
  margin-bottom: 40px;
}

.dashboard-card {
  cursor: pointer;
  height: 100%;
  transition: all 0.3s;
  border-radius: 8px;
}

.dashboard-card:hover {
  transform: translateY(-5px);
}

.card-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 20px 0;
}

.card-icon {
  margin-bottom: 15px;
}

.card-content h3 {
  margin: 10px 0;
  font-size: 18px;
  color: #303133;
}

.card-content p {
  color: #606266;
  font-size: 14px;
  line-height: 1.5;
}

.disabled-card {
  cursor: not-allowed;
  opacity: 0.7;
  background-color: #f5f7fa;
}

.disabled-card:hover {
  transform: none;
}

.quick-actions {
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.quick-actions h3 {
  margin-bottom: 20px;
  font-size: 18px;
  color: #303133;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.2;
  margin-top: 5px;
}

.mt-4 {
  margin-top: 1rem;
}
</style>
