<script setup lang="ts">
import { onMounted } from 'vue'
import { useChatStore } from '../stores/chat'
import SessionList from '../components/SessionList.vue'
import ChatInterface from '../components/ChatInterface.vue'

const store = useChatStore()

onMounted(() => {
  store.init()
})
</script>

<template>
  <div class="chat-view">
    <aside class="session-sidebar">
      <SessionList />
    </aside>
    <main class="chat-main">
      <ChatInterface />
    </main>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex: 1;
  min-height: 0;
  height: 100%;
}

.session-sidebar {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: var(--spacing-4);
}
</style>
