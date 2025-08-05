// Export all modular stores for direct usage
export { useSearchBarStore } from './search/search-bar'
export { useContentStore } from './content/content'
export { useUIStore } from './ui/ui-state'
export { useLoadingStore } from './ui/loading'
export { useNotificationStore } from './utils/notifications'
export { useHistoryStore } from './content/history'

// Export mode stores
export { useLookupMode } from './search/modes/lookup'
export { useWordlistMode } from './search/modes/wordlist'

// Export composables
export { useRouterSync } from './composables/useRouterSync'

// For components that need the orchestrator pattern, provide a unified composable
import { useSearchBarStore } from './search/search-bar'
import { useContentStore } from './content/content'
import { useUIStore } from './ui/ui-state'
import { useLoadingStore } from './ui/loading'
import { useNotificationStore } from './utils/notifications'
import { useHistoryStore } from './content/history'
import { useLookupMode } from './search/modes/lookup'
import { useWordlistMode } from './search/modes/wordlist'

/**
 * Unified stores composable for components that need multiple stores
 * This provides all stores in one import while encouraging direct store usage
 */
export function useStores() {
  const searchBar = useSearchBarStore()
  return {
    searchBar,
    content: useContentStore(),
    ui: useUIStore(),
    loading: useLoadingStore(),
    notifications: useNotificationStore(),
    history: useHistoryStore(),
    lookupMode: useLookupMode(),
    wordlistMode: useWordlistMode(),
  }
}