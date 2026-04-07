<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
  if (authStore.isAuthenticated && !authStore.user) {
    try {
      const res = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${authStore.token}` }
      })
      if (res.ok) {
        authStore.setUser(await res.json())
      } else {
        authStore.logout()
        router.push('/login')
      }
    } catch {
      //
    }
  }
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-container">
    <!-- 顶部导航 -->
    <header v-if="route.path !== '/login' && route.path !== '/register'" class="app-header">
      <h1 class="app-logo">🤖 QA Copilot</h1>

      <nav class="nav-menu">
        <RouterLink to="/" class="nav-link" :class="{ active: route.path === '/' }">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <span>Copilot</span>
        </RouterLink>

        <RouterLink v-if="authStore.isAdmin" to="/docs" class="nav-link" :class="{ active: route.path === '/docs' }">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
          <span>知识源</span>
        </RouterLink>

        <RouterLink v-if="authStore.isAdmin" to="/admin/observability" class="nav-link" :class="{ active: route.path === '/admin/observability' }">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
          </svg>
          <span>观测</span>
        </RouterLink>
      </nav>

      <div class="header-right">
        <span v-if="authStore.user" class="user-info">
          <span class="user-avatar">{{ authStore.user.username?.charAt(0).toUpperCase() }}</span>
          <span class="user-name">{{ authStore.user.username }}</span>
        </span>
        <button @click="handleLogout" class="logout-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          <span>退出</span>
        </button>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--color-bg);
}

/* 头部导航 */
.app-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-6);
  padding: 0 var(--spacing-6);
  height: 60px;
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.app-logo {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  white-space: nowrap;
}

/* 导航菜单 */
.nav-menu {
  display: flex;
  gap: var(--spacing-1);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: all var(--transition-fast);
}

.nav-link:hover {
  background: var(--color-bg-hover);
  color: var(--color-text);
}

.nav-link.active {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

/* 右侧区域 */
.header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
}

.user-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.logout-btn:hover {
  background: var(--color-error-bg);
  border-color: var(--color-error);
  color: var(--color-error);
}

/* 主内容区 */
.app-main {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
</style>