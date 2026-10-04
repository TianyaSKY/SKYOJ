import { expect, it } from 'vitest'
import { parseServerDate, formatServerDateTime, formatServerDate } from '../date'

it.each([
  '2026-06-15T10:20:30',
  '2026-06-15T10:20:30Z',
  '2026-06-15T18:20:30+08:00',
  ' 2026-06-15T10:20:30 ',
])('服务器时间 %s 表示同一 UTC 时刻', (value) => {
  expect(parseServerDate(value)?.toISOString()).toBe('2026-06-15T10:20:30.000Z')
  expect(formatServerDateTime(value)).toBe(new Date('2026-06-15T10:20:30Z').toLocaleString())
  expect(formatServerDate(value)).toBe(new Date('2026-06-15T10:20:30Z').toLocaleDateString())
})
it('保留服务器时间的小数秒', () => {
  expect(parseServerDate('2026-06-15T10:20:30.123456')?.getTime()).toBe(
    Date.parse('2026-06-15T10:20:30.123Z'),
  )
})
it.each([null, undefined, '', '  ', 'invalid', 0])(
  '无效时间 %s 不渲染 Invalid Date 或抛出异常',
  (value) => {
    expect(parseServerDate(value)).toBeNull()
    expect(formatServerDateTime(value)).toBe('')
    expect(formatServerDate(value)).toBe('')
  },
)
