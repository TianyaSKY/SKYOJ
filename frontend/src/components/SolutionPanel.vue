<script setup lang="ts">
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
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Star, StarFilled, ChatDotRound, Edit, Hide, EditPen, Plus } from '@element-plus/icons-vue'
import { getSolutions, createSolution, updateSolution, hideSolution as hideSolutionRequest, toggleSolutionLike, toggleSolutionFavorite, getComments, createComment, deleteComment as deleteCommentRequest } from '@/api/community'
import type { SolutionListItemResponse, CommentResponse } from '@/types/community'
import { errorMessage } from '@/utils/error'
import { formatServerDateTime, formatServerDate } from '@/utils/date'
import { useUserStore } from '@/stores/user'
import { solutionFormSchema, commentFormSchema } from '@/schemas/community'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  problemId: { type: Number, required: true }
})

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const loading = ref(false)
const solutions = ref<SolutionListItemResponse[]>([])
const pendingLikes = ref(new Set<number>())
const pendingFavorites = ref(new Set<number>())
type ReactionValues = Partial<Pick<SolutionListItemResponse, 'vote_count' | 'liked_by_me' | 'favorited_by_me'>>
const reactionUpdates = new Map<number, Partial<Record<'like' | 'favorite', {version: number; values: ReactionValues}>>>()
let reactionVersion = 0
const total = ref(0)
const page = ref(1)
const pageSize = 20

const writeDialogVisible = ref(false)
const savingSolution = ref(false)
let writeVersion = 0
const editing = ref<SolutionListItemResponse | null>(null)  // null 表示新建；非空表示编辑
const form = ref({ title: '', content: '', language: '' })

const commentsDialog = ref(false)
const currentSolution = ref<SolutionListItemResponse | null>(null)
const comments = ref<CommentResponse[]>([])
const commentsTotal = ref(0)
const commentsPage = ref(1)
const commentsPageSize = 50
const loadingComments = ref(false)
const newComment = ref('')
const submittingComment = ref(false)
let scopeVersion = 0
let loadVersion = 0
let commentsVersion = 0
let commentRequestVersion = 0
let disposed = false
const isCurrentScope = (version: number) => !disposed && version === scopeVersion
const isCurrentWrite = (scope: number, version: number) =>
  isCurrentScope(scope) && version === writeVersion && writeDialogVisible.value
const isCurrentComments = (scope: number, version: number, item: SolutionListItemResponse) =>
  isCurrentScope(scope) && version === commentsVersion && commentsDialog.value && currentSolution.value === item

const userStore = useUserStore()
const userInfo = computed(() => userStore.user || {})
const isTeacher = computed(() => userInfo.value.role === 'teacher')

async function load (pageNo = page.value): Promise<void> {
  const scope = scopeVersion
  const requestId = ++loadVersion
  const initialReactionVersion = reactionVersion
  const isCurrent = () => isCurrentScope(scope) && requestId === loadVersion
  loading.value = true
  try {
    const resp = await getSolutions(props.problemId, { page: pageNo, page_size: pageSize })
    if (!isCurrent()) return
    const lastPage = Math.max(1, Math.ceil((resp.total || 0) / pageSize))
    if (pageNo > lastPage) return await load(lastPage)
    page.value = pageNo
    solutions.value = (resp.items || []).map(item => {
      // 列表请求发起后完成的操作优先于该请求可能读取到的旧状态。
      for (const update of Object.values(reactionUpdates.get(item.id) || {})) {
        if (update.version > initialReactionVersion) Object.assign(item, update.values)
      }
      return item
    })
    total.value = resp.total || 0
  } catch (e) {
    if (isCurrent()) ElMessage.error('加载题解失败：' + (errorMessage(e, '未知错误')))
  } finally {
    if (isCurrent()) loading.value = false
  }
}

watch(() => props.problemId, () => {
  scopeVersion += 1
  commentsVersion += 1
  page.value = 1
  solutions.value = []
  pendingLikes.value.clear()
  pendingFavorites.value.clear()
  reactionUpdates.clear()
  reactionVersion = 0
  total.value = 0
  writeDialogVisible.value = false
  editing.value = null
  form.value = { title: '', content: '', language: '' }
  commentsDialog.value = false
  currentSolution.value = null
  comments.value = []
  commentsTotal.value = 0
  commentsPage.value = 1
  loadingComments.value = false
  newComment.value = ''
  submittingComment.value = false
  load()
}, { immediate: true })
watch(commentsDialog, visible => {
  if (!visible) {
    commentsVersion += 1
    currentSolution.value = null
    comments.value = []
    commentsTotal.value = 0
    commentsPage.value = 1
    loadingComments.value = false
    newComment.value = ''
    submittingComment.value = false
  }
})
watch(writeDialogVisible, visible => {
  if (!visible) {
    writeVersion += 1
    savingSolution.value = false
  }
}, { flush: 'sync' })
onBeforeUnmount(() => { disposed = true; scopeVersion += 1 })

function renderMarkdown (text: string) {
  if (!text) return ''
  return md.render(text)
}

function openWrite (item: SolutionListItemResponse | null = null) {
  writeVersion += 1
  savingSolution.value = false
  editing.value = item
  form.value = item
    ? { title: item.title, content: item.content, language: item.language || '' }
    : { title: '', content: '', language: '' }
  writeDialogVisible.value = true
}

async function submitSolution () {
  if (!writeDialogVisible.value || savingSolution.value) return
  const scope = scopeVersion
  const version = writeVersion
  const parsed = solutionFormSchema.safeParse(form.value)
  if (!parsed.success) {
    ElMessage.warning(parsed.error.issues[0]?.message || '请检查题解输入')
    return
  }
  const editingId = editing.value?.id
  const problemId = props.problemId
  savingSolution.value = true
  try {
    await (editingId ? updateSolution(editingId, parsed.data) : createSolution(problemId, parsed.data))
    if (!isCurrentScope(scope)) return
    // 保存已生效时刷新当前题目列表，但不能干扰后来打开的编辑窗口。
    load()
    if (!isCurrentWrite(scope, version)) return
    ElMessage.success(editingId ? '题解已更新' : '题解已发布')
    writeDialogVisible.value = false
  } catch (e) {
    if (isCurrentWrite(scope, version)) ElMessage.error(errorMessage(e, '操作失败'))
  } finally {
    if (isCurrentWrite(scope, version)) savingSolution.value = false
  }
}

function applyReactionResult (item: SolutionListItemResponse, kind: 'like' | 'favorite', values: ReactionValues) {
  const updates = reactionUpdates.get(item.id) || {}
  updates[kind] = { version: ++reactionVersion, values }
  reactionUpdates.set(item.id, updates)
  // 刷新会替换卡片对象，同时更新原对象和当前列表中的对象。
  Object.assign(item, values)
  const current = solutions.value.find(solution => solution.id === item.id)
  if (current) Object.assign(current, values)
}

async function toggleLike (item: SolutionListItemResponse) {
  if (pendingLikes.value.has(item.id)) return
  const scope = scopeVersion
  pendingLikes.value.add(item.id)
  try {
    const resp = await toggleSolutionLike(item.id)
    if (!isCurrentScope(scope)) return
    applyReactionResult(item, 'like', { vote_count: resp.vote_count, liked_by_me: resp.liked })
  } catch (e) {
    if (isCurrentScope(scope)) ElMessage.error(errorMessage(e, '点赞失败'))
  } finally {
    if (isCurrentScope(scope)) pendingLikes.value.delete(item.id)
  }
}

async function toggleFavorite (item: SolutionListItemResponse) {
  if (pendingFavorites.value.has(item.id)) return
  const scope = scopeVersion
  pendingFavorites.value.add(item.id)
  try {
    const resp = await toggleSolutionFavorite(item.id)
    if (!isCurrentScope(scope)) return
    applyReactionResult(item, 'favorite', { favorited_by_me: resp.favorited })
  } catch (e) {
    if (isCurrentScope(scope)) ElMessage.error(errorMessage(e, '收藏失败'))
  } finally {
    if (isCurrentScope(scope)) pendingFavorites.value.delete(item.id)
  }
}

async function hideSolution (item: SolutionListItemResponse) {
  const scope = scopeVersion
  try {
    await ElMessageBox.confirm('确定要隐藏该题解吗？隐藏后仅你自己与教师可见。', '确认隐藏', { type: 'warning' })
    if (!isCurrentScope(scope)) return
    await hideSolutionRequest(item.id)
    if (!isCurrentScope(scope)) return
    ElMessage.success('已隐藏')
    load()
  } catch (e) {
    if (isCurrentScope(scope) && e !== 'cancel' && errorMessage(e, '') !== 'cancel') {
      ElMessage.error(errorMessage(e, '隐藏失败'))
    }
  }
}

async function openComments (item: SolutionListItemResponse) {
  commentsVersion += 1
  submittingComment.value = false
  currentSolution.value = item
  comments.value = []
  commentsTotal.value = 0
  commentsPage.value = 1
  loadingComments.value = false
  commentsDialog.value = true
  newComment.value = ''
  await loadComments()
}

async function loadComments (pageNo = commentsPage.value, latest = false): Promise<void> {
  const item = currentSolution.value
  if (!item) return
  const scope = scopeVersion, version = commentsVersion
  const requestId = ++commentRequestVersion
  const isCurrent = () => isCurrentComments(scope, version, item) && requestId === commentRequestVersion
  loadingComments.value = true
  try {
    const resp = await getComments(item.id, { page: pageNo, page_size: commentsPageSize })
    if (!isCurrent()) return
    const lastPage = Math.max(1, Math.ceil((resp.total || 0) / commentsPageSize))
    if (pageNo > lastPage || (latest && pageNo !== lastPage)) {
      return await loadComments(lastPage, latest)
    }
    commentsPage.value = pageNo
    comments.value = resp.items || []
    commentsTotal.value = resp.total || 0
  } catch (e) {
    if (isCurrent()) ElMessage.error(errorMessage(e, '加载评论失败'))
  } finally {
    if (isCurrent()) loadingComments.value = false
  }
}

async function submitComment () {
  const item = currentSolution.value
  if (!item || !commentsDialog.value || submittingComment.value) return
  const scope = scopeVersion, version = commentsVersion
  const content = newComment.value
  const parsed = commentFormSchema.safeParse({content})
  if (!parsed.success) {
    ElMessage.warning(parsed.error.issues[0]?.message || '请检查评论输入')
    return
  }
  submittingComment.value = true
  try {
    await createComment(item.id, parsed.data)
    if (!isCurrentScope(scope)) return
    item.comment_count += 1
    if (!isCurrentComments(scope, version, item)) return
    if (newComment.value === content) newComment.value = ''
    // 评论按时间正序排列，发布后定位末页；以查询返回的总数修正旧计数。
    const estimatedLastPage = Math.max(1, Math.ceil((commentsTotal.value + 1) / commentsPageSize))
    await loadComments(estimatedLastPage, true)
  } catch (e) {
    if (isCurrentComments(scope, version, item)) ElMessage.error(errorMessage(e, '评论失败'))
  } finally {
    if (isCurrentComments(scope, version, item)) submittingComment.value = false
  }
}

async function deleteComment (commentId: number) {
  const item = currentSolution.value
  if (!item) return
  const scope = scopeVersion, version = commentsVersion
  try {
    await ElMessageBox.confirm('删除这条评论？', '确认', { type: 'warning' })
    if (!isCurrentComments(scope, version, item)) return
    await deleteCommentRequest(commentId)
    if (!isCurrentScope(scope)) return
    item.comment_count = Math.max(0, item.comment_count - 1)
    if (!isCurrentComments(scope, version, item)) return
    ElMessage.success('已删除')
    await loadComments()
  } catch (e) {
    if (isCurrentComments(scope, version, item) && e !== 'cancel' && errorMessage(e, '') !== 'cancel') {
      ElMessage.error(errorMessage(e, '删除失败'))
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
            <span class="meta">{{ formatServerDate(item.created_at) }}</span>
          </div>
        </div>
        <div class="solution-body markdown-body" v-html="renderMarkdown(item.content)" />
        <div class="solution-actions">
          <el-button :type="item.liked_by_me ? 'primary' : 'default'" size="small" :loading="pendingLikes.has(item.id)" :disabled="pendingLikes.has(item.id)" @click="toggleLike(item)">
            <el-icon><Star /></el-icon>
            <span style="margin-left: 4px">{{ item.vote_count }}</span>
          </el-button>
          <el-button :type="item.favorited_by_me ? 'warning' : 'default'" size="small" :loading="pendingFavorites.has(item.id)" :disabled="pendingFavorites.has(item.id)" @click="toggleFavorite(item)">
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

    <el-pagination
      v-if="total > pageSize"
      :current-page="page"
      :page-size="pageSize"
      :total="total"
      :disabled="loading"
      layout="prev, pager, next"
      @current-change="load"
    />

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
        <el-button type="primary" :loading="savingSolution" :disabled="savingSolution" @click="submitSolution">{{ editing ? '保存' : '发布' }}</el-button>
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
        <el-button type="primary" :loading="submittingComment" :disabled="!newComment.trim() || submittingComment" @click="submitComment">发送</el-button>
      </div>
      <el-skeleton v-if="loadingComments" :rows="3" animated />
      <el-empty v-else-if="comments.length === 0" description="还没有评论" :image-size="80" />
      <div v-else class="comment-list">
        <div v-for="c in comments" :key="c.id" class="comment-item">
          <div class="comment-meta">
            <span class="username">@{{ c.username }}</span>
            <span class="time">{{ formatServerDateTime(c.created_at) }}</span>
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
      <el-pagination
        v-if="commentsTotal > commentsPageSize"
        :current-page="commentsPage"
        :page-size="commentsPageSize"
        :total="commentsTotal"
        :disabled="loadingComments"
        layout="prev, pager, next"
        @current-change="loadComments"
      />
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
