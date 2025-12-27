<template>
  <el-menu
      :default-active="activeIndex"
      :ellipsis="false"
      class="el-menu-demo"
      mode="horizontal"
      router
  >
    <el-menu-item index="/" class="brand-item">
      <span class="brand-title">{{ sysStore.title }}</span>
    </el-menu-item>
    <div class="flex-grow"/>
    <el-menu-item index="/">首页</el-menu-item>
    <template v-if="isPracticeMode || isTeacher">
      <el-menu-item index="/problems">题库</el-menu-item>
      <el-menu-item index="/datasets">公开数据集</el-menu-item>
    </template>
    <el-menu-item v-if="!isPracticeMode" index="/exam" class="exam-menu-item">
      <el-icon><Timer /></el-icon>
      考试中心
    </el-menu-item>

    <div class="user-actions">
      <el-dropdown v-if="isLoggedIn" @command="handleCommand">
        <span class="el-dropdown-link">
          <el-avatar :size="32" :src="userAvatar" class="user-avatar-nav">
            {{ username.charAt(0).toUpperCase() }}
          </el-avatar>
          <span class="username">{{ username }}</span>
          <el-icon class="el-icon--right"><ArrowDown/></el-icon>
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
import {computed} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {useUserStore} from '@/stores/user'
import {useSysStore} from '@/stores/sys'
import {ArrowDown, Timer} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const sysStore = useSysStore()

const activeIndex = computed(() => route.path)

const isLoggedIn = computed(() => !!userStore.token)
const username = computed(() => userStore.user?.username || 'User')
const isTeacher = computed(() => userStore.user?.role === 'teacher')
const isPracticeMode = computed(() => sysStore.practice !== false && sysStore.practice !== 'False')

// If backend provides avatar URL, use it; otherwise empty string to trigger slot content
const userAvatar = computed(() => userStore.user?.avatar ? `/api${userStore.user?.avatar}` : '')

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

.brand-item {
  opacity: 1 !important;
  cursor: pointer;
}

.brand-title {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--el-color-primary);
  letter-spacing: 1px;
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

.exam-menu-item {
  color: var(--el-color-danger) !important;
  font-weight: bold;
}
</style>
