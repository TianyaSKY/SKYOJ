<template>
  <el-menu
    :default-active="activeIndex"
    class="el-menu-demo"
    mode="horizontal"
    :ellipsis="false"
    router
  >
    <el-menu-item index="/">
      <img
        style="width: 100px"
        src="@/assets/logo.svg"
        alt="SKYOJ Logo"
      />
    </el-menu-item>
    <div class="flex-grow" />
    <el-menu-item index="/">首页</el-menu-item>
    <el-menu-item index="/problems">题库</el-menu-item>
    <el-menu-item index="/datasets">公开数据集</el-menu-item>

    <div class="user-actions">
      <el-dropdown v-if="isLoggedIn" @command="handleCommand">
        <span class="el-dropdown-link">
          <el-avatar :size="32" :src="userAvatar" class="user-avatar-nav">
            {{ username.charAt(0).toUpperCase() }}
          </el-avatar>
          <span class="username">{{ username }}</span>
          <el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">个人中心</el-dropdown-item>
            <el-dropdown-item v-if="isTeacher" command="teacher-dashboard">教师工作台</el-dropdown-item>
            <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <div v-else>
        <el-button type="primary" @click="$router.push('/login')">登录</el-button>
        <el-button @click="$router.push('/register')">注册</el-button>
      </div>
    </div>
  </el-menu>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ArrowDown } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const activeIndex = computed(() => route.path)

const isLoggedIn = computed(() => !!userStore.token)
const username = computed(() => userStore.user?.username || 'User')
const isTeacher = computed(() => userStore.user?.role === 'teacher')
// If backend provides avatar URL, use it; otherwise empty string to trigger slot content
const userAvatar = computed(() => userStore.user?.avatar || '')

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'teacher-dashboard') {
    router.push('/admin/dashboard')
  }
}
</script>

<style scoped>
.flex-grow {
  flex-grow: 1;
}
.user-actions {
  display: flex;
  align-items: center;
  padding: 0 20px;
}
.el-dropdown-link {
  cursor: pointer;
  display: flex;
  align-items: center;
  outline: none;
}
.username {
  margin-left: 8px;
  font-weight: 500;
}
.user-avatar-nav {
  background-color: var(--el-color-primary);
  color: white;
}
</style>
