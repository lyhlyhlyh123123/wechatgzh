import { createRouter, createWebHistory } from 'vue-router'
import DetailView from './views/DetailView.vue'
import HomeView from './views/HomeView.vue'
import SettingsView from './views/SettingsView.vue'
import TopicsView from './views/TopicsView.vue'
import WizardView from './views/WizardView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/wizard', component: WizardView },
    { path: '/articles/:id', component: DetailView },
    { path: '/topics', component: TopicsView },
    { path: '/settings', component: SettingsView },
  ],
})

export default router
