import axios from 'axios'
import {ElMessage, ElMessageBox} from 'element-plus'
import router from '@/router'

const service = axios.create({
    baseURL: '/api',
    timeout: 5000
})

// Request interceptor
service.interceptors.request.use(
    config => {
        const token = localStorage.getItem('token')
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`
        }
        return config
    },
    error => {
        return Promise.reject(error)
    }
)

// Response interceptor
service.interceptors.response.use(
    response => {
        return response.data
    },
    error => {
        console.error('Request error:', error)
        if (error.response && error.response.status === 401) {
            ElMessageBox.confirm(
                '登录状态已失效，您可以继续留在该页面，或者重新登录',
                '系统提示',
                {
                    confirmButtonText: '重新登录',
                    cancelButtonText: '取消',
                    type: 'warning'
                }
            ).then(() => {
                localStorage.removeItem('token')
                localStorage.removeItem('user')
                router.push('/login')
            })
        } else {
            ElMessage.error(error.message || 'Request failed')
        }
        return Promise.reject(error)
    }
)

export default service
