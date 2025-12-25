<template>
  <div class="code-compare-container">
    <el-page-header class="mb-4" @back="$router.back()">
      <template #content>
        <span class="text-large font-600 mr-3"> 代码查重对比 </span>
      </template>
      <template #extra>
        <div class="flex items-center" v-if="similarity !== null">
          <el-tag :type="getSimilarityTagType(similarity)" size="large" effect="dark">
            相似度: {{ (similarity * 100).toFixed(2) }}%
          </el-tag>
        </div>
      </template>
    </el-page-header>

    <div class="compare-wrapper" v-loading="loading">
      <div class="compare-header">
        <div class="header-item">
          <div class="title">提交 #{{ id1 }}</div>
          <div class="info" v-if="sub1">
            <el-tag size="small">{{ sub1.language }}</el-tag>
            <span class="time">{{ formatTime(sub1.created_at) }}</span>
          </div>
        </div>
        <div class="header-item">
          <div class="title">提交 #{{ id2 }}</div>
          <div class="info" v-if="sub2">
            <el-tag size="small">{{ sub2.language }}</el-tag>
            <span class="time">{{ formatTime(sub2.created_at) }}</span>
          </div>
        </div>
      </div>

      <div class="diff-editor-container">
        <vue-monaco-diff-editor
          v-if="sub1 && sub2"
          :original="sub1.code"
          :modified="sub2.code"
          :language="sub1.language || 'python'"
          :options="diffEditorOptions"
          theme="vs-light"
          class="monaco-diff-editor"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getSubmissionDetail } from '@/api/problem'
import { VueMonacoDiffEditor } from '@guolao/vue-monaco-editor'
import { ElMessage } from 'element-plus'

const route = useRoute()
const id1 = route.query.id1
const id2 = route.query.id2
const similarity = ref(route.query.similarity ? parseFloat(route.query.similarity) : null)

const loading = ref(false)
const sub1 = ref(null)
const sub2 = ref(null)

const diffEditorOptions = {
  readOnly: true,
  automaticLayout: true,
  renderSideBySide: true,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  fontSize: 14,
  fontFamily: "'Fira Code', 'Consolas', monospace",
}

const fetchSubmissions = async () => {
  if (!id1 || !id2) {
    ElMessage.error('缺少提交 ID')
    return
  }

  loading.value = true
  try {
    const [res1, res2] = await Promise.all([
      getSubmissionDetail(id1),
      getSubmissionDetail(id2)
    ])
    sub1.value = res1
    sub2.value = res2
  } catch (error) {
    ElMessage.error('获取提交详情失败')
  } finally {
    loading.value = false
  }
}

const getSimilarityTagType = (score) => {
  if (score >= 0.9) return 'danger'
  if (score >= 0.7) return 'warning'
  return 'success'
}

const formatTime = (time) => time ? new Date(time).toLocaleString() : ''

onMounted(() => {
  fetchSubmissions()
})
</script>

<style scoped>
.code-compare-container {
  padding: 20px;
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
}

.compare-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.compare-header {
  display: flex;
  background: #f5f7fa;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.header-item {
  flex: 1;
  padding: 12px 20px;
}

.header-item:first-child {
  border-right: 1px solid var(--el-border-color-lighter);
}

.header-item .title {
  font-weight: bold;
  font-size: 16px;
  margin-bottom: 4px;
}

.header-item .info {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.diff-editor-container {
  flex: 1;
  min-height: 0;
}

.monaco-diff-editor {
  width: 100%;
  height: 100%;
}

.mb-4 {
  margin-bottom: 20px;
}
</style>
