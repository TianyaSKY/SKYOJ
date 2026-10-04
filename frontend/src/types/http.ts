import type { AxiosInstance, AxiosRequestConfig } from 'axios'

export interface BackendErrorPayload {
  code?: string
  error?: unknown
  detail?: unknown
  message?: unknown
}

// Axios 错误保留原始响应，错误报文只能经校验后读取。
export interface ApiError extends Error {
  code?: string
  backend?: unknown
  response?: { status: number; data: unknown }
  config?: AxiosRequestConfig
}

type RequestMethod = <T = unknown, D = unknown>(url: string, config?: AxiosRequestConfig<D>) => Promise<T>
type DataMethod = <T = unknown, D = unknown>(url: string, data?: D, config?: AxiosRequestConfig<D>) => Promise<T>

// 响应拦截器返回 data，保留实例的 defaults 和 interceptors 供现有调用方使用。
export interface ApiClient extends Pick<AxiosInstance, 'defaults' | 'interceptors' | 'getUri'> {
  <T = unknown, D = unknown>(config: AxiosRequestConfig<D>): Promise<T>
  <T = unknown, D = unknown>(url: string, config?: AxiosRequestConfig<D>): Promise<T>
  request: <T = unknown, D = unknown>(config: AxiosRequestConfig<D>) => Promise<T>
  get: RequestMethod
  delete: RequestMethod
  head: RequestMethod
  options: RequestMethod
  post: DataMethod
  put: DataMethod
  patch: DataMethod
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}
