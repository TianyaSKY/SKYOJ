import axios from 'axios'
import { ElMessageBox } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/stores/user'

const tokenErrorCodes = new Set([
    'AUTH_REQUIRED', 'AUTH_TOKEN_EXPIRED', 'AUTH_INVALID_TOKEN'
])
let isHandlingAuthError = false

// 只提取可读消息，保留字段路径；不把校验错误中的 input 等原始数据拼进提示。
function readableMessage(value, depth = 0) {
    if (typeof value === 'string') return value.trim()
    if (!value || typeof value !== 'object' || depth >= 4) return ''
    if (Array.isArray(value)) {
        return value.map(item => readableMessage(item, depth + 1)).filter(Boolean).join('；')
    }
    if (typeof value.msg === 'string' && Array.isArray(value.loc)) {
        const location = ['body', 'query', 'path', 'header', 'cookie'].includes(value.loc[0])
            ? value.loc.slice(1) : value.loc
        const field = location.filter(part => typeof part === 'string' || typeof part === 'number').join('.')
        const message = value.msg.trim()
        return message ? (field ? `${field}: ${message}` : message) : ''
    }
    for (const key of ['error', 'detail', 'message', 'msg']) {
        const message = readableMessage(value[key], depth + 1)
        if (message) return message
    }
    return ''
}

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
        const message = readableMessage(data.error) || readableMessage(data.detail)
            || readableMessage(data.message) || readableMessage(error.message) || '请求失败'

        // 401 登录态失效：弹窗让用户重新登录。
        // 触发条件：后端返回 AUTH_REQUIRED / AUTH_TOKEN_EXPIRED / AUTH_INVALID_TOKEN，
        // 或 HTTP 401 且没有显式 code（兜底）。
        const isAuthError = tokenErrorCodes.has(code) || (!code && error.response?.status === 401)
        if (isAuthError && !isHandlingAuthError && !error.config?.skipAuthErrorHandler) {
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
                useUserStore().logout()
                if (router.currentRoute.value.name !== 'login') {
                    return router.push('/login')
                }
            }).catch(error => {
                // 取消和关闭是正常交互；其他异常保留诊断信息。
                if (error !== 'cancel' && error !== 'close') {
                    console.error('登录失效恢复失败', error)
                }
            }).finally(() => {
                isHandlingAuthError = false
            })
        }

        // 把后端报文挂到错误对象上，方便上层做更精细的提示（例如展示 retry_after）。
        error.backend = data
        if (code) error.code = code
        error.message = message
        return Promise.reject(error)
    }
)

export default service
