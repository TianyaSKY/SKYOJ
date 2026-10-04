import { expect, it } from 'vitest'
import { parseRouteId } from '../route'

it.each(['1', '42', '0002'])('路由 ID %s 解析为安全正整数', (value) => {
  expect(parseRouteId(value)).toBe(Number(value))
})
it.each([undefined, null, '', '0', '-1', '1.5', '1e3', ' 1 ', ['1'], 1, '9007199254740992'])(
  '无效路由 ID %s 返回 null',
  (value) => {
    expect(parseRouteId(value)).toBeNull()
  },
)
