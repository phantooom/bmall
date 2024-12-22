import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import Home from '../views/Home.vue'
import BrandManage from '../views/BrandManage.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: Home
  },
  {
    path: '/brands',
    name: 'brands',
    component: BrandManage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router 