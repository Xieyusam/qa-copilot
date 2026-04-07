<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <div class="auth-logo">🤖</div>
        <h1 class="auth-title">创建账号</h1>
        <p class="auth-subtitle">注册 QA Copilot 以开始对话</p>
      </div>

      <form class="auth-form" @submit.prevent="handleRegister">
        <div class="form-group">
          <label for="username" class="form-label">用户名</label>
          <input
            id="username"
            v-model="username"
            name="username"
            type="text"
            required
            class="form-input"
            placeholder="请输入用户名"
            autocomplete="username"
          >
        </div>

        <div class="form-group">
          <label for="password" class="form-label">密码</label>
          <input
            id="password"
            v-model="password"
            name="password"
            type="password"
            required
            class="form-input"
            placeholder="请输入至少6位密码"
            autocomplete="new-password"
          >
        </div>

        <div v-if="errorMsg" class="form-error">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
          {{ errorMsg }}
        </div>

        <button type="submit" class="submit-btn" :disabled="loading">
          <span v-if="loading" class="btn-spinner"></span>
          <span v-else>注册</span>
        </button>

        <div class="auth-footer">
          <span class="footer-text">已有账号？</span>
          <router-link to="/login" class="footer-link">直接登录</router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const username = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)
const router = useRouter()

async function handleRegister() {
  if (!username.value || !password.value) return
  if (password.value.length < 6) {
    errorMsg.value = '密码至少需要6位'
    return
  }

  loading.value = true
  errorMsg.value = ''

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: username.value,
        password: password.value
      })
    })

    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || '注册失败')
    }

    router.push('/login')
  } catch (e: any) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-6);
  background: linear-gradient(135deg, var(--color-primary-bg) 0%, var(--color-bg) 100%);
}

.auth-card {
  width: 100%;
  max-width: 400px;
  background: var(--color-bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  padding: var(--spacing-10);
}

.auth-header {
  text-align: center;
  margin-bottom: var(--spacing-8);
}

.auth-logo {
  font-size: 48px;
  margin-bottom: var(--spacing-4);
}

.auth-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  margin: 0 0 var(--spacing-2);
}

.auth-subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-5);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
}

.form-input {
  width: 100%;
  padding: var(--spacing-3) var(--spacing-4);
  font-size: var(--font-size-base);
  font-family: var(--font-family);
  color: var(--color-text);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  outline: none;
  transition: all var(--transition-fast);
}

.form-input::placeholder {
  color: var(--color-text-muted);
}

.form-input:hover {
  border-color: var(--color-border-dark);
}

.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.form-error {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--color-error-bg);
  color: var(--color-error);
  font-size: var(--font-size-sm);
  border-radius: var(--radius-md);
}

.submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 48px;
  padding: 0 var(--spacing-4);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.submit-btn:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: var(--radius-full);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.auth-footer {
  text-align: center;
  font-size: var(--font-size-sm);
  margin-top: var(--spacing-2);
}

.footer-text {
  color: var(--color-text-secondary);
}

.footer-link {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  margin-left: var(--spacing-1);
}

.footer-link:hover {
  text-decoration: underline;
}
</style>