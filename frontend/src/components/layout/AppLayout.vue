<template>
  <div class="common-layout">
    <el-container direction="vertical">
      <el-header class="header-container">
        <NavBar />
      </el-header>
      <el-main class="main-container">
        <router-view />
      </el-main>
      <el-footer class="footer-container">
        <p>&copy; {{ new Date().getFullYear() }} SKYOJ. All rights reserved.</p>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup>
import NavBar from './NavBar.vue'
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
</style>
