<script setup lang="ts">
/**
 * 题目标签面板：在题目标题下展示当前题目的标签，
 * 教师可挂 / 摘标签；普通用户可建议。
 *
 * 数据流：
 * - 题目变化时同时拉题目已贴标签 / 全站可选标签，忽略旧请求响应。
 * - 教师贴：approved=true 立即生效；普通用户：approved=false 进入审批。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getProblemTags, getTags, attachProblemTag, detachProblemTag } from '@/api/tag'
import type { TagResponse } from '@/types/community'
import { errorMessage } from '@/utils/error'
import { useUserStore } from '@/stores/user'

const props = defineProps({
  problemId: { type: Number, required: true },
})

const loading = ref(false)
const attached = ref<TagResponse[]>([]) // 当前题目已贴标签
const all = ref<TagResponse[]>([]) // 全站标签
const attachDialogVisible = ref(false)
const selectedTagId = ref<number | null>(null)
const submittingAttach = ref(false)
let attachVersion = 0
let scopeVersion = 0
let loadVersion = 0
let disposed = false
const isCurrentScope = (version: number) => !disposed && version === scopeVersion
const isCurrentAttach = (scope: number, version: number) =>
  isCurrentScope(scope) && version === attachVersion && attachDialogVisible.value

const userStore = useUserStore()
const isTeacher = computed(() => userStore.user?.role === 'teacher')

async function load() {
  const scope = scopeVersion
  const requestId = ++loadVersion
  const isCurrent = () => isCurrentScope(scope) && requestId === loadVersion
  loading.value = true
  try {
    const [a, b] = await Promise.all([getProblemTags(props.problemId), getTags()])
    if (!isCurrent()) return
    attached.value = a || []
    all.value = b || []
  } catch (e) {
    if (isCurrent()) ElMessage.error(errorMessage(e, '加载标签失败'))
  } finally {
    if (isCurrent()) loading.value = false
  }
}

watch(
  () => props.problemId,
  () => {
    scopeVersion += 1
    attached.value = []
    all.value = []
    selectedTagId.value = null
    attachDialogVisible.value = false
    load()
  },
  { immediate: true },
)
watch(
  attachDialogVisible,
  (visible) => {
    if (!visible) {
      attachVersion += 1
      submittingAttach.value = false
    }
  },
  { flush: 'sync' },
)
onBeforeUnmount(() => {
  disposed = true
  scopeVersion += 1
})

function openAttach() {
  attachVersion += 1
  submittingAttach.value = false
  selectedTagId.value = null
  attachDialogVisible.value = true
}

async function confirmAttach() {
  if (!attachDialogVisible.value || submittingAttach.value) return
  const scope = scopeVersion
  const version = attachVersion
  const approved = isTeacher.value
  const problemId = props.problemId
  if (!selectedTagId.value) {
    ElMessage.warning('请选择标签')
    return
  }
  submittingAttach.value = true
  try {
    await attachProblemTag(problemId, { tag_id: selectedTagId.value, approved })
    if (!isCurrentScope(scope)) return
    // 已生效的操作刷新标签列表，但不影响后来打开的窗口。
    load()
    if (!isCurrentAttach(scope, version)) return
    ElMessage.success(approved ? '标签已挂上' : '已提交建议，等待教师审核')
    attachDialogVisible.value = false
  } catch (e) {
    if (isCurrentAttach(scope, version)) ElMessage.error(errorMessage(e, '操作失败'))
  } finally {
    if (isCurrentAttach(scope, version)) submittingAttach.value = false
  }
}

async function detach(tag: TagResponse) {
  const scope = scopeVersion
  const problemId = props.problemId
  try {
    await ElMessageBox.confirm(`从该题目移除标签「${tag.name}」？`, '确认移除', { type: 'warning' })
    if (!isCurrentScope(scope)) return
    await detachProblemTag(problemId, tag.id)
    if (!isCurrentScope(scope)) return
    ElMessage.success('已移除')
    load()
  } catch (e) {
    if (isCurrentScope(scope) && e !== 'cancel' && errorMessage(e, '') !== 'cancel') {
      ElMessage.error(errorMessage(e, '移除失败'))
    }
  }
}
</script>

<template>
  <div class="tag-panel">
    <div class="tag-list">
      <el-tag
        v-for="t in attached"
        :key="t.id"
        :type="t.category === '基础' ? 'success' : 'info'"
        size="small"
        :closable="isTeacher"
        @close="detach(t)"
      >
        {{ t.name }}
      </el-tag>
      <el-button link size="small" type="primary" @click="openAttach">
        <el-icon><Plus /></el-icon>
        <span style="margin-left: 4px">添加标签</span>
      </el-button>
    </div>

    <el-dialog v-model="attachDialogVisible" title="添加标签" width="480px">
      <el-form label-position="top">
        <el-form-item label="选择标签">
          <el-select v-model="selectedTagId" placeholder="搜索标签" filterable style="width: 100%">
            <el-option
              v-for="t in all.filter((x) => !attached.find((a) => a.id === x.id))"
              :key="t.id"
              :label="t.name + (t.category ? ` (${t.category})` : '')"
              :value="t.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="attachDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submittingAttach"
          :disabled="submittingAttach"
          @click="confirmAttach"
          >提交</el-button
        >
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.tag-panel {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.tag-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
