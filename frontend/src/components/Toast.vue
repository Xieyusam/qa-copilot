<script setup lang="ts">
import { ref } from 'vue'

export interface ToastMessage {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number
}

const toasts = ref<ToastMessage[]>([])
let toastId = 0

function add(type: ToastMessage['type'], message: string, duration = 3000) {
  const id = ++toastId
  toasts.value.push({ id, type, message, duration })

  if (duration > 0) {
    setTimeout(() => {
      remove(id)
    }, duration)
  }

  return id
}

function remove(id: number) {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index !== -1) {
    toasts.value.splice(index, 1)
  }
}

function success(message: string, duration?: number) {
  return add('success', message, duration)
}

function error(message: string, duration?: number) {
  return add('error', message, duration)
}

function warning(message: string, duration?: number) {
  return add('warning', message, duration)
}

function info(message: string, duration?: number) {
  return add('info', message, duration)
}

defineExpose({
  add,
  remove,
  success,
  error,
  warning,
  info
})
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast"
          :class="toast.type"
        >
          <span class="toast-icon">
            <svg v-if="toast.type === 'success'" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
            <svg v-else-if="toast.type === 'error'" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="15" y1="9" x2="9" y2="15"></line>
              <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
            <svg v-else-if="toast.type === 'warning'" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
              <line x1="12" y1="9" x2="12" y2="13"></line>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
          </span>
          <span class="toast-message">{{ toast.message }}</span>
          <button class="toast-close" @click="remove(toast.id)">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: var(--spacing-6);
  right: var(--spacing-6);
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.toast {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  min-width: 280px;
  max-width: 400px;
  border-left: 4px solid var(--color-primary);
}

.toast.success {
  border-left-color: var(--color-success);
}

.toast.error {
  border-left-color: var(--color-error);
}

.toast.warning {
  border-left-color: var(--color-warning);
}

.toast.info {
  border-left-color: var(--color-primary);
}

.toast-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.toast.success .toast-icon {
  color: var(--color-success);
}

.toast.error .toast-icon {
  color: var(--color-error);
}

.toast.warning .toast-icon {
  color: var(--color-warning);
}

.toast.info .toast-icon {
  color: var(--color-primary);
}

.toast-message {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--color-text);
}

.toast-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.toast-close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text);
}

/* 动画 */
.toast-enter-active,
.toast-leave-active {
  transition: all var(--transition-normal);
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>