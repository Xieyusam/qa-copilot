import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// 引入设计规范
import './assets/design.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
