<template>
  <div class="md-editor" :class="{ 'is-readonly': readonly }">
    <div class="md-toolbar">
      <el-radio-group v-model="mode" size="small">
        <el-radio-button value="edit">纯文本</el-radio-button>
        <el-radio-button value="preview">纯渲染</el-radio-button>
        <el-radio-button value="split">分屏</el-radio-button>
      </el-radio-group>
      <span class="toolbar-hint">{{ modeHint }}</span>
    </div>

    <div class="md-body" :class="`mode-${mode}`" :style="{ minHeight: minHeight }">
      <div v-show="mode === 'edit' || mode === 'split'" class="md-pane md-source">
        <el-input
            :model-value="modelValue"
            :placeholder="placeholder"
            :readonly="readonly"
            :rows="rows"
            class="md-textarea"
            resize="vertical"
            type="textarea"
            @update:model-value="onInput"
        />
      </div>

      <div
          v-show="mode === 'preview' || mode === 'split'"
          class="md-pane md-preview markdown-body"
          v-html="renderedHtml"
      />
    </div>
  </div>
</template>

<script setup>
import {computed, ref} from 'vue'
import md from '@/utils/markdown'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  readonly: {
    type: Boolean,
    default: false,
  },
  rows: {
    type: Number,
    default: 14,
  },
  minHeight: {
    type: String,
    default: '320px',
  },
  placeholder: {
    type: String,
    default: '支持 Markdown，可使用代码块与公式…',
  },
  /** 初始展示模式：edit | preview | split */
  defaultMode: {
    type: String,
    default: 'edit',
    validator: (v) => ['edit', 'preview', 'split'].includes(v),
  },
})

const emit = defineEmits(['update:modelValue'])

const mode = ref(
    ['edit', 'preview', 'split'].includes(props.defaultMode)
        ? props.defaultMode
        : 'edit'
)

const modeHint = computed(() => {
  if (mode.value === 'edit') return '编辑 Markdown 源码'
  if (mode.value === 'preview') return '仅预览渲染结果'
  return '左侧编辑 · 右侧预览'
})

const renderedHtml = computed(() => {
  const text = props.modelValue || ''
  if (!text.trim()) {
    return '<p class="md-empty">暂无内容</p>'
  }
  try {
    return md.render(text)
  } catch {
    return '<p class="md-empty">Markdown 渲染失败</p>'
  }
})

const onInput = (value) => {
  if (props.readonly) return
  emit('update:modelValue', value)
}
</script>

<style scoped>
.md-editor {
  width: 100%;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  overflow: hidden;
  background: var(--el-bg-color);
}

.md-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
}

.toolbar-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.md-body {
  display: flex;
  width: 100%;
}

.md-body.mode-edit,
.md-body.mode-preview {
  flex-direction: column;
}

.md-body.mode-split {
  flex-direction: row;
  align-items: stretch;
}

.md-pane {
  flex: 1;
  min-width: 0;
  min-height: inherit;
}

.md-body.mode-split .md-source {
  border-right: 1px solid var(--el-border-color-lighter);
}

.md-textarea {
  height: 100%;
}

.md-textarea :deep(.el-textarea) {
  height: 100%;
}

.md-textarea :deep(.el-textarea__inner) {
  border: none;
  border-radius: 0;
  box-shadow: none;
  min-height: inherit !important;
  height: 100% !important;
  font-family: 'Cascadia Code', 'Fira Code', Consolas, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  padding: 12px 14px;
  resize: vertical;
}

.md-body.mode-split .md-preview {
  max-height: none;
}

.md-textarea :deep(.el-textarea__inner:focus) {
  box-shadow: none;
}

.md-preview {
  padding: 14px 16px;
  overflow: auto;
  box-sizing: border-box;
  background: #fff;
}

.md-preview :deep(.md-empty) {
  margin: 0;
  color: var(--el-text-color-placeholder);
}

/* Markdown 渲染样式（与题目详情页风格对齐） */
.markdown-body {
  font-size: 1.02rem;
  line-height: 1.7;
  color: #333;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin-top: 1.2em;
  margin-bottom: 0.5em;
  font-weight: 600;
  line-height: 1.35;
}

.markdown-body :deep(h1) {
  font-size: 1.6rem;
}

.markdown-body :deep(h2) {
  font-size: 1.35rem;
  border-bottom: 1px solid #eee;
  padding-bottom: 6px;
}

.markdown-body :deep(h3) {
  font-size: 1.15rem;
}

.markdown-body :deep(p) {
  margin: 0.6em 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.4em;
  margin: 0.6em 0;
}

.markdown-body :deep(blockquote) {
  margin: 0.8em 0;
  padding: 0.4em 0.9em;
  border-left: 4px solid #d0d7de;
  color: #57606a;
  background: #f6f8fa;
}

.markdown-body :deep(pre) {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 12px 14px;
  border: 1px solid #eaecf0;
  overflow: auto;
}

.markdown-body :deep(code) {
  font-family: 'Fira Code', Consolas, monospace;
  background-color: #f0f2f5;
  padding: 2px 6px;
  border-radius: 4px;
  color: #e01979;
  font-size: 0.92em;
}

.markdown-body :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: inherit;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.8em 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #d0d7de;
  padding: 6px 10px;
}

.markdown-body :deep(th) {
  background: #f6f8fa;
}

.markdown-body :deep(img) {
  max-width: 100%;
}

.markdown-body :deep(a) {
  color: var(--el-color-primary);
}

@media (max-width: 768px) {
  .md-body.mode-split {
    flex-direction: column;
  }

  .md-body.mode-split .md-source {
    border-right: none;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }

  .toolbar-hint {
    display: none;
  }
}
</style>
