// 后端无时区的 ISO 日期时间使用 UTC；已带时区的时间保留其偏移。
export function parseServerDate(value: unknown) {
  if (typeof value !== 'string' || !value.trim()) return null
  const text = value.trim()
  const naive = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/.test(text)
  const date = new Date(naive ? `${text}Z` : text)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatServerDateTime(value: unknown) {
  return parseServerDate(value)?.toLocaleString() || ''
}

export function formatServerDate(value: unknown) {
  return parseServerDate(value)?.toLocaleDateString() || ''
}
