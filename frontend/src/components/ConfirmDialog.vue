<script setup lang="ts">
defineProps<{
  title: string
  message: string
  confirmText?: string
  loading?: boolean
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('cancel')
}
</script>

<template>
  <Teleport to="body">
    <div class="overlay" @click.self="emit('cancel')" @keydown="onKeydown" tabindex="-1">
      <div class="dialog" role="dialog" :aria-label="title">
        <h3 class="dialog-title">{{ title }}</h3>
        <p class="dialog-message">{{ message }}</p>
        <div class="dialog-actions">
          <button class="btn-cancel" :disabled="loading" @click="emit('cancel')">取消</button>
          <button class="btn-confirm" :disabled="loading" @click="emit('confirm')">
            <span v-if="loading" class="btn-spinner"></span>
            {{ confirmText ?? '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.dialog {
  background: #fff;
  border-radius: 10px;
  padding: 24px;
  width: 360px;
  max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialog-title {
  font-size: 16px;
  font-weight: 600;
  color: #222;
  margin: 0;
}

.dialog-message {
  font-size: 14px;
  color: #555;
  margin: 0;
  line-height: 1.6;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 4px;
}

.btn-cancel {
  padding: 7px 18px;
  background: transparent;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: #555;
  transition: background 0.15s;
}

.btn-cancel:hover:not(:disabled) { background: #f5f5f5; }
.btn-cancel:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-confirm {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 18px;
  background: #e53935;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.15s;
}

.btn-confirm:hover:not(:disabled) { background: #b71c1c; }
.btn-confirm:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-spinner {
  width: 13px;
  height: 13px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
