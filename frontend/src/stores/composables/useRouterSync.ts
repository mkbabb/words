import { getCurrentInstance } from 'vue'
import type { SynthesizedDictionaryEntry } from '@/types'

export function useRouterSync() {
  // Helper to get router instance safely
  const getRouter = () => {
    try {
      const instance = getCurrentInstance()
      return instance?.appContext.app.config.globalProperties.$router
    } catch (error) {
      console.warn('🧭 Could not get router instance:', error)
      return null
    }
  }
  // Enhanced router navigation for lookup mode with query and sub-mode support
  const navigateToLookupMode = (query: string, mode: 'dictionary' | 'thesaurus' | 'suggestions' = 'dictionary') => {
    const router = getRouter()
    if (!router || !query.trim()) {
      console.log('🧭 Cannot navigate: router unavailable or empty query')
      return
    }

    const encodedQuery = encodeURIComponent(query.trim())
    let targetPath: string
    let targetRoute: string

    // Determine route based on sub-mode
    if (mode === 'thesaurus') {
      targetPath = `/thesaurus/${encodedQuery}`
      targetRoute = 'Thesaurus'
    } else if (mode === 'suggestions') {
      // Suggestions mode stays on home but with query state
      targetPath = '/'
      targetRoute = 'Home'
    } else {
      // Default to dictionary
      targetPath = `/definition/${encodedQuery}`
      targetRoute = 'Definition'
    }

    const currentRoute = router.currentRoute?.value
    
    // Only navigate if we're not already on the correct route with the correct query
    if (currentRoute?.name !== targetRoute || currentRoute.params.word !== encodedQuery) {
      console.log('🧭 Navigating to lookup mode:', {
        query,
        mode,
        targetRoute,
        targetPath,
        currentRoute: currentRoute?.name,
        currentParams: currentRoute?.params
      })
      
      if (targetRoute === 'Home') {
        router.push({ name: 'Home', query: { q: query, mode: 'suggestions' } })
      } else {
        router.push(targetPath)
      }
    } else {
      console.log('🧭 Already on correct lookup route')
    }
  }

  // Legacy function for backward compatibility - enhanced to use new logic
  const updateRouterForCurrentEntry = (
    currentEntry: SynthesizedDictionaryEntry | null,
    mode: 'dictionary' | 'thesaurus' | 'suggestions',
    searchMode: string
  ) => {
    // Only update router if we're in lookup mode and have an entry
    if (searchMode !== 'lookup' || !currentEntry?.word) {
      return
    }

    navigateToLookupMode(currentEntry.word, mode)
  }

  // Enhanced wordlist navigation with filters and mode query
  const navigateToWordlist = (
    wordlistId: string | null, 
    filters?: Record<string, any>,
    modeQuery?: string
  ) => {
    const router = getRouter()
    if (!router) {
      console.log('🧭 Router not available for wordlist navigation')
      return
    }

    if (!wordlistId) {
      console.log('🧭 No wordlist selected, going to home')
      router.push('/')
      return
    }

    // Build query parameters for wordlist route
    const queryParams: Record<string, any> = {}
    
    // Add mode query if provided
    if (modeQuery && modeQuery.trim()) {
      queryParams.q = modeQuery.trim()
    }
    
    // Add filters if provided
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
          queryParams[key] = value
        }
      })
    }

    const currentRoute = router.currentRoute?.value
    const targetRoute = `/wordlist/${wordlistId}`
    
    // Check if we need to update the route
    const needsUpdate = currentRoute?.name !== 'WordList' || 
                       currentRoute.params.id !== wordlistId ||
                       JSON.stringify(currentRoute.query) !== JSON.stringify(queryParams)

    if (needsUpdate) {
      console.log('🧭 Navigating to wordlist:', {
        wordlistId,
        filters,
        modeQuery,
        queryParams,
        targetRoute,
        currentRoute: currentRoute?.name,
        currentParams: currentRoute?.params,
        currentQuery: currentRoute?.query
      })
      
      router.push({
        path: targetRoute,
        query: queryParams
      })
    } else {
      console.log('🧭 Already on correct wordlist route')
    }
  }

  // Navigate to home with optional query parameters
  const navigateToHome = (queryParams?: Record<string, any>) => {
    const router = getRouter()
    if (!router) {
      console.log('🧭 Router not available for home navigation')
      return
    }

    const currentRoute = router.currentRoute?.value
    const hasQueryParams = queryParams && Object.keys(queryParams).length > 0
    
    const needsUpdate = currentRoute?.name !== 'Home' || 
                       (hasQueryParams && JSON.stringify(currentRoute.query) !== JSON.stringify(queryParams))

    if (needsUpdate) {
      console.log('🧭 Navigating to home:', { queryParams })
      
      if (hasQueryParams) {
        router.push({ name: 'Home', query: queryParams })
      } else {
        router.push('/')
      }
    } else {
      console.log('🧭 Already on home route')
    }
  }

  // Navigate to word-of-the-day mode
  const navigateToWordOfTheDay = (modeQuery?: string) => {
    const router = getRouter()
    if (!router) {
      console.log('🧭 Router not available for word-of-the-day navigation')
      return
    }

    const queryParams: Record<string, any> = { mode: 'word-of-the-day' }
    if (modeQuery && modeQuery.trim()) {
      queryParams.q = modeQuery.trim()
    }

    navigateToHome(queryParams)
  }

  // Navigate to stage mode  
  const navigateToStage = (modeQuery?: string) => {
    const router = getRouter()
    if (!router) {
      console.log('🧭 Router not available for stage navigation')
      return
    }

    const queryParams: Record<string, any> = { mode: 'stage' }
    if (modeQuery && modeQuery.trim()) {
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