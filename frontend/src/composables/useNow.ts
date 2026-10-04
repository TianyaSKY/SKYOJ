import { onMounted, onUnmounted, ref } from 'vue'

// 响应式时钟让页面状态随时间变化，离开页面时停止刷新。
export function useNow() {
  const now = ref(Date.now())
  let timer: ReturnType<typeof setInterval> | undefined
  onMounted(() => {
    now.value = Date.now()
    timer = setInterval(() => { now.value = Date.now() }, 1000)
  })
  onUnmounted(() => clearInterval(timer))
  return now
}
