<template>
  <div class="register-container">
    <el-card class="register-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>Create Your SKYOJ Account</h2>
        </div>
      </template>
      <el-form
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          label-position="top"
          @submit.prevent="handleRegister"
      >
        <el-form-item label="Username" prop="username">
          <el-input
              v-model="registerForm.username"
              :prefix-icon="User"
              clearable
              placeholder="Enter your username"
              size="large"
          />
        </el-form-item>
        <el-form-item label="Password" prop="password">
          <el-input
              v-model="registerForm.password"
              :prefix-icon="Lock"
              clearable
              placeholder="Enter your password"
              show-password
              size="large"
              type="password"
          />
        </el-form-item>
        <el-form-item label="Confirm Password" prop="confirmPassword">
          <el-input
              v-model="registerForm.confirmPassword"
              :prefix-icon="Lock"
              clearable
              placeholder="Confirm your password"
              show-password
              size="large"
              type="password"
          />
        </el-form-item>
        <el-form-item>
          <el-button
              :loading="loading"
              class="register-button"
              native-type="submit"
              size="large"
              type="primary"
          >
            Register
          </el-button>
        </el-form-item>
      </el-form>
      <div class="login-link">
        <span>Already have an account? </span>
        <el-link type="primary" @click="$router.push('/login')">Sign in</el-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import {reactive, ref} from 'vue'
import {useRouter} from 'vue-router'
import {ElMessage} from 'element-plus'
import {Lock, User} from '@element-plus/icons-vue'
import {register} from '@/api/user'

const router = useRouter()
const registerFormRef = ref(null)
const loading = ref(false)

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})

const validatePass = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('Please input the password again'))
  } else if (value !== registerForm.password) {
    callback(new Error("Passwords don't match!"))
  } else {
    callback()
  }
}

const registerRules = reactive({
  username: [
    {required: true, message: 'Please enter your username', trigger: 'blur'},
    {min: 3, max: 20, message: 'Length should be 3 to 20', trigger: 'blur'},
  ],
  password: [
    {required: true, message: 'Please enter your password', trigger: 'blur'},
    {min: 6, message: 'Password must be at least 6 characters long', trigger: 'blur'},
  ],
  confirmPassword: [
    {required: true, validator: validatePass, trigger: 'blur'},
  ],
})

const handleRegister = async () => {
  if (!registerFormRef.value) return
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await register({
          username: registerForm.username,
          password: registerForm.password,
          // Role defaults to 'student' on the backend according to api_manual.md
        })
        ElMessage.success('Registration successful! Please log in.')
        router.push('/login')
      } catch (error) {
        // Error message is likely handled by the request interceptor
        console.error('Registration failed:', error)
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
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 150px);
  background-color: #f0f2f5;
}

.register-card {
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

.register-button {
  width: 100%;
}

.login-link {
  margin-top: 15px;
  text-align: center;
  font-size: 0.9rem;
}
</style>
