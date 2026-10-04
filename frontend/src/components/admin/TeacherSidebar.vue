<template>
  <aside class="teacher-sidebar">
    <div class="sidebar-brand">
      <el-icon><School /></el-icon><span>教师后台</span>
    </div>
    <el-menu :default-active="route.path" router class="sidebar-menu">
      <el-menu-item index="/admin/dashboard"
        ><el-icon><Odometer /></el-icon><span>概览</span></el-menu-item
      >
      <el-divider content-position="left">教学内容</el-divider>
      <el-menu-item index="/admin/problems"
        ><el-icon><Collection /></el-icon><span>题目管理</span></el-menu-item
      >
      <el-menu-item index="/admin/datasets"
        ><el-icon><FolderOpened /></el-icon><span>数据集</span></el-menu-item
      >
      <el-divider content-position="left">考试管理</el-divider>
      <el-menu-item index="/admin/exams"
        ><el-icon><Timer /></el-icon><span>考试管理</span></el-menu-item
      >
      <el-divider content-position="left">提交与查重</el-divider>
      <el-menu-item index="/admin/submissions"
        ><el-icon><Monitor /></el-icon><span>提交记录</span></el-menu-item
      >
      <el-menu-item v-if="ENABLE_PLAGIARISM" index="/admin/plagiarism"
        ><el-icon><Search /></el-icon><span>查重管理</span></el-menu-item
      >
      <el-divider content-position="left">系统</el-divider>
      <el-menu-item index="/admin/settings"
        ><el-icon><Setting /></el-icon><span>系统设置</span></el-menu-item
      >
      <el-menu-item index="/docs/teacher-manual"
        ><el-icon><Reading /></el-icon><span>教师手册</span></el-menu-item
      >
    </el-menu>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import {
  Collection,
  FolderOpened,
  Monitor,
  Odometer,
  Reading,
  School,
  Search,
  Setting,
  Timer,
} from '@element-plus/icons-vue'
import { ENABLE_PLAGIARISM } from '@/utils/featureFlags'
const route = useRoute()
</script>

<style scoped>
.teacher-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid var(--el-border-color-light);
}
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 20px 16px;
  color: var(--el-color-primary);
  font-size: 18px;
  font-weight: 700;
}
.sidebar-brand .el-icon {
  font-size: 22px;
}
.sidebar-menu {
  border-right: 0;
}
.sidebar-menu :deep(.el-divider__text) {
  font-size: 11px;
  color: #909399;
}
@media (max-width: 768px) {
  .teacher-sidebar {
    width: 64px;
  }
  .sidebar-brand {
    justify-content: center;
    padding: 20px 0;
  }
  .sidebar-brand span,
  .sidebar-menu :deep(.el-menu-item span),
  .sidebar-menu :deep(.el-divider) {
    display: none;
  }
  .sidebar-menu :deep(.el-menu-item) {
    justify-content: center;
    padding: 0;
  }
}
</style>
