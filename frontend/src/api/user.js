import request from '@/utils/request'

/**
 * Get the submission history for the currently logged-in user.
 * The user is identified by the token sent in the request header.
 */
export function getUserSubmissions() {
  return request({
    url: '/user/submissions', // Assumes the blueprint is mounted at /user
    method: 'get'
  })
}

export function register(data) {
  return request({
    url: '/auth/register',
    method: 'post',
    data
  })
}
