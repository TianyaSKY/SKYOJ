<template>
  <div class="login-container">
    <el-card class="login-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>Login to SKYOJ</h2>
        </div>
      </template>
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="Username" prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="Enter your username"
            size="large"
            :prefix-icon="User"
            clearable
          />
        </el-form-item>
        <el-form-item label="Password" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="Enter your password"
            size="large"
            :prefix-icon="Lock"
            show-password
            clearable
          />
        </el-form-item>
        <el-form-item>
          <div class="form-actions">
            <el-checkbox v-model="loginForm.rememberMe">Remember me</el-checkbox>
            <el-link type="primary" :underline="false">Forgot password?</el-link>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            class="login-button"
            size="large"
            native-type="submit"
            :loading="loading"
          >
            Login
          </el-button>
        </el-form-item>
      </el-form>
      <div class="register-link">
        <span>Don't have an account? </span>
        <el-link type="primary" @click="$router.push('/register')">Sign up now</el-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
  rememberMe: false,
})

const loginRules = reactive({
  username: [{ required: true, message: 'Please enter your username', trigger: 'blur' }],
  password: [
    { required: true, message: 'Please enter your password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters long', trigger: 'blur' },
  ],
})

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await userStore.login({
          username: loginForm.username,
          password: loginForm.password
        })
        ElMessage.success('Login successful!')
        router.push('/')
      } catch (error) {
        // Error handling is done in the store or interceptor, but we can add specific UI logic here if needed
        console.error(error)
      } finally {
        loading.value = false
      }
    } else {
      ElMessage.error('Please check your input.')
      return false
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 150px); /* Adjust based on header/footer height */
  background-color: #f0f2f5;
}

.login-card {
  width: 400px;
  border-radius: 8px;
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--el-text-color-primary);
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.login-button {
  width: 100%;
}

.register-link {
  margin-top: 15px;
  text-align: center;
  font-size: 0.9rem;
}
</style>
