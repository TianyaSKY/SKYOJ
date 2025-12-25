import request from '@/utils/request'

/**
 * Get all submissions with filters and pagination.
 * @param {Object} params - Filter parameters: problem_id, user_id, username, exam_id, status, page, per_page
 */
export function getSubmissions(params) {
  return request({
    url: '/submissions',
    method: 'get',
    params
  })
}
