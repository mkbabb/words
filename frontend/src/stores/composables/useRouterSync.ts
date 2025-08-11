import { watch } from 'vue'
import { useRouter } from 'vue-router'
import type { SearchMode } from '@/types'

/**
 * Router synchronization composable
 * Syncs store state with URL parameters
 */
export function useRouterSync() {
  const router = useRouter()

  const syncModeToRoute = (mode: SearchMode) => {
    // Update URL without triggering navigation
    router.replace({ 
      query: { 
        ...router.currentRoute.value.query, 
        mode 
      } 
    })
  }

  const getModeFromRoute = (): SearchMode | null => {
    const query = router.currentRoute.value.query
    if (typeof query.mode === 'string') {
      return query.mode as SearchMode
    }
    return null
  }

  return {
    syncModeToRoute,
    getModeFromRoute
  }
}