import { parseServerDate } from './date'

export function getExamTiming(exam, now) {
  const start = parseServerDate(exam.start_time)?.getTime()
  const end = parseServerDate(exam.end_time)?.getTime()
  if (start == null || end == null || end <= start) {
    return { phase: 'unknown', remainingSeconds: 0 }
  }
  if (now < start) return { phase: 'upcoming', remainingSeconds: Math.ceil((start - now) / 1000) }
  if (now < end) return { phase: 'ongoing', remainingSeconds: Math.ceil((end - now) / 1000) }
  return { phase: 'ended', remainingSeconds: 0 }
}
