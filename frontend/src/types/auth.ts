// 对齐后端响应模型；日期时间在 JSON 协议中使用字符串。
export interface AuthUserResponse {
  id: number
  username: string
  role: string
}

export interface LoginResponse {
  message: string
  token: string
  user: AuthUserResponse
}
