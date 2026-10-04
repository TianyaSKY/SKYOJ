// 对齐后端响应模型。
export interface WrongBookStatsResponse {
  total: number
  unresolved: number
  reviewed: number
  accepted: number
}

export interface WrongBookItemResponse {
  id: number
  problem_id: number
  problem_title: string
  submission_id: number | null
  first_wrong_at: string | null
  latest_wrong_at: string | null
  accepted: boolean
  reviewed: boolean
}

export interface WrongBookListResponse {
  total: number
  page: number
  page_size: number
  items: Array<WrongBookItemResponse>
}

export interface ToggleReviewResponse {
  id: number
  reviewed: boolean
}
