import type { JsonValue } from './common'

export interface SystemConfig {
  title?: string
  practice?: boolean | 'True' | 'False'
  info?: string
  warning?: boolean | 'True' | 'False'
  llm_env_ready?: boolean
  llm_api_url?: string
  llm_model_name?: string
  [key: string]: JsonValue | undefined
}
export interface UpdateSysConfigResponse {
  message: string
  updated_keys: Array<string>
  skipped_keys: Array<string>
}

export interface SystemStatisticsResponse {
  today_submissions: number
  total_problems: number
  total_users: number
  exams_in_period: number
}
