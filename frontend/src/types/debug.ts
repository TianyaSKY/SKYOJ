// 对齐后端响应模型；日期时间在 JSON 协议中使用字符串。
export interface DebugCodeBody {
  problem_id?: number
  code?: string
  language?: string
  exam_id?: number | null
}

export interface CreateDebugRunResponse {
  message: string
  debug_run_id: number
  status: string
  exam_id: number | null
}

export interface DebugRunResponse {
  id: number
  status: string
  language: string
  case_name: string | null
  input: string | null
  expected_output: string | null
  actual_output: string | null
  error_output: string | null
  time_used_ms: number | null
  memory_used_kb: number | null
  created_at: string | null
  finished_at: string | null
  problem_id: number
  exam_id: number | null
}
