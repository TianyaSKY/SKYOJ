import {defineStore} from 'pinia'
import {ref} from 'vue'
import request from '@/utils/request'
import {ElMessage} from 'element-plus'

function readCachedUser() {
    const cached = localStorage.getItem('user')
    if (cached === null) return null
    try {
        const value = JSON.parse(cached)
        if (value === null || (typeof value === 'object' && !Array.isArray(value))) {
            return value
        }
    } catch (error) {
        if (!(error instanceof SyntaxError)) throw error
    }
    console.warn('本地用户缓存无效，已重置用户资料')
    localStorage.removeItem('user')
    return null
}

export const useUserStore = defineStore('user', () => {
    const token = ref(localStorage.getItem('token') || '')
    const user = ref(readCachedUser())

    const login = async (loginForm) => {
        try {
            const res = await request.post('/auth/login', loginForm, {
                skipAuthErrorHandler: true
            })
            if (res.token && res.user) {
                token.value = res.token
                user.value = res.user
                localStorage.setItem('token', res.token)
                localStorage.setItem('user', JSON.stringify(res.user))
                return true
            }
            return false
        } catch (error) {
            ElMessage.error(
                error.response?.data?.message ||
                error.response?.data?.error ||
                'Login failed'
            )
            throw error
        }
    }

    const logout = () => {
        token.value = ''
        user.value = null
        localStorage.removeItem('token')
        localStorage.removeItem('user')
    }

    return {token, user, login, logout}
})
