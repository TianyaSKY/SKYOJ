import request from '@/utils/request'

export function getSysInfo() {
  return request({
    url: '/sys/info',
    method: 'get'
  })
}

export function updateSysInfo(data) {
  return request({
    url: '/sys/info',
    method: 'put',
    data
  })
}
