import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: Home,
    },
    {
      path: '/search/:query?',
      name: 'Search',
      component: Home,
      props: true,
    },
    {
      path: '/definition/:word',
      name: 'Definition',
      component: Home,
      props: true,
    },
    {
      path: '/thesaurus/:word',
      name: 'Thesaurus',
      component: Home,
      props: true,
    },
    {
      path: '/wordlist/:wordlistId',
      name: 'Wordlist',
      component: Home,
      props: true,
    },
    {
      path: '/wordlist/:wordlistId/search/:query?',
      name: 'WordlistSearch',
      component: Home,
      props: true,
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFound.vue'),
    },
  ],
})

// Navigation guards
router.beforeEach((to) => {
  const baseTitle = 'Floridify'

  if (to.name === 'Definition' && to.params.word) {
    document.title = `${to.params.word} - ${baseTitle}`
  } else if (to.name === 'Thesaurus' && to.params.word) {
    document.title = `${to.params.word} (Thesaurus) - ${baseTitle}`
  } else if (to.name === 'Search' && to.params.query) {
    document.title = `Search: ${to.params.query} - ${baseTitle}`
  } else if (to.name === 'NotFound') {
    document.title = `Not Found - ${baseTitle}`
  } else {
    document.title = baseTitle
  }
})

export default router
