// 对齐后端响应模型；日期时间在 JSON 协议中使用字符串。
export interface UserProfileResponse {
  id: number
  username: string
  role: string
  avatar: string | null
}

export interface UploadAvatarResponse {
  message: string
  avatar: string | null
}

export interface UserSubmissionResponse {
  id: number
  problem_id: number
  problem_title: string
  status: string
  score: number
  language: string
  created_at: string | null
  exam_id: number | null
}
