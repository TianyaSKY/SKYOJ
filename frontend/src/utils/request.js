import axios from 'axios'
import { ElMessageBox } from 'element-plus'
import router from '@/router'

const tokenErrorCodes = new Set([
    'AUTH_REQUIRED', 'AUTH_TOKEN_EXPIRED', 'AUTH_INVALID_TOKEN'
])
let isHandlingAuthError = false

const service = axios.create({
    baseURL: '/api',
    timeout: 30000
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
        // 后端统一错误信封：业务异常返回 {code, error}；HTTPException 返回 {code, detail}。
        // 兼容老接口（只有 {error} 或 {detail}），把 code 也补到错误对象上方便调用方判断。
        const data = error.response?.data || {}
        const code = data.code
        const message = data.error || data.detail || error.message || '请求失败'

        // 401 登录态失效：弹窗让用户重新登录。
        // 触发条件：后端返回 AUTH_REQUIRED / AUTH_TOKEN_EXPIRED / AUTH_INVALID_TOKEN，
        // 或 HTTP 401 且没有显式 code（兜底）。
        const isAuthError = tokenErrorCodes.has(code) || (!code && error.response?.status === 401)
        if (isAuthError && !isHandlingAuthError) {
            isHandlingAuthError = true
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
                if (router.currentRoute.value.name !== 'login') {
                    router.push('/login')
                }
            }).finally(() => {
                isHandlingAuthError = false
            })
        }

        // 把后端报文挂到错误对象上，方便上层做更精细的提示（例如展示 retry_after）。
        error.backend = data
        error.code = code
        error.message = message
        return Promise.reject(error)
    }
)

export default service
