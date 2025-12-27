import {createRouter, createWebHistory} from 'vue-router'
import HomeView from '../views/HomeView.vue'
import {useUserStore} from '@/stores/user'
import {useSysStore} from '@/stores/sys'

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
            meta: {requiresAuth: true}
        },
        {
            path: '/problem/:id',
            name: 'problem-detail',
            component: () => import('../views/ProblemDetailView.vue'),
            meta: {requiresAuth: true}
        },
        {
            path: '/submission/:id',
            name: 'submission-detail',
            component: () => import('../views/SubmissionDetailView.vue'),
            meta: {requiresAuth: true}
        },
        {
            path: '/datasets',
            name: 'datasets',
            component: () => import('../views/DatasetListView.vue'),
            meta: {requiresAuth: true}
        },
        {
            path: '/exam',
            name: 'exam',
            component: () => import('../views/ExamView.vue'),
            meta: {requiresAuth: true}
        },
        {
            path: '/exam/:id',
            name: 'exam-detail',
            component: () => import('../views/ExamDetailView.vue'),
            meta: {requiresAuth: true}
        },
        {
            path: '/exam/:id/rank',
            name: 'exam-rank',
            component: () => import('../views/ExamRankView.vue'),
            meta: {requiresAuth: true}
        },
        {
            path: '/admin/dashboard',
            name: 'teacher-dashboard',
            component: () => import('../views/admin/TeacherDashboardView.vue'),
            meta: {requiresAuth: true, role: 'teacher'}
        },
        {
            path: '/admin/problems',
            name: 'problem-admin',
            component: () => import('../views/admin/ProblemAdminView.vue'),
            meta: {requiresAuth: true, role: 'teacher'}
        },
        {
            path: '/admin/exams',
            name: 'exam-admin',
            component: () => import('../views/admin/ExamAdminView.vue'),
            meta: {requiresAuth: true, role: 'teacher'}
        },
        {
            path: '/admin/exams/:id/monitor',
            name: 'exam-monitor',
            component: () => import('../views/admin/ExamMonitorView.vue'),
            meta: {requiresAuth: true, role: 'teacher'}
        },
        {
            path: '/admin/submissions',
            name: 'submission-admin',
            component: () => import('../views/admin/SubmissionAdminView.vue'),
            meta: {requiresAuth: true, role: 'teacher'}
        },
        {
            path: '/admin/plagiarism',
            name: 'plagiarism-admin',
            component: () => import('../views/admin/PlagiarismLogView.vue'),
            meta: {requiresAuth: true, role: 'teacher'}
        },
        {
            path: '/admin/plagiarism/compare',
            name: 'code-compare',
            component: () => import('../views/admin/CodeCompareView.vue'),
            meta: {requiresAuth: true, role: 'teacher'}
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
            meta: {requiresAuth: true}
        },
        {
            path: '/profile/:id',
            name: 'user-profile',
            component: () => import('../views/ProfileView.vue'),
            meta: {requiresAuth: true}
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
        },
        {
            path: '/docs/teacher-manual',
            name: 'doc-teacher-manual',
            component: () => import('../views/docs/TeacherManualView.vue'),
            meta: {requiresAuth: true, role: 'teacher'}
        }
    ],
})

router.beforeEach(async (to, from, next) => {
    const userStore = useUserStore()
    const sysStore = useSysStore()
    const token = localStorage.getItem('token')

    // Ensure sys info is loaded to check practice mode
    if (sysStore.practice === undefined) {
        await sysStore.fetchSysInfo()
    }

    const user = userStore.user || JSON.parse(localStorage.getItem('user') || '{}')
    const isTeacher = user.role === 'teacher'
    const isPracticeMode = sysStore.practice !== false && sysStore.practice !== 'False'

    // Exam Mode Logic
    if (!isPracticeMode) {
        // If practice mode is OFF (i.e., Exam Mode is ON)
        if (!isTeacher) {
            // Restrict access to specific practice-related routes
            const restrictedRoutes = ['problems', 'datasets']
            if (restrictedRoutes.includes(to.name)) {
                next({name: 'exam'})
                return
            }
            
            // If trying to access a problem detail, check if it's within an exam context
            if (to.name === 'problem-detail' && !to.query.exam_id) {
                next({name: 'exam'})
                return
            }
        }
    } else {
        // If practice mode is ON
        if (!isTeacher) {
            // Restrict access to exam-related routes
            const examRoutes = ['exam', 'exam-detail', 'exam-rank']
            if (examRoutes.includes(to.name)) {
                next({name: 'home'})
                return
            }
        }
    }

    if (to.meta.requiresAuth && !token) {
        next({name: 'login', query: {redirect: to.fullPath}})
        return
    }

    // Check role permission
    if (to.meta.role) {
        if (user.role !== to.meta.role) {
            next({name: 'home'})
            return
        }
    }

    next()
})

export default router
