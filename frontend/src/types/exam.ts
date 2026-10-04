// 对齐后端响应模型；日期时间在 JSON 协议中使用字符串。
export interface ExamProblemItem {
  problem_id: number
  display_id: string | null
  score: number
  title: string
}

export interface MonitorSubmissionInfo {
  submission_id: number | null
  status: string
  score: number
  time: string | null
}

export interface MonitorProblemInfo {
  problem_id: number
  display_id: string | null
  max_score: number
}

export interface MonitorEntry {
  user_id: number
  username: string
  total_score: number
  submissions: Record<number, MonitorSubmissionInfo>
}

export interface RankProblemStats {
  solved: boolean
  failed_attempts: number
  time: number
  pending_attempts?: number
}

export interface RankProblemInfo {
  problem_id: number
  display_id: string | null
}

export interface RankEntry {
  user_id: number
  username: string
  solved: number
  penalty: number
  problems: Record<number, RankProblemStats>
}

export interface ExamResponse {
  id: number
  title: string
  description: string
  start_time: string
  end_time: string
  contest_type: string
  freeze_minutes: number | null
  is_visible: boolean
  created_by: number
}

export interface ExamListResponse extends ExamResponse {
  problem_count: number
  submission_count: number
}

export interface ExamDetailResponse extends ExamResponse {
  has_password: boolean
  problems: Array<ExamProblemItem>
}

export interface ExamTokenResponse {
  message: string
  token: string
}

export interface EnterExamResponse extends ExamTokenResponse {
  exam_id: number
}

export interface MonitorResponse {
  exam_title: string
  problems: Array<MonitorProblemInfo>
  users: Array<MonitorEntry>
}

export interface RankResponse {
  exam_title: string
  problems: Array<RankProblemInfo>
  rank: Array<RankEntry>
}

export interface ExamProblemStatusResponse {
  problem_id: number
  display_id: string | null
  title: string
  max_score: number
  status: string
  current_score: number
  last_submitted_at: string | null
}

export interface AddExamProblem {
  problem_id: number
  display_id?: string | null
  score?: number
}
