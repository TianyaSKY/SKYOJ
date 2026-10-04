import 'axios'

declare module 'axios' {
  interface AxiosRequestConfig {
    skipAuthErrorHandler?: boolean
  }
}
