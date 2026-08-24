import { createRouter, createWebHistory } from 'vue-router'
import DetailView from './views/DetailView.vue'
import HomeView from './views/HomeView.vue'
import SettingsView from './views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/articles/:id', component: DetailView },
    { path: '/settings', component: SettingsView },
  ],
})

export default router
