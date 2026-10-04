// 对齐题解、评论和标签 HTTP 响应。
export interface SolutionListItemResponse {
  id: number
  problem_id: number
  author_id: number
  author_username: string
  title: string
  language: string | null
  is_official: boolean
  vote_count: number
  comment_count: number
  created_at: string | null
  content: string
  liked_by_me: boolean
  favorited_by_me: boolean
}

export interface SolutionDetailResponse {
  id: number
  problem_id: number
  author_id: number
  author_username: string
  title: string
  content: string
  language: string | null
  is_official: boolean
  status: string
  vote_count: number
  comment_count: number
  view_count: number
  liked_by_me: boolean
  favorited_by_me: boolean
  favorite_count: number
  created_at: string | null
  updated_at: string | null
}

export interface SolutionListResponse {
  total: number
  page: number
  page_size: number
  items: Array<SolutionListItemResponse>
}

export interface ToggleLikeResponse {
  solution_id: number
  liked: boolean
  vote_count: number
}

export interface ToggleFavoriteResponse {
  solution_id: number
  favorited: boolean
}

export interface CommentResponse {
  id: number
  solution_id: number
  user_id: number
  username: string
  content: string
  created_at: string | null
}

export interface CommentListResponse {
  total: number
  page: number
  page_size: number
  items: Array<CommentResponse>
}

export interface TagResponse {
  id: number
  slug: string
  name: string
  category: string | null
  description: string | null
}
