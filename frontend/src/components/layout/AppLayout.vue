<template>
  <div class="common-layout">
    <el-container direction="vertical">
      <div v-if="sysStore.info" class="sys-info-bar" :class="{ 'warning-mode': sysStore.warning }">
        <div class="scrolling-text">
          {{ sysStore.info }}
        </div>
      </div>
      <el-header class="header-container">
        <NavBar />
      </el-header>
      <el-main class="main-container">
        <router-view />
      </el-main>
      <el-footer class="footer-container">
        <p>&copy; {{ new Date().getFullYear() }} {{ sysStore.title }}. All rights reserved.</p>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import NavBar from './NavBar.vue'
import { useSysStore } from '@/stores/sys'
import { onMounted } from 'vue'

const sysStore = useSysStore()

onMounted(() => {
  sysStore.fetchSysInfo()
})
</script>

<style scoped>
.common-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header-container {
  padding: 0;
  height: auto;
  border-bottom: 1px solid var(--el-menu-border-color);
}

.main-container {
  flex: 1;
  width: 100%;
  margin: 0 auto;
  padding: 20px;
}

.footer-container {
  text-align: center;
  padding: 20px;
  color: var(--el-text-color-secondary);
  border-top: 1px solid var(--el-border-color-light);
}

.sys-info-bar {
  background-color: #e6f7ff;
  color: #1890ff;
  height: 30px;
  line-height: 30px;
  overflow: hidden;
  position: relative;
  width: 100%;
}

.sys-info-bar.warning-mode {
  background-color: #fff1f0;
  color: #f5222d;
}

.scrolling-text {
  position: absolute;
  white-space: nowrap;
  animation: scroll-left 20s linear infinite;
  padding-left: 100%; /* Start from right */
  display: inline-block;
}

@keyframes scroll-left {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-100%);
  }
}
</style>
