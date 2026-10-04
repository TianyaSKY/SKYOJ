<template>
  <div class="settings-container">
    <div class="page-header">
      <h1>系统设置</h1>
      <p>管理平台公告、运行模式及系统维护操作。</p>
    </div>
    <el-tabs type="border-card">
      <el-tab-pane label="基础设置">
        <el-form :model="form" label-position="top">
          <el-form-item label="网站标题"><el-input v-model="form.title" /></el-form-item>
          <el-form-item label="公告内容"><el-input v-model="form.info" :rows="3" type="textarea" /></el-form-item>
          <el-form-item label="运行模式"><el-switch v-model="form.practice" active-text="练习模式" inactive-text="考试模式" /></el-form-item>
          <el-form-item label="公告样式">
            <el-radio-group v-model="form.warning"><el-radio :label="false">普通</el-radio><el-radio :label="true">警告</el-radio></el-radio-group>
          </el-form-item>
          <el-button :loading="saving" type="primary" @click="save">保存配置</el-button>
        </el-form>
      </el-tab-pane>
      <el-tab-pane label="高级维护">
        <el-alert title="危险操作区：重建索引期间，搜索服务可能暂时受到影响。" type="warning" :closable="false" show-icon />
        <el-button v-if="ENABLE_SEMANTIC_SEARCH" class="maintenance-button" :loading="rebuilding" type="warning" @click="rebuild">立即重建搜索索引</el-button>
        <el-empty v-else description="语义搜索功能当前未启用" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import {onMounted, ref} from 'vue'
import {ElMessage, ElMessageBox} from 'element-plus'
import {getSysInfo, rebuildIndex, updateSysInfo} from '@/api/sys'
import {useSysStore} from '@/stores/sys'
import {ENABLE_SEMANTIC_SEARCH} from '@/utils/featureFlags'

const sysStore = useSysStore()
const saving = ref(false)
const rebuilding = ref(false)
const form = ref({title: '', info: '', warning: false, practice: true})

onMounted(async () => {
  try {
    const res = await getSysInfo()
    form.value = {
      title: res.title || 'SKYOJ', info: res.info || '',
      warning: res.warning === 'True' || res.warning === true,
      practice: res.practice === 'True' || res.practice === true
    }
  } catch {
    ElMessage.error('获取系统配置失败')
  }
})

const save = async () => {
  saving.value = true
  try {
    await updateSysInfo(form.value)
    await sysStore.fetchSysInfo()
    ElMessage.success('系统配置已更新')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const rebuild = async () => {
  try {
    await ElMessageBox.confirm('重建索引可能暂时影响搜索服务，是否继续？', '确认重建搜索索引', {type: 'warning'})
    rebuilding.value = true
    await rebuildIndex()
    ElMessage.success('索引重建任务已提交')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('索引重建失败')
  } finally {
    rebuilding.value = false
  }
}
</script>

<style scoped>
.settings-container { max-width: 900px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-header h1 { margin: 0 0 8px; }
.page-header p { margin: 0; color: #909399; }
.maintenance-button { margin-top: 24px; }
</style>
