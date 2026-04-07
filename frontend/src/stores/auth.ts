import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<{ id: string; username: string; role: string } | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  function setUser(newUser: { id: string; username: string; role: string }) {
    user.value = newUser
  }

  async function fetchUser() {
    if (!token.value) return null

    try {
      const res = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${token.value}`
        }
      })

      if (res.ok) {
        const data = await res.json()
        user.value = data
        return data
      } else {
        // Token invalid
        logout()
        return null
      }
    } catch (e) {
      console.error('Failed to fetch user:', e)
      return null
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isAuthenticated, isAdmin, setToken, setUser, fetchUser, logout }
})
