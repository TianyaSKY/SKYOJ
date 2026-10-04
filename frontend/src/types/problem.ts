// 对齐后端响应模型；日期时间在 JSON 协议中使用字符串。
export interface CreateProblemResponse {
  message: string
  problem_id: number
}

export interface ProblemListResponse {
  id: number
  title: string
  type: string
  language: string
  time_limit: number
  memory_limit: number
  test_case_status: string
  test_case_count: number
  test_case_valid_count: number
}

export interface PaginatedProblemsResponse {
  total: number
  page: number
  page_size: number
  problems: Array<ProblemListResponse>
}

export interface ProblemDetailResponse {
  id: number
  title: string
  content: string
  type: string
  language: string
  time_limit: number
  memory_limit: number
  template_code: string | null
}

export interface SearchProblemResponse {
  id: number
  title: string
  content: string
  type: string
  language: string
  time_limit: number
  memory_limit: number
}

export interface UploadTestCasesResponse {
  message: string
  files: Array<string>
}

export interface TestCaseResponse {
  name: string
  input_file: string | null
  output_file: string | null
  input_size: number | null
  output_size: number | null
  status: string
}

export interface TestCaseSummaryResponse {
  status: string
  total_count: number
  valid_count: number
  invalid_count: number
  file_count: number
  total_size: number
  ignored_files: Array<string>
  cases: Array<TestCaseResponse>
}

export interface ProblemQuery { page?: number; page_size?: number; tag_id?: number; problem_type?: 'acm' | 'oop' | 'kaggle' }
export interface SearchQuery { query?: string; top_k?: number; tag_id?: number; problem_type?: 'acm' | 'oop' | 'kaggle' }
