<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '../stores/chat'
import ConfirmDialog from './ConfirmDialog.vue'

const store = useChatStore()

const deleteTarget = ref<{ id: string; title: string } | null>(null)
const deletingId = ref<string | null>(null)

function formatTime(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH} 小时前`
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

async function confirmDeleteSession() {
  if (!deleteTarget.value) return
  deletingId.value = deleteTarget.value.id
  try {
    await store.removeSession(deleteTarget.value.id)
  } finally {
    deletingId.value = null
    deleteTarget.value = null
  }
}
</script>

<template>
  <div class="session-list">
    <div class="list-header">
      <span class="list-title">历史对话</span>
      <button class="btn-new" @click="store.newSession()" title="新建会话">
        ✏️ 新建
      </button>
    </div>

    <div class="sessions">
      <div
        v-for="s in store.sessions"
        :key="s.sessionId"
        class="session-item"
        :class="{ active: s.sessionId === store.currentSessionId }"
        @click="store.switchSession(s.sessionId)"
      >
        <div class="session-body">
          <p class="session-title">{{ s.title || '新对话' }}</p>
          <p class="session-time">{{ formatTime(s.lastActive) }}</p>
        </div>
        <button
          class="btn-del-session"
          :disabled="deletingId === s.sessionId"
          @click.stop="deleteTarget = { id: s.sessionId, title: s.title || '新对话' }"
          title="删除会话"
        >
          <span v-if="deletingId === s.sessionId" class="mini-spinner"></span>
          <span v-else class="del-icon">×</span>
        </button>
      </div>

      <div v-if="store.sessions.length === 0" class="empty-sessions">
        暂无历史对话
      </div>
    </div>

    <ConfirmDialog
      v-if="deleteTarget"
      title="删除会话"
      :message="`确定要删除「${deleteTarget.title}」吗？`"
      confirmText="删除"
      :loading="deletingId === deleteTarget.id"
      @confirm="confirmDeleteSession"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<style scoped>
.session-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-card);
  border-right: 1px solid var(--color-border);
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-4);
  flex-shrink: 0;
}

.list-title {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.btn-new {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-1) var(--spacing-3);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-fast);
}

.btn-new:hover {
  background: var(--color-primary-dark);
}

.sessions {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-1) var(--spacing-2) var(--spacing-2);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.session-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.session-item:hover {
  background: var(--color-bg-hover);
}

.session-item.active {
  background: var(--color-primary-bg);
}

.session-body {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item.active .session-title {
  color: var(--color-primary);
}

.session-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin: var(--spacing-1) 0 0;
}

.btn-del-session {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  opacity: 0;
  transition: all var(--transition-fast);
  color: var(--color-text-muted);
  font-size: 18px;
}

.session-item:hover .btn-del-session {
  opacity: 1;
}

.btn-del-session:hover {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.btn-del-session:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.del-icon {
  line-height: 1;
}

.mini-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-error);
  border-radius: var(--radius-full);
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-sessions {
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  padding: var(--spacing-6) 0;
}
</style>
