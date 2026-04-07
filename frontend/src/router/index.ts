import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import ChatView from '../views/ChatView.vue'
import KnowledgeSourcesView from '../views/KnowledgeSourcesView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import ObservabilityView from '../views/ObservabilityView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/register', component: RegisterView, meta: { public: true } },
    { path: '/', component: ChatView },
    { path: '/docs', component: KnowledgeSourcesView, meta: { requiresAdmin: true } },
    { path: '/admin/observability', component: ObservabilityView, meta: { requiresAdmin: true } },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const token = localStorage.getItem('token')
  const authStore = useAuthStore()

  // Public routes
  if (to.meta.public) {
    if (token) return next('/')
    return next()
  }

  // Require authentication
  if (!token) {
    return next('/login')
  }

  // Admin routes require admin role
  if (to.meta.requiresAdmin) {
    // Fetch user info if not already loaded
    if (!authStore.user) {
      await authStore.fetchUser()
    }

    if (authStore.user?.role !== 'admin') {
      // Non-admin users redirect to home
      return next('/')
    }
  }

  next()
})

export default router
