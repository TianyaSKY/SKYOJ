import { cachedUserSchema, type CachedUser } from '@/schemas/user'
import type { LoginInput } from '@/schemas/auth'
import type { LoginResponse } from '@/types/auth'
import { isRecord } from '@/types/http'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '@/utils/request'
import { ElMessage } from 'element-plus'

function readCachedUser(): CachedUser | null {
  const cached = localStorage.getItem('user')
  if (cached === null) return null
  try {
    const value: unknown = JSON.parse(cached)
    if (value === null) return null
    const parsed = cachedUserSchema.safeParse(value)
    if (parsed.success) return parsed.data
  } catch (error) {
    if (!(error instanceof SyntaxError)) throw error
  }
  console.warn('本地用户缓存无效，已重置用户资料')
  localStorage.removeItem('user')
  return null
}

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<CachedUser | null>(readCachedUser())

  // 登录和考试会话切换共用更新入口，保持响应式状态与请求缓存一致。
  const setToken = (value: string) => {
    token.value = value
    localStorage.setItem('token', value)
  }

  const login = async (loginForm: LoginInput): Promise<boolean> => {
    try {
      const res = await request.post<LoginResponse>('/auth/login', loginForm, {
        skipAuthErrorHandler: true,
      })
      if (res.token && res.user) {
        setToken(res.token)
        user.value = cachedUserSchema.parse(res.user)
        localStorage.setItem('user', JSON.stringify(res.user))
        return true
      }
      return false
    } catch (error) {
      const response = isRecord(error) && isRecord(error.response) ? error.response : null
      const data = response && isRecord(response.data) ? response.data : null
      const message = data?.message || data?.error
      ElMessage.error(typeof message === 'string' ? message : 'Login failed')
      throw error
    }
  }

  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { token, user, setToken, login, logout }
})
