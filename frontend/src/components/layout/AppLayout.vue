<template>
  <div :class="{'answer-workspace-layout': answerWorkspaceActive}" class="common-layout">
    <el-container direction="vertical">
      <div v-if="sysStore.info" :class="{'warning-mode': sysStore.warning}" class="sys-info-bar"><div class="scrolling-text">{{ sysStore.info }}</div></div>
      <el-header class="header-container"><NavBar/></el-header>
      <el-main :class="{'admin-main': isTeacherAdmin, 'answer-workspace-main': answerWorkspaceActive}" class="main-container">
        <div v-if="isTeacherAdmin" class="admin-shell"><TeacherSidebar/><section class="admin-content"><router-view/></section></div>
        <router-view v-else/>
      </el-main>
      <el-footer v-if="!answerWorkspaceActive" class="footer-container"><p>&copy; {{ new Date().getFullYear() }} {{ sysStore.title }}. All rights reserved.</p></el-footer>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import {computed, onMounted, provide, ref} from 'vue'
import {useRoute} from 'vue-router'
import NavBar from './NavBar.vue'
import TeacherSidebar from '@/components/admin/TeacherSidebar.vue'
import {useSysStore} from '@/stores/sys'
import {useUserStore} from '@/stores/user'

const route = useRoute()
const sysStore = useSysStore()
const userStore = useUserStore()
const isTeacherAdmin = computed(() => userStore.user?.role === 'teacher' && (route.path.startsWith('/admin') || route.path === '/docs/teacher-manual'))
const answerWorkspaceActive = ref(false)

provide('setAnswerWorkspaceActive', (active: boolean) => {
  answerWorkspaceActive.value = active
})

onMounted(() => sysStore.fetchSysInfo())
</script>

<style scoped>
.common-layout { min-height: 100vh; display: flex; flex-direction: column; }
.answer-workspace-layout { height: 100dvh; min-height: 100dvh; overflow: hidden; }
.answer-workspace-layout :deep(.el-container) { height: 100%; min-height: 0; overflow: hidden; }
.header-container { padding: 0; height: auto; border-bottom: 1px solid var(--el-menu-border-color); }
.main-container { flex: 1; width: 100%; margin: 0 auto; padding: 20px; }
.main-container.admin-main { padding: 0; }
.main-container.answer-workspace-main { min-height: 0; padding: 0; overflow: hidden; }
.admin-shell { display: flex; min-height: calc(100vh - 100px); }
.admin-content { flex: 1; min-width: 0; padding: 32px; background: #f7f8fa; }
.footer-container { text-align: center; padding: 20px; color: var(--el-text-color-secondary); border-top: 1px solid var(--el-border-color-light); }
.sys-info-bar { background-color: #e6f7ff; color: #1890ff; height: 30px; line-height: 30px; overflow: hidden; position: relative; width: 100%; }
.sys-info-bar.warning-mode { background-color: #fff1f0; color: #f5222d; }
.scrolling-text { position: absolute; white-space: nowrap; animation: scroll-left 20s linear infinite; padding-left: 100%; display: inline-block; }
@keyframes scroll-left { 0% { transform: translateX(0); } 100% { transform: translateX(-100%); } }
@media (max-width: 768px) { .admin-content { padding: 20px 12px; } }
</style>
