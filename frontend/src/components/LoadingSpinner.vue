<script setup lang="ts">
/**
 * 加载动画组件
 */
defineProps<{
  size?: 'sm' | 'md' | 'lg'
}>()
</script>

<template>
  <div class="loading-spinner" :class="size || 'md'">
    <div class="spinner"></div>
  </div>
</template>

<style scoped>
.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner {
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-full);
  animation: spin 0.8s linear infinite;
}

/* 尺寸 */
.loading-spinner.sm .spinner {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

.loading-spinner.md .spinner {
  width: 24px;
  height: 24px;
  border-width: 3px;
}

.loading-spinner.lg .spinner {
  width: 40px;
  height: 40px;
  border-width: 4px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>