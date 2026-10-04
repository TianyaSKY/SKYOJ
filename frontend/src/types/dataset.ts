// 对齐后端响应模型；日期时间在 JSON 协议中使用字符串。
export interface DatasetResponse {
  id: number
  name: string
  description: string | null
  uploader: string
  file_size: string
  created_at: string | null
  download_url: string
  status: string
}

export interface PaginatedDatasetsResponse {
  total: number
  page: number
  page_size: number
  datasets: Array<DatasetResponse>
}

export interface UploadDatasetResponse {
  message: string
  dataset: DatasetResponse
}
