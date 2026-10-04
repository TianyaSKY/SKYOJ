<template>
  <div class="preview-container">
    <el-page-header @back="router.push({ name: 'problem-admin' })"
      ><template #content><span>题目管理预览</span></template></el-page-header
    >
    <el-card v-loading="loading" class="preview-card" shadow="never">
      <template #header
        ><div class="header">
          <div>
            <h2>#{{ problem.id }} {{ problem.title }}</h2>
            <p>教师管理端预览，不提供作答与提交。</p>
          </div>
          <el-button type="primary" @click="router.push({ name: 'problem-admin' })"
            >返回管理</el-button
          >
        </div></template
      >
      <el-descriptions :column="3" border class="meta">
        <el-descriptions-item label="题目类型">{{
          (problem.type || '-').toUpperCase()
        }}</el-descriptions-item>
        <el-descriptions-item label="允许语言">{{ problem.language || '-' }}</el-descriptions-item>
        <el-descriptions-item label="资源限制"
          >{{ problem.time_limit }}ms / {{ problem.memory_limit }}MB</el-descriptions-item
        >
      </el-descriptions>
      <el-divider />
      <div class="markdown-body" v-html="renderedContent"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { ProblemDetailResponse } from '@/types/problem'
import { parseRouteId } from '@/utils/route'
import { getProblemDetail } from '@/api/problem'
import { ElMessage } from 'element-plus'
import { renderMarkdown } from '@/utils/markdown'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const problem = ref<Partial<ProblemDetailResponse>>({})
const renderedContent = computed(() => renderMarkdown(problem.value.content || ''))

onMounted(async () => {
  loading.value = true
  try {
    const id = parseRouteId(route.params.id)
    if (id === null) throw new Error('题目 ID 无效')
    problem.value = await getProblemDetail(id)
  } catch {
    ElMessage.error('加载题目失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.preview-container {
  max-width: 1200px;
  margin: 0 auto;
}
.preview-card {
  margin-top: 20px;
  min-height: 400px;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.header h2 {
  margin: 0;
}
.header p {
  margin: 6px 0 0;
  color: #909399;
}
.meta {
  margin-bottom: 24px;
}
</style>
