// 对齐后端响应模型；日期时间在 JSON 协议中使用字符串。
export interface CaseResult {
  case_name: string
  status: string
  time_used_ms?: number | null
  memory_used_kb?: number | null
  input_data?: string | null
  expected_output?: string | null
  actual_output?: string | null
  error_output?: string | null
}

export interface SubmitCodeResponse {
  message: string
  submission_id: number
  status: string
  exam_id: number | null
}

export interface SubmissionListResponse {
  id: number
  user_id: number
  username: string
  problem_id: number
  exam_id: number | null
  status: string
  score: number
  language: string
  created_at: string | null
}

export interface PaginatedSubmissionsResponse {
  total: number
  pages: number
  current_page: number
  submissions: Array<SubmissionListResponse>
}

export interface SubmissionDetailResponse {
  id: number
  status: string
  score: number
  log: string | null
  code: string | null
  language: string
  exam_id: number | null
  created_at: string | null
  case_results: Array<CaseResult>
}

export interface SubmitCodeBody {
  problem_id: number
  code: string
  language: string
  exam_id?: number | null
}
export interface SubmissionQuery {
  problem_id?: number
  user_id?: number
  username?: string
  exam_id?: number
  status?: string
  page?: number
  per_page?: number
}

// 管理页面兼容历史 items/data 包装与直接数组响应。
export interface LegacySubmissionsResponse {
  total?: number
  items?: SubmissionListResponse[]
  data?: SubmissionListResponse[]
}
export type SubmissionsResponse =
  | PaginatedSubmissionsResponse
  | LegacySubmissionsResponse
  | SubmissionListResponse[]
