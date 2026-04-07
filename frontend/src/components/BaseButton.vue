<script setup lang="ts">
/**
 * 基础按钮组件 - 统一按钮样式
 */
defineProps<{
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
}>()

defineEmits<{
  click: []
}>()
</script>

<template>
  <button
    class="base-button"
    :class="[variant || 'primary', size || 'md', { disabled, loading }]"
    :disabled="disabled || loading"
    @click="$emit('click')"
  >
    <span v-if="loading" class="spinner"></span>
    <slot />
  </button>
</template>

<style scoped>
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  font-family: var(--font-family);
  font-weight: var(--font-weight-medium);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.base-button:focus {
  outline: 2px solid var(--color-primary-light);
  outline-offset: 2px;
}

/* 尺寸 */
.base-button.sm {
  padding: var(--spacing-1) var(--spacing-3);
  font-size: var(--font-size-xs);
}

.base-button.md {
  padding: var(--spacing-2) var(--spacing-4);
  font-size: var(--font-size-sm);
}

.base-button.lg {
  padding: var(--spacing-3) var(--spacing-6);
  font-size: var(--font-size-base);
}

/* 变体 */
.base-button.primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.base-button.primary:hover:not(.disabled) {
  background: var(--color-primary-dark);
}

.base-button.secondary {
  background: var(--color-bg-hover);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.base-button.secondary:hover:not(.disabled) {
  background: var(--color-bg-active);
  border-color: var(--color-border-dark);
}

.base-button.danger {
  background: var(--color-error);
  color: var(--color-text-inverse);
}

.base-button.danger:hover:not(.disabled) {
  background: #DC2626;
}

.base-button.ghost {
  background: transparent;
  color: var(--color-text-secondary);
}

.base-button.ghost:hover:not(.disabled) {
  background: var(--color-bg-hover);
  color: var(--color-text);
}

/* 禁用状态 */
.base-button.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 加载状态 */
.base-button.loading {
  cursor: wait;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: var(--radius-full);
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>