// 对齐后端响应模型。
export interface ProblemPassRateResponse {
  problem_id: number
  title: string
  pass_rate: number
  total: number
}

export interface ProblemDifficultyResponse {
  problem_id: number
  title: string
  difficulty: number
  total: number
}

export interface DailySubmissionCountResponse {
  date: string
  count: number
}

export interface PlatformAnalyticsResponse {
  total_submissions: number
  total_accepted: number
  global_pass_rate: number
  total_problems: number
  problem_pass_rates: Array<ProblemPassRateResponse>
  problem_difficulty: Array<ProblemDifficultyResponse>
  daily_submissions: Array<DailySubmissionCountResponse>
}
