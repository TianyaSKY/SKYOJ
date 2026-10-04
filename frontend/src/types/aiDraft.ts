// 对齐后端响应模型；日期时间在 JSON 协议中使用字符串。
import type { JsonValue } from './common'
export interface AskLlmBody {
  system_setting: string
  prompt: string
  output_format?: Record<string, JsonValue> | null
  context_submission_id?: number | null
}

export interface ExecuteTestGenerationBody {
  problem_id: number
  code: string
  type?: string | null
  language?: string
}

export interface SubmitDraftResponse {
  draft_id: number
  status: string
  task_type: string
  title: string
  message: string
}

export interface ExecuteGenerationResponse {
  message: string
  draft_id: number
  status: string
}

export interface DraftSummaryResponse {
  id: number
  task_type: string
  status: string
  title: string
  problem_id: number | null
  error_message: string | null
  created_at: string | null
  updated_at: string | null
  consumed_at: string | null
}

export interface DraftDetailResponse extends DraftSummaryResponse {
  request_payload: Record<string, JsonValue>
  result_payload: Record<string, JsonValue>
}

export interface DraftListResponse {
  drafts: Array<DraftSummaryResponse>
}

export interface DraftStatsResponse {
  total: number
  pending: number
  running: number
  success: number
  failed: number
  unconsumed_success: number
  in_progress: number
}

export interface ApplyDraftResponse {
  message: string
  problem_id: number
  draft_id: number
  title: string
}

export interface DraftQuery { status?: string; task_type?: string; limit?: number }
