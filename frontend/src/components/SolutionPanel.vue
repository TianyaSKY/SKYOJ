<script setup>
/**
 * 题解面板：嵌入 ProblemDetailView 的题解 Tab。
 *
 * 数据流：
 * - 进入组件时拉取该题目的全部已发布题解（list_for_problem）。
 * - 用户在卡片右侧操作点赞（toggle_like）或点开评论抽屉。
 * - "写题解" / "编辑" 走 dialog 提交，独立表单。
 *
 * 设计选择：
 * - 不在卡片内嵌评论，只点开抽屉，避免卡片过长。
 * - Markdown 渲染沿用项目通用的 markdown-it（与题目描述一致）。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Star, StarFilled, ChatDotRound, Edit, Hide, EditPen, Plus } from '@element-plus/icons-vue'
import request from '@/utils/request'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  problemId: { type: Number, required: true }
})

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const loading = ref(false)
const solutions = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const writeDialogVisible = ref(false)
const editing = ref(null)  // null 表示新建；非空表示编辑
const form = ref({ title: '', content: '', language: '' })

const commentsDialog = ref(false)
const currentSolution = ref(null)
const comments = ref([])
const commentsTotal = ref(0)
const newComment = ref('')

const userInfo = (() => {
  try { return JSON.parse(localStorage.getItem('user') || '{}') } catch { return {} }
})()
const isTeacher = computed(() => userInfo.role === 'teacher')

async function load () {
  loading.value = true
  try {
    const resp = await request({
      url: `/api/problems/${props.problemId}/solutions`,
      method: 'get',
      params: { page: page.value, page_size: pageSize }
    })
    solutions.value = resp.items || []
    total.value = resp.total || 0
  } catch (e) {
    ElMessage.error('加载题解失败：' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

watch(() => props.problemId, () => { page.value = 1; load() }, { immediate: false })
onMounted(load)

function renderMarkdown (text) {
  if (!text) return ''
  return md.render(text)
}

function openWrite (item = null) {
  editing.value = item
  form.value = item
    ? { title: item.title, content: item.content, language: item.language || '' }
    : { title: '', content: '', language: '' }
  writeDialogVisible.value = true
}

async function submitSolution () {
  if (!form.value.title.trim() || !form.value.content.trim()) {
    ElMessage.warning('标题和正文不能为空')
    return
  }
  try {
    if (editing.value) {
      await request({
        url: `/api/problems/solutions/${editing.value.id}`,
        method: 'put',
        data: form.value
      })
      ElMessage.success('题解已更新')
    } else {
      await request({
        url: `/api/problems/${props.problemId}/solutions`,
        method: 'post',
        data: form.value
      })
      ElMessage.success('题解已发布')
    }
    writeDialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  }
}

async function toggleLike (item) {
  try {
    const resp = await request({
      url: `/api/problems/solutions/${item.id}/like`,
      method: 'post'
    })
    item.vote_count = resp.vote_count
    item.liked_by_me = resp.liked
  } catch (e) {
    ElMessage.error(e.message || '点赞失败')
  }
}

async function toggleFavorite (item) {
  try {
    const resp = await request({
      url: `/api/problems/solutions/${item.id}/favorite`,
      method: 'post'
    })
    item.favorited_by_me = resp.favorited
  } catch (e) {
    ElMessage.error(e.message || '收藏失败')
  }
}

async function hideSolution (item) {
  try {
    await ElMessageBox.confirm('确定要隐藏该题解吗？隐藏后仅你自己与教师可见。', '确认隐藏', { type: 'warning' })
    await request({ url: `/api/problems/solutions/${item.id}`, method: 'delete' })
    ElMessage.success('已隐藏')
    load()
  } catch (e) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      ElMessage.error(e.message || '隐藏失败')
    }
  }
}

async function openComments (item) {
  currentSolution.value = item
  commentsDialog.value = true
  newComment.value = ''
  await loadComments()
}

async function loadComments (pageNo = 1) {
  if (!currentSolution.value) return
  try {
    const resp = await request({
      url: `/api/problems/solutions/${currentSolution.value.id}/comments`,
      method: 'get',
      params: { page: pageNo, page_size: 50 }
    })
    comments.value = resp.items || []
    commentsTotal.value = resp.total || 0
  } catch (e) {
    ElMessage.error(e.message || '加载评论失败')
  }
}

async function submitComment () {
  const text = newComment.value.trim()
  if (!text) return
  try {
    await request({
      url: `/api/problems/solutions/${currentSolution.value.id}/comments`,
      method: 'post',
      data: { content: text }
    })
    newComment.value = ''
    currentSolution.value.comment_count += 1
    await loadComments()
  } catch (e) {
    ElMessage.error(e.message || '评论失败')
  }
}

async function deleteComment (commentId) {
  try {
    await ElMessageBox.confirm('删除这条评论？', '确认', { type: 'warning' })
    await request({ url: `/api/problems/comments/${commentId}`, method: 'delete' })
    ElMessage.success('已删除')
    currentSolution.value.comment_count = Math.max(0, currentSolution.value.comment_count - 1)
    await loadComments()
  } catch (e) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      ElMessage.error(e.message || '删除失败')
    }
  }
}
</script>

<template>
  <el-card class="solution-panel" shadow="never">
    <template #header>
      <div class="panel-header">
        <span class="title">题解（{{ total }}）</span>
        <el-button type="primary" size="small" @click="openWrite()">
          <el-icon><EditPen /></el-icon>
          <span style="margin-left: 4px">写题解</span>
        </el-button>
      </div>
    </template>

    <el-empty v-if="!loading && solutions.length === 0" description="还没有题解，来贡献第一篇？" />
    <el-skeleton v-else-if="loading" :rows="4" animated />

    <div v-else class="solution-list">
      <el-card
        v-for="item in solutions"
        :key="item.id"
        class="solution-item"
        shadow="hover"
      >
        <div class="solution-head">
          <div class="head-left">
            <el-tag v-if="item.is_official" type="success" size="small">官方</el-tag>
            <span class="solution-title">{{ item.title }}</span>
          </div>
          <div class="head-right">
            <span class="meta">@{{ item.author_username }}</span>
            <span class="meta">{{ new Date(item.created_at).toLocaleDateString() }}</span>
          </div>
        </div>
        <div class="solution-body markdown-body" v-html="renderMarkdown(item.content)" />
        <div class="solution-actions">
          <el-button :type="item.liked_by_me ? 'primary' : 'default'" size="small" @click="toggleLike(item)">
            <el-icon><Star /></el-icon>
            <span style="margin-left: 4px">{{ item.vote_count }}</span>
          </el-button>
          <el-button :type="item.favorited_by_me ? 'warning' : 'default'" size="small" @click="toggleFavorite(item)">
            <el-icon><StarFilled /></el-icon>
          </el-button>
          <el-button size="small" @click="openComments(item)">
            <el-icon><ChatDotRound /></el-icon>
            <span style="margin-left: 4px">{{ item.comment_count }}</span>
          </el-button>
          <el-button
            v-if="userInfo.id === item.author_id || isTeacher"
            size="small"
            @click="openWrite(item)"
          >
            <el-icon><Edit /></el-icon>
            <span style="margin-left: 4px">编辑</span>
          </el-button>
          <el-button
            v-if="userInfo.id === item.author_id || isTeacher"
            size="small"
            type="danger"
            @click="hideSolution(item)"
          >
            <el-icon><Hide /></el-icon>
            <span style="margin-left: 4px">隐藏</span>
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 写题解 / 编辑题解 -->
    <el-dialog
      v-model="writeDialogVisible"
      :title="editing ? '编辑题解' : '发布题解'"
      width="720px"
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="代码示例语言（可选）">
          <el-input v-model="form.language" placeholder="如 python / cpp" maxlength="50" />
        </el-form-item>
        <el-form-item label="正文 (Markdown)" required>
          <el-input v-model="form.content" type="textarea" :rows="12" maxlength="20000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="writeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitSolution">{{ editing ? '保存' : '发布' }}</el-button>
      </template>
    </el-dialog>

    <!-- 评论抽屉 -->
    <el-dialog
      v-model="commentsDialog"
      :title="currentSolution ? `评论：${currentSolution.title}` : '评论'"
      width="640px"
      destroy-on-close
    >
      <div class="comment-input">
        <el-input v-model="newComment" type="textarea" :rows="3" maxlength="1000" placeholder="说点什么…" show-word-limit />
        <el-button type="primary" :disabled="!newComment.trim()" @click="submitComment">发送</el-button>
      </div>
      <el-empty v-if="comments.length === 0" description="还没有评论" :image-size="80" />
      <div v-else class="comment-list">
        <div v-for="c in comments" :key="c.id" class="comment-item">
          <div class="comment-meta">
            <span class="username">@{{ c.username }}</span>
            <span class="time">{{ new Date(c.created_at).toLocaleString() }}</span>
            <el-button
              v-if="userInfo.id === c.user_id || isTeacher"
              type="danger"
              link
              size="small"
              @click="deleteComment(c.id)"
            >
              删除
            </el-button>
          </div>
          <div class="comment-body">{{ c.content }}</div>
        </div>
      </div>
    </el-dialog>
  </el-card>
</template>

<style scoped>
.solution-panel {
  margin-top: 16px;
  border-radius: 12px;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title {
  font-weight: 600;
  font-size: 16px;
}
.solution-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.solution-item {
  border-radius: 8px;
}
.solution-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.head-right .meta {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-left: 12px;
}
.solution-title {
  font-weight: 600;
  font-size: 15px;
}
.solution-body {
  font-size: 14px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  margin: 8px 0;
  max-height: 360px;
  overflow-y: auto;
}
.solution-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.comment-input {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.comment-input :deep(.el-textarea) {
  flex: 1;
}
.comment-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 420px;
  overflow-y: auto;
}
.comment-item {
  padding: 8px 12px;
  background: var(--el-bg-color-page);
  border-radius: 6px;
}
.comment-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}
.comment-meta .username {
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.comment-body {
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>