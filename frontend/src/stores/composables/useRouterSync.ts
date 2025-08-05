import { getCurrentInstance, shallowRef } from 'vue'
import type { SynthesizedDictionaryEntry } from '@/types'
import type { Router, RouteLocationNormalizedLoaded } from 'vue-router'

export function useRouterSync() {
  // Cache router instance
  const routerRef = shallowRef<Router | null>(null)
  const currentRouteRef = shallowRef<RouteLocationNormalizedLoaded | null>(null)
  
  // Get router instance once and cache it
  const getRouter = () => {
    if (routerRef.value) {
      return routerRef.value
    }
    
    try {
      const instance = getCurrentInstance()
      const router = instance?.appContext.app.config.globalProperties.$router
      if (router) {
        routerRef.value = router
        // Also cache current route and update it on navigation
        currentRouteRef.value = router.currentRoute.value
        router.afterEach((to) => {
          currentRouteRef.value = to
        })
      }
      return router
    } catch (error) {
      console.warn('🧭 Could not get router instance:', error)
      return null
    }
  }
  
  // Optimized route comparison
  const isSameRoute = (targetName: string, targetParams?: Record<string, any>, targetQuery?: Record<string, any>) => {
    const current = currentRouteRef.value || getRouter()?.currentRoute.value
    if (!current) return false
    
    if (current.name !== targetName) return false
    
    // Compare params if provided
    if (targetParams) {
      for (const [key, value] of Object.entries(targetParams)) {
        if (current.params[key] !== value) return false
      }
    }
    
    // Compare query if provided
    if (targetQuery) {
      const currentQueryKeys = Object.keys(current.query).sort()
      const targetQueryKeys = Object.keys(targetQuery).sort()
      
      if (currentQueryKeys.length !== targetQueryKeys.length) return false
      
      for (const key of targetQueryKeys) {
        if (current.query[key] !== targetQuery[key]) return false
      }
    }
    
    return true
  }
  // Memoized navigation targets
  const navigationTargets = {
    dictionary: (word: string) => ({ 
      name: 'Definition', 
      params: { word: encodeURIComponent(word) },
      path: `/definition/${encodeURIComponent(word)}`
    }),
    thesaurus: (word: string) => ({ 
      name: 'Thesaurus', 
      params: { word: encodeURIComponent(word) },
      path: `/thesaurus/${encodeURIComponent(word)}`
    }),
    suggestions: (query: string) => ({ 
      name: 'Home', 
      query: { q: query, mode: 'suggestions' }
    })
  }
  
  // Enhanced router navigation for lookup mode with query and sub-mode support
  const navigateToLookupMode = (query: string, mode: 'dictionary' | 'thesaurus' | 'suggestions' = 'dictionary', routerInstance?: any) => {
    const router = routerInstance || getRouter()
    if (!router || !query.trim()) {
      return
    }

    const trimmedQuery = query.trim()
    const target = navigationTargets[mode](trimmedQuery)
    
    // Check if already on target route
    if (mode === 'suggestions') {
      const sugTarget = target as { name: string; query: { q: string; mode: string } }
      if (isSameRoute(sugTarget.name, undefined, sugTarget.query as Record<string, any>)) {
        return
      }
      router.push(sugTarget as any)
    } else {
      const wordTarget = target as { name: string; params: { word: string }; path: string }
      if (isSameRoute(wordTarget.name, wordTarget.params as Record<string, any>)) {
        return
      }
      router.push(wordTarget.path)
    }
  }

  // Legacy function for backward compatibility - enhanced to use new logic
  const updateRouterForCurrentEntry = (
    currentEntry: SynthesizedDictionaryEntry | null,
    mode: 'dictionary' | 'thesaurus' | 'suggestions',
    searchMode: string,
    routerInstance?: any
  ) => {
    // Only update router if we're in lookup mode and have an entry
    if (searchMode !== 'lookup' || !currentEntry?.word) {
      return
    }

    navigateToLookupMode(currentEntry.word, mode, routerInstance)
  }

  // Enhanced wordlist navigation with filters and mode query
  const navigateToWordlist = (
    wordlistId: string | null, 
    filters?: Record<string, any>,
    modeQuery?: string,
    routerInstance?: any
  ) => {
    const router = routerInstance || getRouter()
    if (!router) return

    if (!wordlistId) {
      router.push('/')
      return
    }

    // Build query parameters efficiently
    const queryParams: Record<string, any> = {}
    
    if (modeQuery?.trim()) {
      queryParams.q = modeQuery.trim()
    }
    
    // Filter out null/undefined/empty values
    if (filters) {
      for (const [key, value] of Object.entries(filters)) {
        if (value != null && value !== '') {
          queryParams[key] = value
        }
      }
    }

    // Check if already on target route
    if (isSameRoute('Wordlist', { wordlistId }, queryParams)) {
      return
    }
    
    router.push({
      path: `/wordlist/${wordlistId}`,
      query: queryParams
    })
  }

  // Navigate to home with optional query parameters
  const navigateToHome = (queryParams?: Record<string, any>, routerInstance?: any) => {
    const router = routerInstance || getRouter()
    if (!router) return

    const hasQueryParams = queryParams && Object.keys(queryParams).length > 0
    
    // Check if already on target route
    if (isSameRoute('Home', undefined, hasQueryParams ? queryParams : undefined)) {
      return
    }
    
    if (hasQueryParams) {
      router.push({ name: 'Home', query: queryParams })
    } else {
      router.push('/')
    }
  }

  // Navigate to word-of-the-day mode
  const navigateToWordOfTheDay = (modeQuery?: string) => {
    const queryParams: Record<string, any> = { mode: 'word-of-the-day' }
    if (modeQuery?.trim()) {
      queryParams.q = modeQuery.trim()
    }
    navigateToHome(queryParams)
  }

  // Navigate to stage mode  
  const navigateToStage = (modeQuery?: string) => {
    const queryParams: Record<string, any> = { mode: 'stage' }
    if (modeQuery?.trim()) {
      queryParams.q = modeQuery.trim()
    }
    navigateToHome(queryParams)
  }

  return {
    // Core navigation functions
    navigateToLookupMode,
    navigateToWordlist,
    navigateToHome,
    navigateToWordOfTheDay,
    navigateToStage,
    
    // Legacy compatibility
    updateRouterForCurrentEntry
  }
}