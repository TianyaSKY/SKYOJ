<template>
  <div class="draft-box-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <h2>AI 草稿箱</h2>
            <p class="subtitle">异步出题与测例生成任务在此查看，无需在提交页长时间等待。</p>
          </div>
          <div class="header-actions">
            <el-button :loading="loading" @click="fetchDrafts">刷新</el-button>
            <el-button type="primary" @click="$router.push({name: 'problem-admin'})">
              返回题目管理
            </el-button>
          </div>
        </div>
      </template>

      <el-row :gutter="12" class="stats-row">
        <el-col :span="4">
          <div class="mini-stat">
            <div class="mini-value">{{ stats.in_progress || 0 }}</div>
            <div class="mini-label">进行中</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="mini-stat">
            <div class="mini-value success">{{ stats.success || 0 }}</div>
            <div class="mini-label">成功</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="mini-stat">
            <div class="mini-value warning">{{ stats.unconsumed_success || 0 }}</div>
            <div class="mini-label">待应用</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="mini-stat">
            <div class="mini-value danger">{{ stats.failed || 0 }}</div>
            <div class="mini-label">失败</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="mini-stat">
            <div class="mini-value">{{ stats.total || 0 }}</div>
            <div class="mini-label">总计</div>
          </div>
        </el-col>
      </el-row>

      <div class="filters">
        <el-select v-model="filterStatus" clearable placeholder="状态" style="width: 140px" @change="fetchDrafts">
          <el-option label="等待中" value="pending"/>
          <el-option label="执行中" value="running"/>
          <el-option label="成功" value="success"/>
          <el-option label="失败" value="failed"/>
        </el-select>
        <el-select v-model="filterType" clearable placeholder="任务类型" style="width: 180px" @change="fetchDrafts">
          <el-option label="AI 出题" value="problem_generation"/>
          <el-option label="测例脚本" value="test_script_generation"/>
          <el-option label="测例执行" value="test_data_execution"/>
        </el-select>
      </div>

      <el-table v-loading="loading" :data="drafts" stripe>
        <el-table-column label="ID" prop="id" width="70"/>
        <el-table-column label="标题" min-width="220" prop="title" show-overflow-tooltip/>
        <el-table-column label="类型" prop="task_type" width="140">
          <template #default="{row}">
            <el-tag size="small">{{ taskTypeLabel(row.task_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" prop="status" width="110">
          <template #default="{row}">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="题目" prop="problem_id" width="90">
          <template #default="{row}">
            <span v-if="row.problem_id">#{{ row.problem_id }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="160">
          <template #default="{row}">
            {{ formatTime(row.updated_at || row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column align="center" fixed="right" label="操作" width="260">
          <template #default="{row}">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button
                v-if="row.task_type === 'problem_generation' && row.status === 'success' && !row.consumed_at"
                link
                type="success"
                @click="handleApply(row)"
            >
              创建题目
            </el-button>
            <el-button
                v-if="row.task_type === 'test_script_generation' && row.status === 'success'"
                link
                type="warning"
                @click="openDetail(row, true)"
            >
              执行
            </el-button>
            <el-popconfirm
                v-if="row.status !== 'pending' && row.status !== 'running'"
                title="确定删除该草稿？"
                @confirm="handleDelete(row.id)"
            >
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-drawer v-model="detailVisible" size="55%" title="草稿详情" @close="resetDetail">
      <div v-loading="detailLoading" class="detail-body">
        <template v-if="detail">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="ID">{{ detail.id }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTagType(detail.status)" size="small">
                {{ statusLabel(detail.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="类型">
              {{ taskTypeLabel(detail.task_type) }}
            </el-descriptions-item>
            <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item>
            <el-descriptions-item v-if="detail.problem_id" label="关联题目">
              #{{ detail.problem_id }}
            </el-descriptions-item>
            <el-descriptions-item v-if="detail.consumed_at" label="已应用">
              {{ formatTime(detail.consumed_at) }}
            </el-descriptions-item>
          </el-descriptions>

          <el-alert
              v-if="detail.error_message"
              :closable="false"
              :title="detail.error_message"
              class="mt-16"
              show-icon
              type="error"
          />

          <template v-if="detail.task_type === 'problem_generation' && detail.status === 'success'">
            <h3 class="section-title">题目预览</h3>
            <el-form label-position="top">
              <el-form-item label="标题">
                <el-input :model-value="detail.result_payload?.title" readonly/>
              </el-form-item>
              <el-form-item label="内容 (Markdown)">
                <MarkdownContentEditor
                    :model-value="detail.result_payload?.content || ''"
                    default-mode="preview"
                    min-height="320px"
                    readonly
                    :rows="12"
                />
              </el-form-item>
              <el-row :gutter="12">
                <el-col :span="8">
                  <el-form-item label="类型">
                    <el-input :model-value="detail.result_payload?.type" readonly/>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="语言">
                    <el-input :model-value="detail.result_payload?.language" readonly/>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="时限 / 内存">
                    <el-input
                        :model-value="`${detail.result_payload?.time_limit || 1000}ms / ${detail.result_payload?.memory_limit || 128}MB`"
                        readonly
                    />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
            <el-button
                v-if="!detail.consumed_at"
                :loading="applying"
                type="primary"
                @click="handleApply(detail)"
            >
              创建为正式题目
            </el-button>
            <el-tag v-else type="success">已创建正式题目</el-tag>
          </template>

          <template v-if="detail.task_type === 'test_script_generation' && detail.status === 'success'">
            <h3 class="section-title">生成脚本</h3>
            <div class="editor-container script-editor">
              <vue-monaco-editor
                  v-model:value="editableScript"
                  :language="editableLanguage"
                  :options="editorOptions"
                  theme="vs-dark"
              />
            </div>
            <div class="mt-16">
              <el-button :loading="executing" type="success" @click="handleExecuteFromDraft">
                提交后台执行
              </el-button>
              <span class="hint">提交后可关闭本页，到列表中查看执行结果。</span>
            </div>
          </template>

          <template v-if="detail.task_type === 'test_data_execution' && detail.status === 'success'">
            <h3 class="section-title">执行结果</h3>
            <el-result
                :sub-title="detail.result_payload?.message || '执行完成'"
                icon="success"
                title="成功"
            />
          </template>

          <h3 class="section-title">请求参数</h3>
          <pre class="json-block">{{ prettyJson(detail.request_payload) }}</pre>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import {onMounted, onUnmounted, ref} from 'vue'
import {useRouter} from 'vue-router'
import {ElMessage} from 'element-plus'
import {VueMonacoEditor} from '@guolao/vue-monaco-editor'
import MarkdownContentEditor from '@/components/MarkdownContentEditor.vue'
import {
  applyProblemDraft,
  deleteAiDraft,
  getAiDraftDetail,
  getAiDraftStats,
  listAiDrafts,
  submitTestDataExecutionDraft,
} from '@/api/llm'
import {executeTestDataDraftSchema} from '@/schemas/aiDraft'

const router = useRouter()
const drafts = ref([])
const loading = ref(false)
const filterStatus = ref('')
const filterType = ref('')
const stats = ref({})
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
const applying = ref(false)
const executing = ref(false)
const editableScript = ref('')
const editableLanguage = ref('python')
let pollTimer = null

const editorOptions = {
  automaticLayout: true,
  minimap: {enabled: true},
  fontSize: 14,
  scrollBeyondLastLine: false,
}

const taskTypeLabel = (type) => {
  const map = {
    problem_generation: 'AI 出题',
    test_script_generation: '测例脚本',
    test_data_execution: '测例执行',
  }
  return map[type] || type
}

const statusLabel = (status) => {
  const map = {
    pending: '等待中',
    running: '执行中',
    success: '成功',
    failed: '失败',
  }
  return map[status] || status
}

const statusTagType = (status) => {
  const map = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

const formatTime = (value) => {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

const prettyJson = (obj) => {
  try {
    return JSON.stringify(obj || {}, null, 2)
  } catch {
    return String(obj)
  }
}

const fetchStats = async () => {
  try {
    stats.value = (await getAiDraftStats()) || {}
  } catch {
    // 统计失败不打断主流程
  }
}

const fetchDrafts = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterStatus.value) params.status = filterStatus.value
    if (filterType.value) params.task_type = filterType.value
    const res = await listAiDrafts(params)
    drafts.value = res?.drafts || []
    await fetchStats()
  } catch {
    ElMessage.error('获取草稿列表失败')
  } finally {
    loading.value = false
  }
}

const openDetail = async (row, preferExecute = false) => {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  editableScript.value = ''
  try {
    const data = await getAiDraftDetail(row.id)
    detail.value = data
    if (data.task_type === 'test_script_generation' && data.status === 'success') {
      editableScript.value = data.result_payload?.code || ''
      editableLanguage.value = data.result_payload?.language || 'python'
    }
    if (preferExecute) {
      // 已打开编辑区，用户可直接点执行
    }
  } catch {
    ElMessage.error('获取草稿详情失败')
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

const resetDetail = () => {
  detail.value = null
  editableScript.value = ''
}

const handleApply = async (row) => {
  applying.value = true
  try {
    const res = await applyProblemDraft(row.id)
    ElMessage.success(`题目已创建：#${res.problem_id} ${res.title || ''}`)
    await fetchDrafts()
    if (detail.value?.id === row.id) {
      detail.value = await getAiDraftDetail(row.id)
    }
  } catch (error) {
    const msg = error?.response?.data?.error || '创建题目失败'
    ElMessage.error(msg)
  } finally {
    applying.value = false
  }
}

const handleExecuteFromDraft = async () => {
  if (!detail.value) return
  const payload = {
    problem_id: detail.value.problem_id || detail.value.result_payload?.problem_id,
    code: editableScript.value,
    type: detail.value.result_payload?.problem_type || 'acm',
    language: editableLanguage.value || detail.value.result_payload?.language || 'python',
    source_draft_id: detail.value.id,
  }
  const parsed = executeTestDataDraftSchema.safeParse(payload)
  if (!parsed.success) {
    ElMessage.warning(parsed.error.issues[0]?.message || '参数校验失败')
    return
  }

  executing.value = true
  try {
    const res = await submitTestDataExecutionDraft(parsed.data)
    ElMessage.success(res.message || '已提交后台执行，请稍后在列表中查看')
    detailVisible.value = false
    await fetchDrafts()
  } catch (error) {
    const msg = error?.response?.data?.error || '提交执行失败'
    ElMessage.error(msg)
  } finally {
    executing.value = false
  }
}

const handleDelete = async (id) => {
  try {
    await deleteAiDraft(id)
    ElMessage.success('已删除')
    if (detail.value?.id === id) {
      detailVisible.value = false
    }
    await fetchDrafts()
  } catch (error) {
    const msg = error?.response?.data?.error || '删除失败'
    ElMessage.error(msg)
  }
}

onMounted(() => {
  fetchDrafts()
  // 有进行中任务时自动刷新
  pollTimer = setInterval(() => {
    const hasInProgress = drafts.value.some(
        (d) => d.status === 'pending' || d.status === 'running'
    )
    if (hasInProgress || (stats.value.in_progress || 0) > 0) {
      fetchDrafts()
    }
  }, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.draft-box-container {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.header-left h2 {
  margin: 0 0 4px;
}

.subtitle {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.stats-row {
  margin-bottom: 16px;
}

.mini-stat {
  background: var(--el-fill-color-light);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}

.mini-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--el-color-primary);
}

.mini-value.success {
  color: var(--el-color-success);
}

.mini-value.warning {
  color: var(--el-color-warning);
}

.mini-value.danger {
  color: var(--el-color-danger);
}

.mini-label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
}

.muted {
  color: var(--el-text-color-placeholder);
}

.detail-body {
  min-height: 200px;
}

.section-title {
  margin: 20px 0 10px;
  font-size: 15px;
}

.mt-16 {
  margin-top: 16px;
}

.editor-container {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  overflow: hidden;
}

.script-editor {
  height: 360px;
}

.hint {
  margin-left: 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.json-block {
  background: var(--el-fill-color-light);
  border-radius: 6px;
  padding: 12px;
  font-size: 12px;
  overflow: auto;
  max-height: 240px;
}
</style>
