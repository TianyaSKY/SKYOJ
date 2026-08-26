<template>
  <button
      :class="['sample-button', variant]"
      :disabled="disabled"
      @click="handleClick"
  >
    <slot>{{ label }}</slot>
  </button>
</template>

<script setup>
/**
 * 用于测试的最小可交互按钮组件：
 * - props: label / variant / disabled
 * - emits: click
 */
const props = defineProps({
  label: { type: String, default: 'Click me' },
  variant: { type: String, default: 'primary' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['click'])

function handleClick () {
  if (!props.disabled) emit('click')
}
</script>

<style scoped>
.sample-button { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; }
.sample-button:disabled { opacity: 0.5; cursor: not-allowed; }
.sample-button.primary { background: #409eff; color: white; }
.sample-button.success { background: #67c23a; color: white; }
</style>
