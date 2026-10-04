// 路由参数是外部文本，仅接受单个正整数 ID，拒绝数组、科学计数法和越界值。
export function parseRouteId(value: unknown): number | null {
  if (typeof value !== 'string' || !/^\d+$/.test(value)) return null
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}
