import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/problems',
      name: 'problems',
      component: () => import('../views/ProblemListView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/problem/:id',
      name: 'problem-detail',
      component: () => import('../views/ProblemDetailView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/submission/:id',
      name: 'submission-detail',
      component: () => import('../views/SubmissionDetailView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/datasets',
      name: 'datasets',
      component: () => import('../views/DatasetListView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/admin/problems',
      name: 'problem-admin',
      component: () => import('../views/admin/ProblemAdminView.vue'),
      meta: { requiresAuth: true, role: 'teacher' }
    },
    {
      path: '/rank',
      name: 'rank',
      component: () => import('../views/HomeView.vue') // Temporary
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue')
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue')
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/ProfileView.vue'),
      meta: { requiresAuth: true }
    },
    // Documentation Routes
    {
      path: '/docs/acm',
      name: 'doc-acm',
      component: () => import('../views/docs/ACMDocView.vue')
    },
    {
      path: '/docs/kaggle',
      name: 'doc-kaggle',
      component: () => import('../views/docs/KaggleDocView.vue')
    },
    {
      path: '/docs/oop',
      name: 'doc-oop',
      component: () => import('../views/docs/OOPDocView.vue')
    }
  ],
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const token = localStorage.getItem('token')
  
  if (to.meta.requiresAuth && !token) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  // Check role permission
  if (to.meta.role) {
    const user = userStore.user || JSON.parse(localStorage.getItem('user') || '{}')
    if (user.role !== to.meta.role) {
      next({ name: 'home' }) 
      return
    }
  }

  next()
})

export default router
