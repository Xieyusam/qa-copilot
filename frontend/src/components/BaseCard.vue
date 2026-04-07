<script setup lang="ts">
/**
 * 基础卡片组件 - 统一卡片样式
 */
defineProps<{
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
}>()
</script>

<template>
  <div class="base-card" :class="[padding || 'md', { hover }]">
    <slot />
  </div>
</template>

<style scoped>
.base-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

/* 内边距 */
.base-card.none {
  padding: 0;
}

.base-card.sm {
  padding: var(--spacing-3);
}

.base-card.md {
  padding: var(--spacing-4);
}

.base-card.lg {
  padding: var(--spacing-6);
}

/* 悬停效果 */
.base-card.hover {
  transition: box-shadow var(--transition-normal), transform var(--transition-normal);
  cursor: pointer;
}

.base-card.hover:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
</style>