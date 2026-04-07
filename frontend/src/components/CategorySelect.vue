<script setup lang="ts">
import { useCategoryStore } from '../stores/categories'

defineProps<{
  modelValue: string
  disabled?: boolean
  placeholder?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const store = useCategoryStore()

function onChange(e: Event) {
  const target = e.target as HTMLSelectElement
  emit('update:modelValue', target.value)
}
</script>

<template>
  <select
    :value="modelValue"
    :disabled="disabled"
    class="category-select"
    @change="onChange"
  >
    <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
    <option
      v-for="cat in store.categories"
      :key="cat.id"
      :value="cat.id"
    >
      {{ cat.name }}{{ cat.description ? ` - ${cat.description}` : '' }}
    </option>
  </select>
</template>

<style scoped>
.category-select {
  width: 100%;
  padding: var(--spacing-2) var(--spacing-8) var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  background-color: var(--color-bg-card);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  color: var(--color-text);
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  transition: all var(--transition-fast);
}

.category-select:hover:not(:disabled) {
  border-color: var(--color-border-dark);
}

.category-select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.category-select:disabled {
  background-color: var(--color-bg-hover);
  cursor: not-allowed;
  opacity: 0.6;
}
</style>