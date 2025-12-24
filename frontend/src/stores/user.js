import {defineStore} from 'pinia'
import {ref} from 'vue'
import request from '@/utils/request'
import {ElMessage} from 'element-plus'

export const useUserStore = defineStore('user', () => {
    const token = ref(localStorage.getItem('token') || '')
    const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

    const login = async (loginForm) => {
        try {
            const res = await request.post('/auth/login', loginForm)
            if (res.token && res.user) {
                token.value = res.token
                user.value = res.user
                localStorage.setItem('token', res.token)
                localStorage.setItem('user', JSON.stringify(res.user))
                return true
            }
            return false
        } catch (error) {
            ElMessage.error(error.response?.data?.message || 'Login failed')
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
