<script setup lang="ts">
/**
 * 空状态组件 - 引导性提示
 */
defineProps<{
  icon?: string
  title: string
  description?: string
}>()
</script>

<template>
  <div class="empty-state">
    <div v-if="icon" class="empty-icon">{{ icon }}</div>
    <div class="empty-icon default-icon" v-else>
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <path d="M8 15h8"></path>
        <path d="M9 9h.01"></path>
        <path d="M15 9h.01"></path>
      </svg>
    </div>
    <h3 class="empty-title">{{ title }}</h3>
    <p v-if="description" class="empty-description">{{ description }}</p>
    <div v-if="$slots.default" class="empty-action">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-12);
  text-align: center;
}

.empty-icon {
  color: var(--color-text-muted);
  font-size: 48px;
  margin-bottom: var(--spacing-4);
}

.default-icon {
  opacity: 0.5;
}

.empty-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
  margin-bottom: var(--spacing-2);
}

.empty-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  max-width: 320px;
  margin-bottom: var(--spacing-4);
}

.empty-action {
  margin-top: var(--spacing-2);
}
</style>